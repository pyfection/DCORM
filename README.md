# DCORM - Data Classs ORM

## Motivation
There are a lot of ORMs out there, but none of the
major ones fulfilled all my needs:
- Be Pythonic
- Easy to use
- Extendable

This ORM may be slower than other ORMs and also doesn't
have as many features, as it's still very much in
its infancy.

## Setting up the Database
This Creates the connection to the database.
```python
from dcorm.mappers.sqlite import SQLite3


db_name = "db.sqlite"
db = SQLite3(db_name)
```

## Creating models
Models can be created by inheriting from the basic class
`Model`. They also need to be decorated by the `@register`
decorator. This makes them valid dataclasses and also
registers the DB to use.

Type hints are mandatory, as they show what type fields
should be. `Field`s that have another model as type hint
have a one-way connection to the other model.

`Collection`s are a many-to relationship to the model
specified in the type annotation. The `backref` marks
which field it is connected to in the other model.
```python
from uuid import UUID, uuid4

from dcorm import Field, Collection, register


@register(db)
class User:
    id: UUID = Field(default_factory=uuid4)
    name: str = Field()
    class_: 'Class' = Field(null=True)


@register(db)
class Class:
    id: UUID = Field(default_factory=uuid4)
    users: list[User] = Collection(backref="class_")
    name: str = Field()
```

## Creating instances
Instances can simply be created like any other python dataclass.
Relations can be set or added and automatically set the backreferenc
on the related object too.
```python
user = User(name="Bob")
class_ = Class(name="1st Class")
class_.users.append(user)
# Also possible:
# user.class_ = class_
```

## Saving to the database
Saving to the database is as easy as just calling the method on
the instance.
```python
user.save()
class_.save()
```

## Getting an instance from the database
`get` returns the first match from the query. The query is connected
by an implicit `and`.
```python
user2 = User.get(name="Bob")
class_2 = Class.get(name="1st Class")
```

## Caching
Objects are automatically cached once they are loaded, which is
why these asserts don't raise an error.
```python
assert user is user2
assert class_ is class_2
```


## ToDo:
There are a lot of things still to do. Some of the planned features are:
- Get multiple objects from the database at once
- Deleting objects
- Support of functions for querying


For an entire example, have a look at https://github.com/pyfection/DCORM/blob/main/examples/complete.py