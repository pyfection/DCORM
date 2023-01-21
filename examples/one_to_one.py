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
class User(Model):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field()
    profile: 'Profile' = Field(backref="user")


@register(db=db)
class Profile(Model):
    id: UUID = Field(default_factory=uuid4)
    user: User = Field(backref="profile")
    bio: str = Field()


profile = Profile(bio="Hi there, this is my profile")
user = User(name="Bob", profile=profile)

# user = User(name="Bob"profile)
# profile = Profile(bio="Hi there, this is my profile", user=user)

# user = User(name="Bob")
# user.profile = Profile(bio="Hi there, this is my profile")

# profile = Profile(bio="Hi there, this is my profile")
# profile.user = User(name="Bob")

# Save into database
user.save()
profile.save()


# ToDo: get multiple objects from DB
# User.find(name="Bob")
# User.find(name="Bob", limit=10)


# Get one object from DB
user2 = User.get(name="Bob")
print(user2)
print(user2.profile)


# When model is loaded from DB, it's cached
# assert user is user2
# assert profile is user2.profile
