import os
from uuid import UUID, uuid4

from dcorm import Field, register, Model
from dcorm.mappers.sqlite import SQLite3


# Create and connect to database
db_name = "db.sqlite"
try:
    os.remove(db_name)
except FileNotFoundError:
    pass
db = SQLite3(db_name)


# Create Models
@register(db=db)
class Profile(Model):
    id: UUID = Field(default_factory=uuid4)
    user: 'User' = Field(backref="profile")
    bio: str = Field(default="No bio")


@register(db=db)
class User(Model):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field()
    profile: 'Profile' = Field(backref="user", default_factory=Profile)


# profile = Profile(bio="test bio")
user = User(name="Bob")

# Save into database
user.save()
user.profile.save()


# Get one object from DB
user2 = User.get(name="Bob")
print(user2)
print(user2.profile)


# When model is loaded from DB, it's cached
# assert user is user2
# assert profile is user2.profile
