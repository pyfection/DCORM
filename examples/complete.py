import os
from uuid import UUID, uuid4

from dcorm import Field, Collection, register, Model
from dcorm.mappers.sqlite import SQLite3


# Create and connect to database
db_name = "db.sqlite"
try:
    os.remove(db_name)
except FileNotFoundError:
    pass
db = SQLite3(db_name)


# Create Models
@register(db)
class User(Model):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field()
    class_: 'Class' = Field(null=True)


@register(db)
class Class(Model):
    id: UUID = Field(default_factory=uuid4)
    users: list[User] = Collection(backref="class_")
    name: str = Field()


user = User(name="Bob")
class_ = Class(name="1st Class")
print("Collection relation")
# user.class_ = class_
class_.users.append(user)
print("Done")


# Save into database
user.save()
# class_.save()


# ToDo: get multiple objects from DB
# User.find(name="Bob")
# User.find(name="Bob", limit=10)


# Get one object from DB
user2 = User.get(name="Bob")
class_2 = Class.get(name="1st Class")


# When model is loaded from DB, it's cached
assert user is user2
assert class_ is class_2


# ToDo: pre-loading (keeps model instances in cache forever)
# User.pre_load()


# ToDo: deleting entries


# ToDo: support lambda function in get/find
