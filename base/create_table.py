import sqlalchemy as sq
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def create_tables(engine):
    Base.metadata.create_all(engine)


class Profiles(Base):
    __tablename__ = 'profiles'

    vk_id = sq.Column(sq.Integer, primary_key=True)
    first_name = sq.Column(sq.String)
    last_name = sq.Column(sq.String)
    age = sq.Column(sq.Integer)
    sex = sq.Column(sq.Integer)
    city = sq.Column(sq.String)
    photos = sq.Column(sq.String, unique=True)


class Relationship(Base):
    __tablename__ = 'relationship'

    id = sq.Column(sq.Integer, primary_key=True)
    vkid_profile = sq.Column(sq.Integer, sq.ForeignKey("profiles.vk_id"), nullable=False)
    vkid_candidate = sq.Column(sq.Integer, nullable=False)
    flag = sq.Column(sq.Integer)

    pr = relationship('Profiles', backref='relationship')


class Settings(Base):
    __tablename__ = 'settings'

    id = sq.Column(sq.Integer, primary_key=True)
    vkid_profile = sq.Column(sq.Integer, sq.ForeignKey("profiles.vk_id"), nullable=False)
    token = sq.Column(sq.String, unique=True)
    offset = sq.Column(sq.Integer)

    pr = relationship('Profiles', backref='settings')
