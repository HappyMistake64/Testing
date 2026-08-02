"""Ports for personal-assistant adapters (voice, vision, integrations)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    id: str
    title: str
    start: datetime
    end: datetime | None = None
    location: str | None = None


@dataclass(frozen=True, slots=True)
class EmailMessage:
    id: str
    subject: str
    sender: str
    recipient: str
    body: str
    sent: bool = False


@dataclass(frozen=True, slots=True)
class DeviceState:
    entity_id: str
    state: str
    attributes: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Transcription:
    text: str
    provider_id: str
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class SpeechAudio:
    provider_id: str
    text: str
    audio_b64: str | None = None
    media_type: str | None = None


@dataclass(frozen=True, slots=True)
class VisionDescription:
    provider_id: str
    description: str


class CalendarPort(ABC):
    """Calendar integration boundary."""

    @abstractmethod
    async def list_events(self, *, start: datetime, end: datetime) -> list[CalendarEvent]: ...

    @abstractmethod
    async def create_event(
        self, *, title: str, start: datetime, end: datetime | None = None
    ) -> CalendarEvent: ...


class EmailPort(ABC):
    """Email integration boundary."""

    @abstractmethod
    async def search(self, query: str, *, limit: int = 10) -> list[EmailMessage]: ...

    @abstractmethod
    async def draft(self, *, to: str, subject: str, body: str) -> EmailMessage: ...

    @abstractmethod
    async def send(self, draft_id: str) -> EmailMessage: ...


class NotificationPort(ABC):
    """Owner notification boundary."""

    @abstractmethod
    async def notify(self, *, title: str, message: str) -> str: ...


class SmartHomePort(ABC):
    """Smart-home gateway boundary (Home Assistant)."""

    @abstractmethod
    async def get_state(self, entity_id: str) -> DeviceState: ...

    @abstractmethod
    async def list_states(self, *, domain: str | None = None) -> list[DeviceState]: ...

    @abstractmethod
    async def call_service(
        self, *, domain: str, service: str, entity_id: str
    ) -> DeviceState: ...


class SpeechToTextPort(ABC):
    """Speech recognition boundary."""

    @property
    @abstractmethod
    def provider_id(self) -> str: ...

    @abstractmethod
    async def transcribe(
        self, *, audio_b64: str | None, text_hint: str | None
    ) -> Transcription: ...


class TextToSpeechPort(ABC):
    """Speech synthesis boundary."""

    @property
    @abstractmethod
    def provider_id(self) -> str: ...

    @abstractmethod
    async def speak(self, text: str) -> SpeechAudio: ...


class VisionPort(ABC):
    """Image understanding boundary."""

    @property
    @abstractmethod
    def provider_id(self) -> str: ...

    @abstractmethod
    async def describe(self, *, image_b64: str, prompt: str | None = None) -> VisionDescription: ...
