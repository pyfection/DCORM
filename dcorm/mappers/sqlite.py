import sqlite3
from sqlite3 import OperationalError
from typing import Type
from uuid import UUID

from dcorm import Model
from dcorm.mappers.base import Mapper


class SQLite3(Mapper):
    def __init__(self, db_path):
        self.db_path = db_path
        self.con = sqlite3.connect(db_path)
        self.cur = self.con.cursor()
        self.types_map = {
            UUID: str,
        }

    def get(self, model_cls: Type[Model], query=None, **filters):
        table = model_cls.__name__.lower()
        type_mapper = {
            UUID: str,
        }
        filters_ = {
            k: type_mapper.get(type(v), lambda v_: v_)(v)
            for k, v in filters.items()
        }
        filters_ = ", ".join(
            f"{k}={repr(v)}" for k, v in filters_.items()
        )
        sql = "\n".join((
            "SELECT *"
            f"FROM {table}",
            f"WHERE {filters_}",
        ))
        res = self.cur.execute(sql)
        data = res.fetchone()
        if not data:
            return None
        data = dict(zip(model_cls._fields(), data))
        model = model_cls.from_json(**data)
        model._in_db = True
        return model

    def create(self, model: Type[Model]):
        attrs = list(model._fields())
        table = model.__name__.lower()
        try:
            self.cur.execute(
                f"CREATE TABLE {table}{str(tuple(attrs))}"
            )
        except OperationalError:
            pass  # Table already exists

    def save(self, model: Model):
        table = model.table_name
        attrs = list(model._fields())
        if model._in_db:
            attrs.remove("id")
        data = [getattr(model, attr) for attr in attrs]
        data = [
            value.id if isinstance(value, Model) else value
            for value in data
        ]
        # Converting
        data = [
            self.types_map.get(
                type(value), lambda v: v
            )(value)
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
        self.cur.execute(sql)
        self.con.commit()
