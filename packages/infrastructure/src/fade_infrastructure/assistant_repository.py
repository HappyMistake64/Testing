"""SQLAlchemy repositories for assistant sessions, turns, approvals and controls."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fade_domain.assistant import (
    AssistantSession,
    AssistantTurn,
    Capability,
    CommandMode,
    ToolApproval,
    TurnState,
)
from fade_domain.ids import ApprovalId, AssistantSessionId, AssistantTurnId
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fade_infrastructure.models import (
    AssistantControlModel,
    AssistantSessionModel,
    AssistantTurnModel,
    ToolApprovalModel,
)


class SqlAlchemyAssistantRepository:
    """Persistence for assistant conversations and approvals."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # Sessions -----------------------------------------------------------

    async def create_session(self, session: AssistantSession) -> AssistantSession:
        model = AssistantSessionModel(
            id=str(session.id),
            title=session.title,
            provider_id=session.provider_id,
            model_id=session.model_id,
        )
        self._session.add(model)
        await self._session.commit()
        return session

    async def get_session(self, session_id: AssistantSessionId) -> AssistantSession | None:
        model = await self._session.get(AssistantSessionModel, str(session_id))
        return _session_from_model(model) if model else None

    async def list_sessions(self, *, limit: int = 50) -> list[AssistantSession]:
        result = await self._session.execute(
            select(AssistantSessionModel)
            .order_by(AssistantSessionModel.created_at.desc())
            .limit(limit)
        )
        return [_session_from_model(m) for m in result.scalars().all()]

    # Turns --------------------------------------------------------------

    async def create_turn(self, turn: AssistantTurn, *, job_id: str | None = None) -> AssistantTurn:
        model = AssistantTurnModel(
            id=str(turn.id),
            session_id=str(turn.session_id),
            job_id=job_id,
            command=turn.command,
            mode=turn.mode.value,
            state=turn.state.value,
            provider_id=turn.provider_id,
            model_id=turn.model_id,
            response=turn.response,
            tool_calls_json=json.dumps(turn.tool_calls),
            evidence_refs_json=json.dumps(turn.evidence_refs),
        )
        self._session.add(model)
        await self._session.commit()
        return turn

    async def get_turn(self, turn_id: AssistantTurnId) -> AssistantTurn | None:
        model = await self._session.get(AssistantTurnModel, str(turn_id))
        return _turn_from_model(model) if model else None

    async def get_turn_job_id(self, turn_id: AssistantTurnId) -> str | None:
        model = await self._session.get(AssistantTurnModel, str(turn_id))
        return model.job_id if model else None

    async def list_turns(self, session_id: AssistantSessionId) -> list[AssistantTurn]:
        result = await self._session.execute(
            select(AssistantTurnModel)
            .where(AssistantTurnModel.session_id == str(session_id))
            .order_by(AssistantTurnModel.created_at.asc())
        )
        return [_turn_from_model(m) for m in result.scalars().all()]

    async def update_turn(
        self,
        turn_id: AssistantTurnId,
        *,
        state: TurnState | None = None,
        response: str | None = None,
        provider_id: str | None = None,
        model_id: str | None = None,
        tool_calls: list[dict[str, object]] | None = None,
        evidence_refs: list[str] | None = None,
    ) -> AssistantTurn | None:
        model = await self._session.get(AssistantTurnModel, str(turn_id))
        if model is None:
            return None
        if state is not None:
            model.state = state.value
        if response is not None:
            model.response = response
        if provider_id is not None:
            model.provider_id = provider_id
        if model_id is not None:
            model.model_id = model_id
        if tool_calls is not None:
            model.tool_calls_json = json.dumps(tool_calls)
        if evidence_refs is not None:
            model.evidence_refs_json = json.dumps(evidence_refs)
        model.updated_at = datetime.now(UTC)
        await self._session.commit()
        return _turn_from_model(model)

    # Approvals ----------------------------------------------------------

    async def create_approval(self, approval: ToolApproval, *, args_preview: str) -> ToolApproval:
        model = ToolApprovalModel(
            id=str(approval.id),
            turn_id=str(approval.turn_id),
            tool_name=approval.tool_name,
            normalized_args_hash=approval.normalized_args_hash,
            capability=approval.capability.value,
            args_preview=args_preview,
            decision=approval.decision,
            expires_at=approval.expires_at,
        )
        self._session.add(model)
        await self._session.commit()
        return approval

    async def get_approval(self, approval_id: ApprovalId) -> ToolApproval | None:
        model = await self._session.get(ToolApprovalModel, str(approval_id))
        return _approval_from_model(model) if model else None

    async def list_pending_approvals(self) -> list[dict[str, object]]:
        result = await self._session.execute(
            select(ToolApprovalModel)
            .where(ToolApprovalModel.decision == "pending")
            .order_by(ToolApprovalModel.created_at.asc())
        )
        return [
            {
                "id": m.id,
                "turn_id": m.turn_id,
                "tool_name": m.tool_name,
                "capability": m.capability,
                "args_preview": m.args_preview,
                "created_at": m.created_at,
            }
            for m in result.scalars().all()
        ]

    async def decide_approval(
        self, approval_id: ApprovalId, *, decision: str
    ) -> ToolApproval | None:
        model = await self._session.get(ToolApprovalModel, str(approval_id))
        if model is None or model.decision != "pending":
            return None
        model.decision = decision
        await self._session.commit()
        return _approval_from_model(model)

    async def find_granted_approval(
        self,
        *,
        turn_id: AssistantTurnId,
        tool_name: str,
        normalized_args_hash: str,
    ) -> ToolApproval | None:
        """Find an unconsumed, unexpired approval matching the exact tool call."""
        result = await self._session.execute(
            select(ToolApprovalModel).where(
                ToolApprovalModel.turn_id == str(turn_id),
                ToolApprovalModel.tool_name == tool_name,
                ToolApprovalModel.normalized_args_hash == normalized_args_hash,
                ToolApprovalModel.decision == "approved",
                ToolApprovalModel.consumed.is_(False),
            )
        )
        model = result.scalars().first()
        if model is None:
            return None
        if model.expires_at is not None:
            expires = model.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
            if expires < datetime.now(UTC):
                return None
        return _approval_from_model(model)

    async def consume_approval(self, approval_id: ApprovalId) -> None:
        model = await self._session.get(ToolApprovalModel, str(approval_id))
        if model is not None:
            model.consumed = True
            await self._session.commit()

    async def revoke_pending_approvals(self) -> int:
        result = await self._session.execute(
            update(ToolApprovalModel)
            .where(ToolApprovalModel.decision == "pending")
            .values(decision="revoked")
        )
        await self._session.commit()
        return int(result.rowcount or 0)

    # Emergency stop -----------------------------------------------------

    async def is_paused(self) -> bool:
        model = await self._session.get(AssistantControlModel, 1)
        return bool(model.paused) if model else False

    async def set_paused(self, paused: bool, *, reason: str | None = None) -> None:
        model = await self._session.get(AssistantControlModel, 1)
        if model is None:
            model = AssistantControlModel(id=1, paused=paused, reason=reason)
            self._session.add(model)
        else:
            model.paused = paused
            model.reason = reason
        await self._session.commit()


def _session_from_model(model: AssistantSessionModel) -> AssistantSession:
    return AssistantSession(
        id=AssistantSessionId.from_string(model.id),
        title=model.title,
        provider_id=model.provider_id,
        model_id=model.model_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _turn_from_model(model: AssistantTurnModel) -> AssistantTurn:
    return AssistantTurn(
        id=AssistantTurnId.from_string(model.id),
        session_id=AssistantSessionId.from_string(model.session_id),
        command=model.command,
        mode=CommandMode(model.mode),
        state=TurnState(model.state),
        provider_id=model.provider_id,
        model_id=model.model_id,
        response=model.response,
        tool_calls=json.loads(model.tool_calls_json),
        evidence_refs=json.loads(model.evidence_refs_json),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _approval_from_model(model: ToolApprovalModel) -> ToolApproval:
    return ToolApproval(
        id=ApprovalId.from_string(model.id),
        turn_id=AssistantTurnId.from_string(model.turn_id),
        tool_name=model.tool_name,
        normalized_args_hash=model.normalized_args_hash,
        capability=Capability(model.capability),
        decision=model.decision,
        expires_at=model.expires_at,
        created_at=model.created_at,
    )
