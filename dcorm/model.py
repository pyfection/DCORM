from copy import deepcopy
from dataclasses import _process_class
from typing import get_type_hints

from dcorm import Field, Collection
from dcorm.mappers.base import Mapper


def register(
    db, *, init=True, repr=True, eq=True,
    order=False, unsafe_hash=False, frozen=False, match_args=True,
    kw_only=False, slots=False
):
    """Returns the same class as was passed in, with dunder methods
    added based on the fields defined in the class.

    Examines PEP 526 __annotations__ to determine fields.

    If init is true, an __init__() method is added to the class. If
    repr is true, a __repr__() method is added. If order is true, rich
    comparison dunder methods are added. If unsafe_hash is true, a
    __hash__() method function is added. If frozen is true, fields may
    not be assigned to after instance creation. If match_args is true,
    the __match_args__ tuple is added. If kw_only is true, then by
    default all fields are keyword-only. If slots is true, an
    __slots__ attribute is added.
    """

    def wrap(cls):
        return _register(
            cls, db, init, repr, eq, order, unsafe_hash,
            frozen, match_args, kw_only, slots
        )

    if not isinstance(db, Mapper):
        raise TypeError(
            "First argument of register needs to be a Mapper."
        )
    return wrap


class Model:
    _db = None  # Set by register decorator
    _model_clss = {}  # All registered model classes

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._cache = list()
        cls._in_db = False
        cls.savable = True
        cls._model_clss[cls.__name__] = cls
        return cls

    def __post_init__(self):
        self._cache.append(self)
        for attr, type_hint in get_type_hints(
            self.__class__, locals() | self._model_clss
        ).items():
            value = getattr(self, attr)
            if isinstance(value, Field) and issubclass(type_hint, Model):
                field = self.__class__.__dict__[attr]
            elif isinstance(value, Collection):
                value.model = self

    @classmethod
    def from_json(cls, **data):
        type_hints = get_type_hints(
            cls, locals() | cls._model_clss
        )
        for key, value in data.items():
            type_hint = type_hints[key]
            if type(value) is not type_hint:
                # Convert to annotated type
                data[key] = type_hint(value)

        return cls(**data)

    @classmethod
    def _fields(cls):
        return [
            key
            for cls_ in cls.mro()[::-1]
            for key, value in cls_.__dict__.items()
            if isinstance(value, Field)
        ]

    @classmethod
    def get(cls, query=None, **filters):
        if query:
            raise NotImplementedError(
                "Function-like queries are not supported yet!"
            )

        for instance in cls._cache:
            for key, value in filters.items():
                if getattr(instance, key) != value:
                    break
            else:
                return instance

        return cls._db.get(cls, query, **filters)

    @property
    def table_name(self):
        return self.__class__.__name__.lower()

    @property
    def relations(self):
        for cls_ in self.__class__.mro()[::-1]:
            for key, type_ in cls_.__dict__.items():
                if isinstance(type_, Field):
                    type_hints = get_type_hints(
                        self, locals() | self._model_clss
                    )
                    if issubclass(type_hints[key], Model):
                        yield getattr(self, key)
                elif isinstance(type_, Collection):
                    relations = getattr(self, key).relationships
                    for relation in relations:
                        yield relation

    def clone(self, savable=False):
        """Creates a clone of this model instance."""
        # ToDo: consider how to clone relationships
        copy = deepcopy(self)
        copy.savable = savable
        return copy

    def save(self):
        if self.savable:
            self._db.save(self)
            self._in_db = True
            for relation in self.relations:
                if not relation._in_db:
                    relation.save()

        # ToDo: throw error for else


def _register(
    cls, db, init, repr, eq, order, unsafe_hash,
    frozen, match_args, kw_only, slots
):
    cls = _process_class(
        cls, init, repr, eq, order, unsafe_hash,
        frozen, match_args, kw_only, slots
    )
    cls._db = db
    __old_init__ = cls.__init__
    def __pre_init__(inst, *args, **kwargs):
        inst._descriptor_values = {}
        __old_init__(inst, *args, **kwargs)
    cls.__init__ = __pre_init__
    db.create(cls)
    return cls
