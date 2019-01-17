import sqlalchemy as db
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


Base = declarative_base()


class Round(Base):
    __tablename__ = 'rounds'

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True)
    completed = db.Column(db.Boolean, default=False)
    start = db.Column(db.DateTime, server_default=func.current_timestamp())
    finish = db.Column(db.DateTime)

    def __init__(self, number):
        self.number = number


class Team(Base):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(191), unique=True)
    enabled = db.Column(db.Boolean, default=True)
    check_team = db.Column(db.Boolean, default=False)

    def __init__(self, name, check_team=None):
        self.name = name
        if check_team is not None:
            self.check_team = check_team

    def __repr__(self):
        return (
            'Team(id={id}, name={name!r}, enabled={enabled}, check_team={check_team})'
        ).format_map(self.__dict__)


class Service(Base):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(191), unique=True)
    group = db.Column(db.String(191))
    check = db.Column(db.String(191))
    enabled = db.Column(db.Boolean, default=True)

    def __init__(self, name, group, check):
        self.name = name
        self.group = group
        self.check = check

    def __repr__(self):
        return (
            'Service(id={id}, name={name!r}, group={group}, check={check}, enabled={enabled})'
        ).format_map(self.__dict__)


class TeamService(Base):
    __tablename__ = 'team_service'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'))
    key = db.Column(db.String(191))
    value = db.Column(db.Text)
    edit = db.Column(db.Boolean, default=True)
    hidden = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)

    team = relationship('Team', lazy='joined')
    service = relationship('Service', lazy='joined')

    def __init__(self, team, service, key, value, edit=None, hidden=None, order=None):
        self.team = team
        self.service = service
        self.key = key
        self.value = value
        if edit is not None:
            self.edit = edit
        if hidden is not None:
            self.hidden = hidden
        if order is not None:
            self.order = order


class Check(Base):
    __tablename__ = 'checks'

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'))
    round = db.Column(db.Integer)
    time = db.Column(db.DateTime, server_default=func.now())
    passed = db.Column(db.Boolean)
    output = db.Column(db.Text)

    team = relationship('Team')
    service = relationship('Service')
