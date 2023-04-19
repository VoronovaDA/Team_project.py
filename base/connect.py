import sqlalchemy as sq
from sqlalchemy.orm import sessionmaker

from base.create_table import create_tables, Profiles, Relationship, Settings
from base.settings import db_name, db_password, db_users

DSN = f"postgresql://{db_users}:{db_password}@localhost:5432/{db_name}"
engine = sq.create_engine(DSN)

create_tables(engine)

Session = sessionmaker(bind=engine)
session = Session()


class Database:
    def profile_save(self, profile):
        if (
                session.query(Profiles).filter(Profiles.vk_id == profile.vk_id).first()
                is None
        ):
            session.add(
                Profiles(
                    vk_id=profile.vk_id,
                    first_name=profile.first_name,
                    last_name=profile.last_name,
                    age=profile.age,
                    sex=profile.sex,
                    city=profile.city,
                    photos=profile.photos
                )
            )
        else:
            prof = session.query(Profiles) \
                .filter(Profiles.vk_id == profile.vk_id) \
                .first()
            prof.vk_id = profile.vk_id
            prof.first_name = profile.first_name
            prof.last_name = profile.last_name
            prof.age = profile.age
            prof.sex = profile.sex
            prof.city = profile.city
            prof.photos = profile.photos
        session.commit()

    def profile_load(self, vk_ids: int):
        data = None
        res = session.query(Profiles).filter(Profiles.vk_id == vk_ids).first()
        if res is not None:
            data = {
                "vk_id": res.vk_id,
                "first_name": res.first_name,
                "last_name": res.last_name,
                "age": res.age,
                "sex": res.sex,
                "city": res.city,
                "photos": res.photos
            }
        return data

    def profile_del(self, profile):
        session.query(Profiles).filter(Profiles.vk_id == profile.vk_id).delete()
        session.query(Relationship).filter(Relationship.vk_id == profile.vk_id).delete()
        session.query(Settings).filter(Settings.vk_id == profile.vk_id).delete()

    def offset_load(self, profile):
        res = (
            session.query(Settings.offset)
            .filter(Settings.vkid_profile == profile.vk_id)
            .first()
        )
        return res.offset if res is not None else None

    def offset_save(self, profile, value):
        session.query(Settings.offset) \
            .filter(Settings.vkid_profile == profile.vk_id) \
            .first().offset = value
        session.commit()

    def candidates_save(self, profile, client, flag=2):
        if (
                session.query(Relationship)
                        .filter(Relationship.vkid_profile == profile.vk_id)
                        .filter(Relationship.vkid_candidate == client.vk_id)
                        .all()
        ):
            session.add(Relationship(profile.vk_id, client.vk_id, flag))
            session.commit()

    def candidates_check(self, profile, client):
        res = (
            session.query(Relationship)
            .filter(Relationship.vkid_candidate == profile.vk_id)
            .filter(Relationship.vkid_profile == client.vk_id)
            .first()
        )
        if res is None:
            return None
        else:
            return res.flag

    def candidates_del(self, profile, client):
        session.query(Relationship.offset) \
            .filter(Relationship.vkid_profile == profile.vk_id) \
            .filter(Relationship.vkid_candidate == client.vk_id) \
            .first().flag = 2
        session.commit()

    def favorite_load(self, profile, offset, limit=10):
        data = []
        result = (
            session.query(
                Relationship.vkid_profile,
                Profiles.first_name,
                Profiles.last_name,
                Profiles.photos,
            )
            .join(Profiles)
            .join(Relationship)
            .filter(Relationship.vkid_profile == profile.vk_id)
            .filter(Relationship.flag == 1)
            .limit(limit)
            .offset(offset)
            .all()
        )
        for item in result:
            data.append(
                {
                    "vk_id": item.vk_id,
                    "first_name": item.first_name,
                    "last_name": item.last_name,
                    "photos": item.photos,
                }
            )
        return data

    def token_load(self, profile):
        res = (
            session.query(Settings.token)
            .filter(Settings.vkid_profile == profile.vk_id)
            .first()
        )
        return res.token if res is not None else None

    def token_save(self, vk_id, token):
        session.query(Settings.token).filter(
            Settings.vkid_profile == vk_id
        ).first().token = token
        session.commit()
