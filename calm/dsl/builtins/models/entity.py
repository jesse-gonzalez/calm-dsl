from collections import OrderedDict
import json
from json import JSONEncoder

from .schema import get_schema_props, get_validators_with_defaults


class EntityDict(OrderedDict):

    def __init__(self, validators):
        self.validators = validators

    def _check_name(self, name):
        if name not in self.validators:
            raise TypeError("Unknown attribute {} given".format(name))

    def _validate(self, name, value):

        if not (name.startswith('__') and name.endswith('__')):
            self._check_name(name)
            ValidatorType, is_array = self.validators[name]
            if ValidatorType is not None:
                ValidatorType.validate(value, is_array)

    def __setitem__(self, name, value):

        self._validate(name, value)
        super().__setitem__(name, value)


class EntityType(type):

    __schema_name__ = None

    @classmethod
    def __prepare__(mcls, name, bases, **kwargs):

        schema_name = mcls.__schema_name__

        # Handle base case (Entity)
        if not schema_name:
            return dict()

        # Check if validators were already set during previous class creation.
        # If yes, then do not set validators again; just return entity dict.

        if not hasattr(mcls, '__validator_dict__'):

            # Set validator type on metaclass for each prop.
            # To be used during __setattr__() to validate props.
            # Look at validate() for details.

            schema_props = get_schema_props(schema_name)
            validators, defaults = get_validators_with_defaults(schema_props)

            # Attach schema properties, validators and defaults to metaclass
            setattr(mcls, "__schema_props__", schema_props)
            setattr(mcls, "__validator_dict__", validators)
            setattr(mcls, "__default_attrs__", defaults)

        else:
            validators = getattr(mcls, '__validator_dict__')

        # Class creation would happen using EntityDict() instead of dict().
        # This is done to add validations to class attrs during class creation.
        # Look at __setitem__ in EntityDict
        return EntityDict(validators)

    def lookup_validator_type(cls, name):
        # Use metaclass dictionary to get the right validator type
        return type(cls).__validator_dict__.get(name, None)

    def check_name(cls, name):
        if name not in type(cls).__schema_props__:
            raise TypeError("Unknown attribute {} given".format(name))

    def validate(cls, name, value):

        if not (name.startswith('__') and name.endswith('__')):
            cls.check_name(name)
            ValidatorType, is_array = cls.lookup_validator_type(name)
            ValidatorType.validate(value, is_array)

    def __setattr__(cls, name, value):

        # Validate attribute
        cls.validate(name, value)

        # Set attribute
        super().__setattr__(name, value)

    def __str__(cls):
        return cls.__name__

    def get_user_attrs(cls):
        user_attrs = {}
        user_attrs["name"] = cls.__name__
        user_attrs["description"] = cls.__doc__ if cls.__doc__ else ''
        for name, value in cls.__dict__.items():
            if not (name.startswith('__') and name.endswith('__')):
                user_attrs[name] = value

        return user_attrs

    def get_default_attrs(cls):
        return type(cls).__default_attrs__

    def json_repr(cls):

        default_attrs = cls.get_default_attrs()
        user_attrs = cls.get_user_attrs()

        # Merge both attrs. Overwrite user attrs on default attrs
        return {**default_attrs, **user_attrs}

    def json_dumps(cls, pprint=False, sort_keys=False):
        return json.dumps(cls.json_repr(),
                          cls=EntityJSONEncoder,
                          sort_keys=sort_keys,
                          indent=4 if pprint else None,
                          separators=(",", ": ") if pprint else (",", ":"))


class Entity(metaclass=EntityType):
    pass


class EntityJSONEncoder(JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'json_repr'):
            return obj.json_repr()
        else:
            return super().default(obj)
