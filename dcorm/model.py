from copy import deepcopy
from dataclasses import _process_class
from typing import get_type_hints, get_args, Any

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
    _has_unsaved_changes = False

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
            is_field = isinstance(self.fields()[attr], Field)
            if value is not None and is_field:
                is_set = isinstance(value, type_hint)
                # is_set is inside this if, because it will raise erros if type
                # hint is something like list[Model]
                if not is_set and issubclass(type_hint, Model):
                    # Load relationship
                    relation = getattr(self, attr)
                    if getattr(relation, "id", None) is not value:
                        # Only set if it's not set already
                        relation = type_hint.get(id=value)
                        setattr(self, attr, relation)
            elif isinstance(value, Collection):
                value = deepcopy(value)
                setattr(self, attr, value)
                value.model = self
                # Load relationships
                th = get_args(type_hint)[0]
                filters = {value.backref: self.id}
                # Adding the relationships found to the collection is automatic
                # through the relation finding of the related field
                for rel in th.find(**filters):
                    if rel not in value:
                        value.append(rel)

    @classmethod
    def from_json(cls, **data):
        return cls(**data)

    @classmethod
    def fields(cls) -> dict[str, Any]:
        return {
            key: value
            for cls_ in cls.mro()[::-1]
            for key, value in cls_.__dict__.items()
            if isinstance(value, Field)
        }

    @classmethod
    def find(cls, query=None, **filters):
        if query:
            raise NotImplementedError(
                "Function-like queries are not supported yet!"
            )

        instances_found = {}
        for instance in cls._cache:
            for key, value in filters.items():
                if getattr(instance, key) != value:
                    break
            else:
                instances_found[str(instance.id)] = instance

        raw_instances = cls._db.find(cls, query, **filters)
        for data in raw_instances:
            if data["id"] not in instances_found:
                instance = cls.from_json(**data)
                instance._in_db = True
                instances_found[data["id"]] = instance
        return list(instances_found.values())

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

        # ToDo: get data and load it with cls.from_json
        return cls._db.get(cls, query, **filters)

    @classmethod
    def all(cls):
        """All instances of this model."""
        return cls.find()

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
                        value = getattr(self, key)
                        if isinstance(value, Model):
                            yield value
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

    def save(self, *, exclude_ids=None):
        exclude_ids = exclude_ids or []
        if self.savable and self.id not in exclude_ids:
            if self._has_unsaved_changes:
                self._db.save(self)
                self._has_unsaved_changes = False
                self._in_db = True
            exclude_ids.append(self.id)
            for relation in self.relations:
                relation.save(exclude_ids=exclude_ids)

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
