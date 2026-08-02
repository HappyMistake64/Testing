"""User-created automations (reminders, scheduled commands)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from fade_infrastructure.models import AutomationModel


@dataclass(frozen=True, slots=True)
class Automation:
    id: str
    name: str
    command: str
    schedule_kind: str
    interval_seconds: int | None
    next_run_at: datetime | None
    enabled: bool
    last_run_at: datetime | None
    created_at: datetime


class SqlAlchemyAutomationRepository:
    """Persistence for explicitly user-created automations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        name: str,
        command: str,
        schedule_kind: str,
        interval_seconds: int | None,
        next_run_at: datetime | None,
    ) -> Automation:
        model = AutomationModel(
            id=str(ULID()),
            name=name,
            command=command,
            schedule_kind=schedule_kind,
            interval_seconds=interval_seconds,
            next_run_at=next_run_at,
            enabled=True,
        )
        self._session.add(model)
        await self._session.commit()
        return _from_model(model)

    async def list_all(self) -> list[Automation]:
        result = await self._session.execute(
            select(AutomationModel).order_by(AutomationModel.created_at.desc())
        )
        return [_from_model(m) for m in result.scalars().all()]

    async def get(self, automation_id: str) -> Automation | None:
        model = await self._session.get(AutomationModel, automation_id)
        return _from_model(model) if model else None

    async def set_enabled(self, automation_id: str, enabled: bool) -> Automation | None:
        model = await self._session.get(AutomationModel, automation_id)
        if model is None:
            return None
        model.enabled = enabled
        await self._session.commit()
        return _from_model(model)

    async def delete(self, automation_id: str) -> bool:
        model = await self._session.get(AutomationModel, automation_id)
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.commit()
        return True

    async def claim_due(self, *, now: datetime | None = None) -> list[Automation]:
        """Return due automations and advance their schedules atomically."""
        now = now or datetime.now(UTC)
        result = await self._session.execute(
            select(AutomationModel).where(
                AutomationModel.enabled.is_(True),
                AutomationModel.next_run_at.is_not(None),
            )
        )
        due: list[Automation] = []
        for model in result.scalars().all():
            next_run = model.next_run_at
            if next_run is not None and next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=UTC)
            if next_run is None or next_run > now:
                continue
            model.last_run_at = now
            if model.schedule_kind == "interval" and model.interval_seconds:
                model.next_run_at = now + timedelta(seconds=model.interval_seconds)
            else:
                model.next_run_at = None
                model.enabled = False
            due.append(_from_model(model))
        if due:
            await self._session.commit()
        return due


def _from_model(model: AutomationModel) -> Automation:
    return Automation(
        id=model.id,
        name=model.name,
        command=model.command,
        schedule_kind=model.schedule_kind,
        interval_seconds=model.interval_seconds,
        next_run_at=model.next_run_at,
        enabled=model.enabled,
        last_run_at=model.last_run_at,
        created_at=model.created_at,
    )
