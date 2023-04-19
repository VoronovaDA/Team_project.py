import configparser

from base.connect import Database
from handler.user_handler import UserHandler

if __name__ == "__main__":
    ini = configparser.ConfigParser()
    ini.read("settings.ini")

    base = Database()
    uh = UserHandler(
        base,
        ini.getint("vk", "group_id"),
        ini.get("vk", "version"),
        ini.get("tokens", "vk_group"),
        ini.get("tokens", "vk_service")
    )