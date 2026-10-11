import uuid
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, ForeignKeyConstraint, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, mapped_column


class Base(DeclarativeBase):
    pass


def uid(nullable: bool = True, **kw):
    return mapped_column(PGUUID(as_uuid=True), nullable=nullable, **kw)


def txt(nullable: bool = True, **kw):
    return mapped_column(Text, nullable=nullable, **kw)


def req(**kw):
    return mapped_column(Text, nullable=False, **kw)


def num(default: int | None = None, nullable: bool = True):
    return mapped_column(Integer, default=default, nullable=nullable)


def flag(default: bool = False):
    return mapped_column(Boolean, default=default, nullable=False)


def ts(nullable: bool = True, **kw):
    return mapped_column(DateTime(timezone=True), nullable=nullable, **kw)


def jlist():
    return mapped_column(JSONB, default=list, nullable=False, info={"py": list[Any]})


def jdict(nullable: bool = False):
    return mapped_column(JSONB, default=None if nullable else dict, nullable=nullable, info={"py": dict[str, Any]})


def ref(table: str, column: str) -> ForeignKeyConstraint:
    """Container-scoped reference: a record can only point inside its own workspace container."""
    return ForeignKeyConstraint(["container_id", column], [f"{table}.container_id", f"{table}.id"],
                                deferrable=True, initially="IMMEDIATE", name=f"fk_{column}_{table}")


class Record(Base):
    """Workspace-container scoped record. `id` is the stable logical identity preserved by archives."""

    __abstract__ = True
    kind: str = "record"

    container_id = mapped_column(PGUUID(as_uuid=True), ForeignKey("workspace_containers.id", ondelete="CASCADE"), primary_key=True)
    id = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    revision = mapped_column(Integer, default=1, nullable=False)
    recorded_seq = mapped_column(BigInteger, default=0, nullable=False)
    recorded_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    recorded_by = mapped_column(PGUUID(as_uuid=True), nullable=True)
    recorded_by_name = mapped_column(Text, nullable=True)
