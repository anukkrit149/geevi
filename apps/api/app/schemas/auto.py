"""Response schemas derived from the SQLAlchemy record tables.

Request schemas are hand-written and validated; read models mirror the stored columns so the
OpenAPI contract never drifts from the database. JSONB content can be refined with overrides.
"""
import datetime as dt
import decimal
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, create_model
from sqlalchemy import LargeBinary

from app.db.base import Base

_HIDDEN = {"container_id", "password_hash", "token_hash"}


def schema_for(model: type[Base], name: str | None = None, *, exclude: set[str] = frozenset(), **overrides: Any) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    for column in model.__table__.columns:
        if column.name in _HIDDEN or column.name in exclude or isinstance(column.type, LargeBinary):
            continue
        py = column.info.get("py")
        if py is None:
            try:
                py = column.type.python_type
            except NotImplementedError:
                py = Any
        if py not in (uuid.UUID, str, int, bool, float, dt.datetime, dt.date, decimal.Decimal) and "py" not in column.info:
            py = Any
        fields[column.name] = ((py | None, None) if column.nullable else (py, ...))
    for key, value in overrides.items():
        fields[key] = (value[0], ...)  # computed view fields are always supplied, so they are required in the contract
    return create_model(name or f"{model.__name__}Out", __config__=ConfigDict(from_attributes=True), **fields)
