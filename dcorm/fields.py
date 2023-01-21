from dataclasses import dataclass, field
from typing import Any, Type, Callable, get_type_hints


@dataclass
class Field:
    default: Any = None
    default_factory: Callable = None
    null: bool = False
    backref: str = None
    model = None
    _initialized = False

    def __call__(self, *args, **kwargs):
        self._initialized = True

    def __post_init__(self):
        self._value = None

        if self.default:
            self._value = self.default
        elif self.default_factory:
            self._value = self.default_factory()

    def __set_name__(self, owner, name):
        self._owner = owner
        self._name = name

    def __set__(self, instance, value):
        self._value = value
        from dcorm import Model
        if not issubclass(value.__class__, Model):
            return

        type_hints = get_type_hints(value.__class__)
        name = instance.__class__.__name__.lower()
        rel_cls = type_hints.get(name)
        if not rel_cls:
            name = f"{name}s"
            rel_cls = type_hints.get(name)
            if not rel_cls:
                raise ValueError("No backref found")  # ToDo: improve error
        descriptor = value.__class__.__dict__[name]
        if isinstance(descriptor, Collection):
            if self.model not in descriptor:
                descriptor.append(self.model)
        elif isinstance(descriptor, Field):
            if getattr(value, name) is not instance:
                setattr(value, name, instance)
        else:
            raise ValueError("Backref of wrong format")  # ToDo: improve error

    def __get__(self, instance, owner):
        return self._value


@dataclass
class Collection:
    backref: str
    relationships: list = field(default_factory=list)
    model = None

    def __set_name__(self, owner, name):
        self._model_class = owner
        self._field_name = name

    def __contains__(self, item):
        return item in self.relationships

    def __len__(self):
        return len(self.relationships)

    def __iter__(self):
        return iter(self.relationships)

    def append(self, other):
        self.relationships.append(other)

        type_hints = get_type_hints(other.__class__)
        if type_hints[self.backref] is not self._model_class:
            raise ValueError("Backref isn't of the right type")
        setattr(other, self.backref, self.model)
