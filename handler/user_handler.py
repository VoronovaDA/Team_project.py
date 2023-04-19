import json
import random
import re

import requests

from handler.keyboard import make_keyboard
from handler.tools import profile_check
from vk_profile import VkUser
from vk_search import VkSearch


class UserHandler:
    url = "https://api.vk.com/method"

    def __init__(
            self,
            db_session,
            group_id: int,
            version: str,
            token_group: str,
            token_service: str
    ):
        self.db_session = db_session
        self.session = {}
        self.group_id = group_id
        self.params = {"access_token": token_group, "v": version}
        self.params_search_city = {"access_token": token_service, "v": version, 'lang': 0}
        self.reg_long_poll_server()

    def get_long_poll_server(self, group_id):  # Запрос сервера
        params = {"group_id": group_id}
        return requests.get(
            f"{self.url}/groups.getLongPollServer",
            params={**self.params, **params},
        ).json()

    def reg_long_poll_server(self):  # Запускаем сервер
        serv_param = self.get_long_poll_server(self.group_id)
        if serv_param is None:
            return
        serv_param = serv_param["response"]
        ts = serv_param["ts"]
        answer = True
        while answer:
            res = requests.get(
                f'{serv_param["server"]}?act=a_check&key={serv_param["key"]}&ts={ts}&wait=25'
            ).json()
            if "failed" in res:
                if res["failed"] == 1:
                    ts = res["ts"]
                else:
                    serv_param = self.get_long_poll_server(self.group_id)
                    if serv_param is None:
                        return
                    ts = serv_param["response"]["ts"]
            else:
                ts = res["ts"]
                for update in res["updates"]:
                    if update["type"] == "message_new":
                        self.parse_message(update["object"]["message"])

    def send_message(
            self,
            user_id: int,
            message: dict  # {'text': '', 'attachment': '', 'btn_in_mes': True\False, 'buttons':[]}
    ):
        # https://dev.vk.com/method/messages.send
        params = {
            "user_id": user_id,
            "peer_id": user_id,
            "random_id": random.randint(1, 10000),
        }

        if "text" in message:
            params["message"] = message["text"]

        if "attachment" in message:
            params["attachment"] = message["attachment"]

        if "btn_in_mes" not in message:
            message["btn_in_mes"] = False

        if "buttons" in message:
            params["keyboard"] = make_keyboard(
                [message["buttons"]], message["btn_in_mes"]
            )
        answer = requests.get(
            f"{self.url}/messages.send", params={**self.params, **params}
        ).json()
        if 'error' in answer:
            del params["keyboard"]
            del params["attachment"]
            params['text'] = 'Ошибка при обработке, повторите попытку чуть позже'

            requests.get(
                f"{self.url}/messages.send", params={**self.params, **params}
            ).json()

    def parse_message(self, message):  # Разбор входящих сообщений
        if message["from_id"] not in self.session:
            self.session[message["from_id"]] = {"profile": None, "handler": None}
        session = self.session[message["from_id"]]
        if session["profile"] is None:  # Загружаем профиль
            session["profile"] = VkUser(
                self.db_session, message["from_id"], self.params["access_token"]
            )
            session["profile"].save()
            session["client"] = None
            session["favorite_offset"] = 0
            session['params'] = {"cmid": message["conversation_message_id"]}
        answer = False
        check = profile_check(session["profile"])
        cmd = self.default_cmd
        command = "default_cmd"
        if "payload" in message:  # Нажата кнопка
            command = json.loads(message["payload"])["command"]
            if 'params' in message["payload"]:
                session['params'] = {**session['params'], **json.loads(message["payload"])["params"]}
        if (
                len(check) > 0
                and session["handler"] is None
                and command.find("setting") == -1
        ):
            answer = self.menu_settings()
            answer["text"] = f"{check} {answer['text']}"
        else:
            if session["handler"] is not None and command.find("cancel") == -1:
                cmd = session["handler"]
            elif command in dir(self):
                cmd = getattr(self, command)
            try:
                message["text"] = re.sub('[^a-zа-я-0-9,. ]', '', message["text"], flags=re.IGNORECASE)
                answer = cmd(session, message["text"])
            except Exception as e:
                answer = {"text": "Ошибка при обработке, повторите попытку чуть позже"}
        if type(answer) is list:
            for mes in answer:
                self.send_message(message["from_id"], mes)
        else:
            if answer:
                self.send_message(message["from_id"], answer)

    def menu_main(self):
        return {
            "text": "Главное меню",
            "buttons": [
                [
                    ["В избранное", '{"command":"to_favorite"}', "primary"],
                    ["Следующий", '{"command":"next"}', "primary"],
                ],
                [["Избранные", '{"command":"favorites"}', "primary"]],
                [["Настройки", '{"command":"settings"}', "primary"]],
            ],
        }

    def menu_settings(self):
        return {
            "text": '<br>Меню "Настройки"',
            "buttons": [
                [
                    ["Возраст", '{"command":"setting_age"}', "primary"],
                    ["Город", '{"command":"setting_city"}', "primary"],
                    ["Пол", '{"command":"setting_sex"}', "primary"],
                ],
                [["Регистрация", "https://178.57.222.71:8080/", None, "open_link"]],
                [["Удалить профиль", '{"command":"setting_del"}', "primary"]],
                [["<- Назад", '{"command":"default_cmd"}', "primary"]],
            ],
        }

    def menu_favorites(self):
        return {
            "text": "Избранные",
            "buttons": [
                [
                    [
                        "Предыдущая страница",
                        '{"command":"favorites_prev_page"}',
                        "primary",
                    ],
                    [
                        "Следующая страница",
                        '{"command":"favorites_next_page"}',
                        "primary",
                    ],
                ],
                [["<- Назад", '{"command":"default_cmd"}', "primary"]],
            ],
        }

    def default_cmd(self, session, text):
        session["handler"] = None
        return self.menu_main()

    def settings(self, session, text):
        session["handler"] = None
        return self.menu_settings()

    def setting_cancel(self, session, text):
        session["handler"] = None
        return self.menu_main()

    def setting_age(self, session, text):
        session["handler"] = self.setting_age_save
        answer = {'text': "Введите возраст:",
                  "buttons": [[["Отмена", '{"command":"settings_cancel"}', "primary"]]]}
        if session["profile"].age is not None:
            answer['text'] = f"Ваш текущий возраст: {session['profile'].age} <br> {answer['text']}"
        return answer

    def setting_age_save(self, session, text):
        session["handler"] = None
        mes = self.menu_settings()
        if text.isdigit():
            text = int(text)
            if 10 <= text <= 100:
                session["profile"].age = text
                mes["text"] = f"Возраст сохранен {mes['text']}"
                session["profile"].save()
            else:
                mes["text"] = f"Пошутить любишь :) {mes['text']}"
        else:
            mes["text"] = f"Введите возраст цифрами {mes['text']}"
        return mes

    def setting_city(self, session, text):
        session["handler"] = self.setting_city_save
        answer = {'text': "Введите новый (город, область):",
                  "buttons": [[["Отмена", '{"command":"settings_cancel"}', "primary"]]]}
        if session['profile'].city is not None:
            answer['text'] = f"Ваш текущий город: {self.get_city(session['profile'].city)} <br> {answer['text']}"
        return answer

    def setting_city_save(self, session, text):
        session["handler"] = None
        mes = self.menu_settings()
        if 'city' not in session['params']:
            result, text = self.search_city(text)
            if result is None:
                mes["text"] = f"Город неопределен: {text}"
                session["handler"] = self.setting_city
                return mes
            else:
                return {
                    "text": f"Сохранить {result['title']} ?",
                    "buttons": [
                        [
                            ["Да", f'{{"command":"setting_city_save", "params":{{"city": {result["id"]} }}}}',
                             "primary"],
                            ["Нет", '{"command":"settings_cancel"}', "primary"],
                        ],
                        [["Отмена", '{"command":"settings_cancel"}', "primary"]],
                    ],
                }
        else:
            session["profile"].city = int(session['params']['city'])
            session["profile"].save()
        mes["text"] = f"Город сохранен {mes['text']}"
        return mes

    def get_city(self, id):
        city = ''
        params = {
            "city_ids": id
        }
        response = requests.get(
            f"{self.url}/database.getCitiesById",
            params={**self.params_search_city, **params}
        ).json()
        if 'error' not in response:
            city = response['response'][0]['title']
        return city

    def search_region(self, value):
        url = "https://api.vk.com/method"

        answer = []
        params = {
            "q": value,
            "country_id": 1,
            "count": 10,
        }
        response = requests.get(
            f"{url}/database.getRegions",
            params={**self.params_search_city, **params}
        ).json()
        if 'error' not in response:
            answer = response['response']['items']
        return answer

    def search_city(self, value):
        url = "https://api.vk.com/method"
        params = {"country_id": 1}
        arr = value.split(',')
        answer = None

        if len(arr) > 1:
            region_arr = self.search_region(arr[1].strip())
            if len(region_arr) != 1:
                return None, 'Уточните область'
            params["region_id"] = region_arr[0]['id']
        params["q"] = arr[0].strip()
        params["count"] = 1

        response = requests.get(
            f"{url}/database.getCities",
            params={**self.params_search_city, **params}
        ).json()
        if 'error' not in response:
            if response['response']['count'] > 0:
                answer = response['response']['items'][0]
        return answer, ''

    def setting_sex(self, session, text):
        session["handler"] = None
        mes = {
            "text": "Укажите пол",
            "buttons": [
                [
                    ["Мужской", '{"command":"setting_sex_save_male"}', "primary"],
                    ["Женский", '{"command":"setting_sex_save_female"}', "primary"],
                ],
                [["Отмена", '{"command":"settings_cancel"}', "primary"]],
            ],
        }
        if session["profile"].sex == 1:
            mes["text"] += " (текущий пол: женский)"
        elif session["profile"].sex == 2:
            mes["text"] += " (текущий пол: мужской)"
        else:
            mes["text"] += " (текущий пол: неопределен)"
        return mes

    def setting_sex_save_male(self, session, text):
        session["handler"] = None
        session["profile"].sex = 2
        mes = self.menu_settings()
        mes["text"] = f"Пол сохранен {mes['text']}"
        return mes

    def setting_sex_save_female(self, session, text):
        session["handler"] = None
        session["profile"].sex = 1
        mes = self.menu_settings()
        mes["text"] = f"Пол сохранен {mes['text']}"
        return mes

    def next(self, session, text):
        if session["client"] is not None:
            self.db_session.candidates_save(session["profile"], session["client"])
        session["client"] = VkSearch(session["profile"], self.db_session).next()
        return {
            "text": f'{session["client"].last_name} {session["client"].first_name}\n https://vk.com/id{session["client"].vk_id}',
            "attachment": session["client"].photos,
        }

    def to_favorite(self, session, text):
        if session["client"] is not None:
            self.db_session.candidates_save(session["profile"], session["client"], 1)
        session["client"] = None
        return self.next(session, text)

    def from_favorite(self, session, text):
        if session['params'] is not None:
            if 'vk_id' in session['params']:
                self.db_session.candidates_del(session["profile"], session['params']['vk_id'])
        return {'text': 'Убрана'}

    def favorites(self, session, text):
        session["handler"] = None
        session["favorite_offset"] = 0
        return self.menu_favorites()

    def favorite_records(self, session):
        data = []
        res = self.db_session.favorite_load(
            session["profile"], session["favorite_offset"]
        )
        for rec in res:
            data.append(
                {
                    "text": f'{rec["last_name"]} {rec["first_name"]}\n https://vk.com/id{rec["vk_id"]}',
                    "attachment": rec["photos"],
                    "btn_in_mes": True,
                    "buttons": [[["Убрать из избранного",
                                  f'{{"command":"from_favorite", "params":{{"vk_id":{rec["vk_id"]} }}}}', "primary"]]],
                }
            )
        return data

    def favorites_prev_page(self, session, text):
        if session["favorite_offset"] > 10:
            session["favorite_offset"] -= 10
        if session["favorite_offset"] < 0:
            session["favorite_offset"] = 0
        return self.favorite_records(session)

    def favorites_next_page(self, session, text):
        data = self.favorite_records(session)
        if len(data) == 10:
            session["favorite_offset"] += 10
        return data

    def setting_del(self, session, text):
        session["handler"] = None
        return {
            "text": "Вы действительно хотите удалить профиль ?",
            "buttons": [
                [
                    ["Да", '{"command":"setting_del_yes"}', "primary"],
                    ["Нет", '{"command":"setting_del_no"}', "primary"],
                ],
                [["Отмена", '{"command":"settings_cancel"}', "primary"]],
            ],
        }

    def setting_del_yes(self, session, text):
        session["handler"] = None
        session['profile'].delete()
        session['profile'] = None
        return {
            "text": "Ваш профиль удален. До свидания",
            "buttons": [],
        }

    def setting_del_no(self, session, text):
        session["handler"] = None
        mes = self.menu_main()
        mes["text"] = f"Отлично {mes['text']}"
        return mes

