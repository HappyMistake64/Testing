"""Durable assistant memory with SQLite FTS5 retrieval."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fade_domain.assistant import MemoryItem
from fade_domain.ids import AssistantTurnId, MemoryId
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from fade_infrastructure.models import MemoryItemModel


class SqlAlchemyMemoryRepository:
    """Store and retrieve verified assistant memories locally."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def store(self, item: MemoryItem) -> MemoryItem:
        model = MemoryItemModel(
            id=str(item.id),
            content=item.content,
            source_turn_id=str(item.source_turn_id) if item.source_turn_id else None,
            confidence=item.confidence,
            evidence_refs_json=json.dumps(item.evidence_refs),
            expires_at=item.expires_at,
        )
        self._session.add(model)
        await self._session.commit()
        try:
            await self._session.execute(
                text("INSERT INTO memory_fts (memory_id, content) VALUES (:id, :content)"),
                {"id": str(item.id), "content": item.content},
            )
            await self._session.commit()
        except OperationalError:
            await self._session.rollback()
        return item

    async def search(self, query: str, *, limit: int = 10) -> list[MemoryItem]:
        ids: list[str] = []
        if query.strip():
            try:
                result = await self._session.execute(
                    text(
                        "SELECT memory_id FROM memory_fts WHERE memory_fts MATCH :q LIMIT :limit"
                    ),
                    {"q": _fts_query(query), "limit": limit},
                )
                ids = [row[0] for row in result.fetchall()]
            except OperationalError:
                await self._session.rollback()

        if ids:
            result = await self._session.execute(
                select(MemoryItemModel).where(MemoryItemModel.id.in_(ids))
            )
        else:
            stmt = select(MemoryItemModel).order_by(MemoryItemModel.created_at.desc()).limit(limit)
            if query.strip():
                stmt = (
                    select(MemoryItemModel)
                    .where(MemoryItemModel.content.like(f"%{query}%"))
                    .order_by(MemoryItemModel.created_at.desc())
                    .limit(limit)
                )
            result = await self._session.execute(stmt)

        now = datetime.now(UTC)
        items = []
        for model in result.scalars().all():
            expires = model.expires_at
            if expires is not None and expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
            if expires is not None and expires < now:
                continue
            items.append(_from_model(model))
        return items

    async def list_all(self, *, limit: int = 100) -> list[MemoryItem]:
        result = await self._session.execute(
            select(MemoryItemModel).order_by(MemoryItemModel.created_at.desc()).limit(limit)
        )
        return [_from_model(m) for m in result.scalars().all()]

    async def delete(self, memory_id: MemoryId) -> bool:
        model = await self._session.get(MemoryItemModel, str(memory_id))
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.commit()
        try:
            await self._session.execute(
                text("DELETE FROM memory_fts WHERE memory_id = :id"),
                {"id": str(memory_id)},
            )
            await self._session.commit()
        except OperationalError:
            await self._session.rollback()
        return True


def _fts_query(query: str) -> str:
    tokens = [t for t in query.replace('"', " ").split() if t.isalnum()]
    return " OR ".join(tokens) if tokens else query


def _from_model(model: MemoryItemModel) -> MemoryItem:
    return MemoryItem(
        id=MemoryId.from_string(model.id),
        content=model.content,
        source_turn_id=(
            AssistantTurnId.from_string(model.source_turn_id) if model.source_turn_id else None
        ),
        confidence=model.confidence,
        evidence_refs=json.loads(model.evidence_refs_json),
        expires_at=model.expires_at,
        created_at=model.created_at,
    )
