from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, get_type_hints


@dataclass
class Field:
    default: Any = None
    default_factory: Callable = None
    null: bool = False
    backref: str = None

    def __set_name__(self, owner, name):
        self._owner = owner
        self._name = name

    def __set__(self, instance, value):
        from dcorm import Model

        type_hint = get_type_hints(
            instance.__class__, locals() | Model._model_clss
        )[self._name]

        # Set default values
        if value is None:
            if self.default is not None:
                value = self.default
            elif self.default_factory:
                # This may also create a Model
                value = self.default_factory()
            else:  # Figure out sensible value
                if type_hint in (str, int, float, bool):
                    value = type_hint()

        # Convert values if necessary, such as str to UUID
        if value is None:
            # Don't convert
            pass
        elif issubclass(type_hint, Model):
            # Is a relationship
            rel_type_hint = get_type_hints(
                type_hint, locals() | Model._model_clss
            )["id"]
            if isinstance(value, Model):
                # relationship is already set
                pass
            elif rel_type_hint is not type(value):
                # Relationship not set yet
                # Will be properly set on post init of model
                value = rel_type_hint(value)
        elif type_hint is not type(value):
            if issubclass(type_hint, datetime):
                value = datetime.fromtimestamp(value)
            else:
                value = type_hint(value)

        # Save value to instance
        instance._descriptor_values[self._name] = value
        instance._has_unsaved_changes = True

        if not issubclass(value.__class__, Model):
            return

        type_hints = get_type_hints(
            value.__class__, locals() | Model._model_clss
        )
        name = self.backref or instance.__class__.__name__.lower()
        descriptor = getattr(value, name, None)
        if isinstance(descriptor, Collection):
            # Set back relationship one-to-many
            if instance not in descriptor:
                descriptor.append(instance)
        else:  # Try to get Field backref
            try:
                descriptor = value.fields()[name]
            except KeyError:
                pass  # No back reference
            else:
                # Set back relationship
                if isinstance(descriptor, Field):
                    if getattr(value, name) is not instance:
                        setattr(value, name, instance)
                else:
                    raise ValueError("Backref of wrong format")  # ToDo: improve error

    def __get__(self, instance, owner):
        try:
            return instance._descriptor_values[self._name]
        except (AttributeError, KeyError):
            return None


@dataclass
class Collection:
    backref: str
    relationships: list = field(default_factory=list)
    model = None

    def __set_name__(self, owner, name):
        self._model_class = owner
        self._field_name = name

    def __getitem__(self, item):
        return self.relationships[item]

    def __contains__(self, item):
        return item in self.relationships

    def __len__(self):
        return len(self.relationships)

    def __iter__(self):
        return iter(self.relationships)

    def remove(self, item):
        self.relationships.remove(item)
        if self.backref in item.fields():
            setattr(item, self.backref, None)
        elif self.backref in item.collections():
            collection = getattr(item, self.backref)
            if self in collection:
                collection.remove(self)
        self.model._has_unsaved_changes = True

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

        elif type_hint is self._model_class:
            # many-to-one relationship
            setattr(other, self.backref, self.model)
        else:
            raise ValueError("Backref isn't of the right type")
        self.model._has_unsaved_changes = True
