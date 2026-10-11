from typing import Any

from pydantic import BaseModel


class ErrorTarget(BaseModel):
    kind: str
    id: str | None = None


class ErrorBody(BaseModel):
    code: str
    message: str
    target: ErrorTarget | None = None
    next_action: str | None = None
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class DomainError(Exception):
    """Typed failure: safe message, target and the next resolvable action."""

    def __init__(self, status: int, code: str, message: str, *, target: tuple[str, Any] | None = None,
                 next_action: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message
        self.target, self.next_action, self.details = target, next_action, details

    def body(self) -> dict:
        target = {"kind": self.target[0], "id": str(self.target[1]) if self.target[1] is not None else None} if self.target else None
        return {"error": {"code": self.code, "message": self.message, "target": target,
                          "next_action": self.next_action, "details": self.details}}


def not_permitted(message: str, **kw) -> DomainError:
    return DomainError(403, "actor_not_permitted", message, **kw)


def not_found(kind: str, id_: Any) -> DomainError:
    return DomainError(404, "not_found", f"{kind} was not found in this workspace.", target=(kind, id_))


def stale(message: str, **kw) -> DomainError:
    return DomainError(409, kw.pop("code", "stale_target"), message, **kw)


def blocked(code: str, message: str, **kw) -> DomainError:
    return DomainError(422, code, message, **kw)
