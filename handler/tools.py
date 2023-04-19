from datetime import date, datetime


def calculate_age(bdate):
    bdate = datetime.strptime(bdate, "%d.%m.%Y")
    today = date.today()
    age = (
        today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))
    )
    return age


def profile_vk_check(vk_profile):
    if "bdate" in vk_profile:
        if len(vk_profile["bdate"].split(".")) < 3:
            vk_profile["age"] = None
        else:
            vk_profile["age"] = calculate_age(vk_profile["bdate"])
        del vk_profile["bdate"]
    else:
        vk_profile["age"] = None

    if "sex" in vk_profile:
        if vk_profile["sex"] == 0:
            vk_profile["sex"] = None
    else:
        vk_profile["sex"] = None

    if "city" in vk_profile:
        vk_profile["city"] = vk_profile["city"]["id"]
    else:
        vk_profile["city"] = None

    return vk_profile


def profile_check(profile):
    err = ""
    if profile.token is None:
        err += " - Для использования поиска необходимо зарегистрироваться<br>"

    if profile.age is None:
        err += (
            " - Не удается определить Ваш возраст, так как скрыта дата рождения<br>"
        )

    if profile.sex is None:
        err += " - Не удается определить Ваш пол<br>"

    if profile.city is None:
        err += " - У Вас не указан город<br>"

    return (
        f"Есть ошибки: <br> {err} <br>Необходимо указать недостающие данные"
        if len(err) > 0
        else ""
    )
