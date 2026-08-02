"""Deterministic command interpretation for the assistant.

Known commands compile into typed tool calls without model involvement, which
keeps side effects predictable. Free-form input falls back to a model answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Intent:
    kind: str
    tool_calls: list[dict[str, object]] = field(default_factory=list)


_REMEMBER = re.compile(r"^(?:remember|zapamatuj si|pamatuj si)\s*[:,]?\s*(.+)$", re.IGNORECASE)
_RECALL = re.compile(
    r"^(?:recall|what do you know about|co v[ií]š o|vzpome[nň] si na)\s*[:,]?\s*(.+)$",
    re.IGNORECASE,
)
_CALENDAR = re.compile(
    r"\b(calendar|kalend[aá][rř])\b|\bwhat'?s on (?:my )?(today|tomorrow)\b", re.IGNORECASE
)
_ADD_EVENT = re.compile(
    r"^(?:add event|create event|p[rř]idej ud[aá]lost)\s+(?P<title>.+?)\s+at\s+(?P<start>\S+)$",
    re.IGNORECASE,
)
_EMAIL_SEARCH = re.compile(
    r"^(?:search email|find email|najdi e?mail)\s*[:,]?\s*(.+)$", re.IGNORECASE
)
_EMAIL_DRAFT = re.compile(
    r"^(?:draft email|napi[sš] e?mail)\s+to\s+(?P<to>\S+)\s+subject\s+(?P<subject>.+?)"
    r"\s+body\s+(?P<body>.+)$",
    re.IGNORECASE,
)
_EMAIL_SEND = re.compile(r"^(?:send email|ode[sš]li e?mail)\s+(?P<draft_id>\S+)$", re.IGNORECASE)
_NOTIFY = re.compile(r"^(?:notify me|upozorni m[eě])\s*[:,]?\s*(.+)$", re.IGNORECASE)
_HOME_ON = re.compile(
    r"^(?:turn on|zapni)\s+(?:the\s+)?(?P<entity>[\w.]+)\s*$", re.IGNORECASE
)
_HOME_OFF = re.compile(
    r"^(?:turn off|vypni)\s+(?:the\s+)?(?P<entity>[\w.]+)\s*$", re.IGNORECASE
)
_HOME_STATE = re.compile(
    r"^(?:state of|status of|stav)\s+(?P<entity>[\w.]+)\s*$", re.IGNORECASE
)
_LIGHTS = re.compile(r"^(?:lights|sv[eě]tla)\??$", re.IGNORECASE)


def _entity_id(raw: str) -> str:
    entity = raw.strip().lower().replace(" ", "_")
    if "." not in entity:
        entity = f"light.{entity}"
    return entity


def interpret(command: str) -> Intent:
    """Compile a user command into deterministic tool calls when recognized."""
    text = command.strip()

    match = _REMEMBER.match(text)
    if match:
        return Intent(
            kind="tools",
            tool_calls=[{"tool": "memory_store", "args": {"content": match.group(1).strip()}}],
        )

    match = _RECALL.match(text)
    if match:
        return Intent(
            kind="tools",
            tool_calls=[{"tool": "memory_search", "args": {"query": match.group(1).strip()}}],
        )

    match = _ADD_EVENT.match(text)
    if match:
        return Intent(
            kind="tools",
            tool_calls=[
                {
                    "tool": "calendar_create",
                    "args": {
                        "title": match.group("title").strip(),
                        "start": match.group("start").strip(),
                    },
                }
            ],
        )

    if _CALENDAR.search(text):
        days = 2 if re.search(r"tomorrow|z[ií]tra", text, re.IGNORECASE) else 1
        return Intent(kind="tools", tool_calls=[{"tool": "calendar_list", "args": {"days": days}}])

    match = _EMAIL_DRAFT.match(text)
    if match:
        return Intent(
            kind="tools",
            tool_calls=[
                {
                    "tool": "email_draft",
                    "args": {
                        "to": match.group("to"),
                        "subject": match.group("subject").strip(),
                        "body": match.group("body").strip(),
                    },
                }
            ],
        )

    match = _EMAIL_SEND.match(text)
    if match:
        return Intent(
            kind="tools",
            tool_calls=[{"tool": "email_send", "args": {"draft_id": match.group("draft_id")}}],
        )

    match = _EMAIL_SEARCH.match(text)
    if match:
        return Intent(
            kind="tools",
            tool_calls=[{"tool": "email_search", "args": {"query": match.group(1).strip()}}],
        )

    match = _NOTIFY.match(text)
    if match:
        return Intent(
            kind="tools",
            tool_calls=[{"tool": "notify_send", "args": {"message": match.group(1).strip()}}],
        )

    match = _HOME_ON.match(text)
    if match:
        return Intent(
            kind="tools",
            tool_calls=[
                {
                    "tool": "home_control",
                    "args": {"entity_id": _entity_id(match.group("entity")), "service": "turn_on"},
                }
            ],
        )

    match = _HOME_OFF.match(text)
    if match:
        return Intent(
            kind="tools",
            tool_calls=[
                {
                    "tool": "home_control",
                    "args": {
                        "entity_id": _entity_id(match.group("entity")),
                        "service": "turn_off",
                    },
                }
            ],
        )

    match = _HOME_STATE.match(text)
    if match:
        return Intent(
            kind="tools",
            tool_calls=[
                {"tool": "home_state", "args": {"entity_id": _entity_id(match.group("entity"))}}
            ],
        )

    if _LIGHTS.match(text):
        return Intent(
            kind="tools", tool_calls=[{"tool": "home_state", "args": {"domain": "light"}}]
        )

    return Intent(kind="answer")
