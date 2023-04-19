import time
import requests
import time
import requests
from vk_profile import VkUser


class VkSearch:
    url = "https://api.vk.com/method"

    def __init__(self, profile, db_session):
        self.params = {"access_token": profile.token, "v": "5.131"}
        self.profile = profile
        self.db_session = db_session

    def search(self):
        params = {
            "age_from": self.profile.age - 2,
            "age_to": self.profile.age + 2,
            "sex": 1 if self.profile.sex == 2 else 2,
            "city_id": self.profile.city,
            "status": 1,
            "has_photo": 1,
            "offset": self.profile.get_offset(),
            "count": 1,
        }
        time.sleep(0.5)
        response = requests.get(
            f"{self.url}/users.search", params={**self.params, **params}
        ).json()
        return response["response"]["items"][0]

    def next(self):
        client = None
        if self.params["access_token"] is None:
            return client
        while True:
            result = self.search()
            if result["is_closed"]:
                continue
            client = VkUser(
                self.db_session, result["id"], self.params["access_token"]
            )
            client.photo_update()
            if (
                self.db_session.candidates_check(self.profile, client)
                is not None
            ):
                continue
            break
        return client