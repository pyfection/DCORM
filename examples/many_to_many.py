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
class Human(Model):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field()
    pets: list['Pet'] = Collection(backref="humans")


@register(db)
class Pet(Model):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field()
    humans: list[Human] = Collection(backref="pets")


owner1 = Human(name="Bob")
owner2 = Human(name="Bertha")
pet1 = Pet(name="Doggo")
pet2 = Pet(name="Caty")

owner1.pets.append(pet1)
owner1.pets.append(pet2)
owner2.pets.append(pet1)
print("Done")


# Save into database
owner1.save()
owner2.save()
pet1.save()
pet2.save()


# # Get one object from DB
# user2 = User.get(name="Bob")
# class_2 = Class.get(name="1st Class")
#
#
# # When model is loaded from DB, it's cached
# assert user is user2
# assert class_ is class_2
