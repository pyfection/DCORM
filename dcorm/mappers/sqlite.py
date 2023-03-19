import sqlite3
from datetime import datetime
from enum import Enum
from sqlite3 import OperationalError
from typing import Type, Iterator
from uuid import UUID

from dcorm import Model
from dcorm.mappers.base import Mapper


class SQLite3(Mapper):
    def __init__(self, db_path):
        self.db_path = db_path
        self.con = sqlite3.connect(db_path)
        self.cur = self.con.cursor()

    def _serealize_type(self, value):
        if isinstance(value, UUID):
            return str(value)
        elif isinstance(value, Enum):
            return value.value
        elif isinstance(value, datetime):
            return value.timestamp()
        return value

    def _filter(self, model_cls: Type[Model], **filters):
        table = model_cls.__name__.lower()

        filters_ = {
            k: self._serealize_type(v)
            for k, v in filters.items()
        }
        filters_ = " AND ".join(
            f"'{k}'={repr(v)}" for k, v in filters_.items()
        )
        sql = "\n".join((
            "SELECT *"
            f"FROM {table}",
            f"WHERE {filters_}" if filters_ else "",
        ))
        try:
            return self.cur.execute(sql)
        except OperationalError as exc:
            raise OperationalError(f"Bad format '{sql}'") from exc

    def get(self, model_cls: Type[Model], query=None, **filters) -> Model:
        # ToDo: return data instead of Model
        res = self._filter(model_cls, **filters)
        data = res.fetchone()
        if not data:
            return None
        data = dict(zip(model_cls.fields().keys(), data))
        model = model_cls.from_json(**data)
        model._in_db = True
        return model

    def find(self, model_cls: Type[Model], query=None, **filters) -> Iterator[Model]:
        res = self._filter(model_cls, **filters)
        datas = res.fetchall()
        for data in datas:
            data = dict(zip(model_cls.fields().keys(), data))
            yield data

    def create(self, model: Type[Model]):
        attrs = list(model.fields().keys())
        table = model.__name__.lower()
        try:
            self.cur.execute(
                f"CREATE TABLE {table}{str(tuple(attrs))}"
            )
        except OperationalError:
            pass  # Table already exists

    def save(self, model: Model):
        table = model.table_name
        attrs = list(model.fields().keys())
        if model._in_db:
            attrs.remove("id")
        data = [getattr(model, attr) for attr in attrs]
        data = [
            value.id if isinstance(value, Model) else value
            for value in data
        ]
        # Converting
        data = [
            self._serealize_type(value)
            for value in data
        ]
        if model._in_db:
            sql = "\n".join((
                f"UPDATE {table}",
                "SET",
                " , ".join(
                    f"{attr} = {repr(value)}"
                    for attr, value in zip(attrs, data)
                ),
                f"WHERE id = {repr(str(model.id))}",
            ))
        else:
            sql = "\n".join((
                f"INSERT INTO {table}",
                f"VALUES {tuple(data)}"
            ))
        sql = sql.replace("None", "NULL")
        self.cur.execute(sql)
        self.con.commit()
