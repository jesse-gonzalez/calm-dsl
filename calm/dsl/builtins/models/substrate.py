from .entity import EntityType, Entity
from .validator import PropertyValidator


# Substrate

class SubstrateType(EntityType):
    __schema_name__ = "Substrate"


class Substrate(Entity, metaclass=SubstrateType):
    pass


def substrate(**kwargs):
    return SubstrateType("", (Entity, ), kwargs)


class SubstrateValidator(PropertyValidator, openapi_type="substrate"):

    __default__ = None
    __kind__ = SubstrateType
