from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import JSON, select
from sqlalchemy.orm import Session


ModelType = TypeVar("ModelType")


class RecordNotFoundError(LookupError):
    def __init__(self, model: type, record_id: Any):
        super().__init__(f"{model.__name__} record {record_id!r} was not found")
        self.model = model
        self.record_id = record_id


class Repository(Generic[ModelType]):
    def __init__(
        self,
        session: Session,
        model: type[ModelType],
        create_schema: type[BaseModel],
        update_schema: type[BaseModel],
        *,
        relationships: dict[str, tuple[str, type]] | None = None,
    ):
        self.session = session
        self.model = model
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.relationships = relationships or {}

    def create(self, data: BaseModel | dict[str, Any]) -> ModelType:
        values = self._dump(self.create_schema, data)
        values = self._normalize_json_values(values)
        relationship_values = self._resolve_relationships(values)
        record = self.model(**values, **relationship_values)
        self.session.add(record)
        self.session.flush()
        return record

    def get(self, record_id: Any) -> ModelType:
        record = self.session.get(self.model, record_id)
        if record is None:
            raise RecordNotFoundError(self.model, record_id)
        return record

    def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        if offset < 0 or limit < 1:
            raise ValueError("offset must be non-negative and limit must be positive")
        statement = select(self.model)
        for name, value in (filters or {}).items():
            column = getattr(self.model, name, None)
            if column is None or name not in self.model.__table__.columns:
                raise ValueError(f"{name!r} is not a filterable {self.model.__name__} field")
            statement = statement.where(column == value)
        statement = statement.order_by(self.model.id).offset(offset).limit(limit)
        return list(self.session.scalars(statement))

    def update(self, record_id: Any, data: BaseModel | dict[str, Any]) -> ModelType:
        record = self.get(record_id)
        changes = self._dump(self.update_schema, data)
        changes = self._normalize_json_values(changes)
        merged = self._current_values(record)
        merged.update(changes)
        self.create_schema.model_validate(merged)

        relationship_values = self._resolve_relationships(changes)
        for name, value in changes.items():
            if name not in self.relationships:
                setattr(record, name, value)
        for name, value in relationship_values.items():
            setattr(record, name, value)
        self.session.flush()
        return record

    def delete(self, record_id: Any) -> None:
        record = self.get(record_id)
        self.session.delete(record)
        self.session.flush()

    def _current_values(self, record: ModelType) -> dict[str, Any]:
        schema_fields = set(self.create_schema.model_fields)
        values = {
            attribute.key: getattr(record, attribute.key)
            for attribute in self.model.__mapper__.column_attrs
            if attribute.key in schema_fields
            if attribute.key not in {
                column.key for column in self.model.__mapper__.primary_key
            }
        }
        for input_name, (relationship_name, _) in self.relationships.items():
            if input_name not in schema_fields:
                continue
            related = getattr(record, relationship_name)
            if isinstance(related, list):
                values[input_name] = [item.id for item in related]
            else:
                values[input_name] = related.id if related is not None else None
        return values

    def _resolve_relationships(self, values: dict[str, Any]) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for input_name, (relationship_name, related_model) in self.relationships.items():
            if input_name not in values:
                continue
            ids = values.pop(input_name)
            if ids is None:
                if self.model.__mapper__.relationships[relationship_name].uselist:
                    raise ValueError(f"{input_name} cannot be null; use an empty list")
                resolved[relationship_name] = None
                continue
            if isinstance(ids, list):
                if len(ids) != len(set(ids)):
                    raise ValueError(f"{input_name} must not contain duplicate IDs")
                related = [self._get_related(related_model, item_id) for item_id in ids]
            else:
                related = self._get_related(related_model, ids)
            resolved[relationship_name] = related
        return resolved

    def _normalize_json_values(self, values: dict[str, Any]) -> dict[str, Any]:
        for name, value in list(values.items()):
            property_ = self.model.__mapper__.column_attrs.get(name)
            if (
                property_ is not None
                and property_.columns
                and isinstance(property_.columns[0].type, JSON)
            ):
                values[name] = self._json_safe(value)
        return values

    @classmethod
    def _json_safe(cls, value: Any) -> Any:
        if isinstance(value, BaseModel):
            return cls._json_safe(value.model_dump())
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: cls._json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [cls._json_safe(item) for item in value]
        return value

    def _get_related(self, related_model: type, record_id: Any) -> Any:
        record = self.session.get(related_model, record_id)
        if record is None:
            raise RecordNotFoundError(related_model, record_id)
        return record

    @staticmethod
    def _dump(schema_type: type[BaseModel], data: BaseModel | dict[str, Any]) -> dict[str, Any]:
        if isinstance(data, BaseModel):
            return schema_type.model_validate(data.model_dump(exclude_unset=True)).model_dump(
                exclude_unset=True
            )
        return schema_type.model_validate(data).model_dump(exclude_unset=True)
