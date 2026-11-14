from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import inspect


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReadSchema(Schema):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class UpdateSchema(Schema):
    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


SchemaType = TypeVar("SchemaType", bound=BaseModel)


def read_model(model: Any, schema_type: type[SchemaType], **relationships: Any) -> SchemaType:
    values = {
        attribute.key: getattr(model, attribute.key)
        for attribute in inspect(model).mapper.column_attrs
    }
    values.update(relationships)
    return schema_type.model_validate(values)
