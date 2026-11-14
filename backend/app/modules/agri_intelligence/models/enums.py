from enum import Enum

from sqlalchemy import Enum as SQLAlchemyEnum


class EvidenceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PROVISIONAL = "PROVISIONAL"
    UNKNOWN = "UNKNOWN"
    UNDER_REVIEW = "UNDER_REVIEW"


class ApplicabilityMode(str, Enum):
    ALL_CROPS = "ALL_CROPS"
    CROP = "CROP"
    VARIETY = "VARIETY"
    FAMILY = "FAMILY"


class GeographicScopeType(str, Enum):
    GLOBAL = "GLOBAL"
    COUNTRY = "COUNTRY"
    PROVINCE_STATE = "PROVINCE_STATE"
    DISTRICT = "DISTRICT"
    LOCALITY = "LOCALITY"
    AGROECOLOGICAL_ZONE = "AGROECOLOGICAL_ZONE"
    FARM = "FARM"


class EvidenceOriginType(str, Enum):
    FARMER_PROVIDED = "FARMER_PROVIDED"
    DIRECTLY_MEASURED = "DIRECTLY_MEASURED"
    PUBLISHED_SOURCE = "PUBLISHED_SOURCE"


class RequirementType(str, Enum):
    SOIL = "soil"
    WATER = "water"
    TEMPERATURE = "temperature"
    SALINITY = "salinity"
    NUTRIENT = "nutrient"
    OTHER = "other"


def enum_column(enum_class: type[Enum], name: str) -> SQLAlchemyEnum:
    return SQLAlchemyEnum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda members: [member.value for member in members],
    )
