from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.services.command_service import CommandBase

__all__ = ["CommandBase", "CommandResult", "CommandTarget", "Revisioned", "NoteCreate", "NoteUpdate"]


class CommandTarget(BaseModel):
    kind: str
    id: str
    revision: int


class CommandResult(BaseModel):
    """Durable result of a committed command. `replayed` is true when a stored receipt was returned."""

    command_id: UUID
    action: str
    sequence: int
    target: CommandTarget | None
    data: dict[str, Any]
    replayed: bool


class Revisioned(CommandBase):
    expected_revision: int


class NoteCreate(CommandBase):
    text: str


class NoteUpdate(Revisioned):
    text: str | None = None
    status: str | None = None
