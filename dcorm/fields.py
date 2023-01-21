from dataclasses import dataclass, field
from typing import Any, Type, Callable, get_type_hints


@dataclass
class Field:
    default: Any = None
    default_factory: Callable = None
    null: bool = False
    backref: str = None
    model = None
    _value = None

    def __set_name__(self, owner, name):
        self._owner = owner
        self._name = name

    def __set__(self, instance, value):
        from dcorm import Model

        save_relation = False

        if value is None:
            if self.default:
                value = self.default
            elif self.default_factory:
                value = self.default_factory()
                # ToDo: once #1 is solved, remove next two lines
                if isinstance(value, Model):
                    save_relation = True
        self._value = value

        if not issubclass(value.__class__, Model):
            return

        type_hints = get_type_hints(
            value.__class__, locals() | Model._model_clss
        )
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
        if save_relation:
            self._value.save()

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

        type_hints = get_type_hints(
            other.__class__, locals() | self.model._model_clss
        )
        type_hint = type_hints[self.backref]
        list_model_types = (
            list[self._model_class], list[self._model_class.__name__]
        )
        if type_hint in list_model_types:
            # many-to-many relationship
            other_collection = getattr(other, self.backref)
            if self.model not in other_collection:
                other_collection.append(self.model)
            ...
        elif type_hint is self._model_class:
            # many-to-one relationship
            setattr(other, self.backref, self.model)
        else:
            raise ValueError("Backref isn't of the right type")
