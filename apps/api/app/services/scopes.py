"""Watch scopes (KTD4): revision counters for material a signed decision depends on.

A packet freezes the revisions of its watch set; the approval command re-reads them under the
workspace lock, so newly arrived relevant material cannot evade review merely by being absent
from an earlier read set. Unrelated writes (tasks, notes) never touch these scopes.
"""
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.models.sources import ScopeRevision
from app.services.command_service import Ctx


def patient_scope(patient_id: UUID | str, area: str) -> str:
    return f"patient/{patient_id}/{area}"


def bump(ctx: Ctx, key: str, change: dict[str, Any]) -> int:
    row = ctx.db.scalar(select(ScopeRevision).where(ScopeRevision.container_id == ctx.container_id, ScopeRevision.scope_key == key))
    detail = {**change, "actor": ctx.account.display_name, "sequence": ctx.seq}
    if row is None:
        row = ctx.new(ScopeRevision, scope_key=key, last_change=detail)
    else:
        ctx.touch(row)
        row.last_change = detail
    ctx.db.flush()
    return row.revision


def current(ctx: Ctx, keys: list[str]) -> dict[str, dict[str, Any]]:
    rows = {r.scope_key: r for r in ctx.db.scalars(select(ScopeRevision).where(
        ScopeRevision.container_id == ctx.container_id, ScopeRevision.scope_key.in_(keys or [""])))}
    return {k: {"revision": rows[k].revision if k in rows else 0, "last_change": rows[k].last_change if k in rows else None} for k in keys}


def material_changed(ctx: Ctx, patient_id: UUID, area: str, change: dict[str, Any], *, nominate: bool = True) -> None:
    """Relevant patient material changed: bump its scope and nominate scoped impact reviews."""
    key = patient_scope(patient_id, area)
    bump(ctx, key, change)
    if area.startswith("reports/"):
        bump(ctx, patient_scope(patient_id, "reports/*"), change)
    if nominate:
        from app.services import impacts
        impacts.nominate_for_material_change(ctx, patient_id, key, change)
