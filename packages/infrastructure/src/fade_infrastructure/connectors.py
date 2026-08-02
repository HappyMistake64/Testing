"""Integration connector adapters and local test doubles.

Real adapters call external services only through explicit configuration and
host allowlists; doubles keep the assistant fully functional offline.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import httpx
from fade_application.assistant_ports import (
    CalendarEvent,
    CalendarPort,
    DeviceState,
    EmailMessage,
    EmailPort,
    NotificationPort,
    SmartHomePort,
    SpeechAudio,
    SpeechToTextPort,
    TextToSpeechPort,
    Transcription,
    VisionDescription,
    VisionPort,
)
from ulid import ULID

from fade_infrastructure.settings import Settings


class ConnectorError(Exception):
    """Raised when a connector call fails or is not configured."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _check_host_allowed(url: str, allowed_hosts: list[str]) -> None:
    host = urlparse(url).hostname or ""
    if host not in allowed_hosts:
        msg = f"Host not in integration allowlist: {host}"
        raise ConnectorError("HOST_NOT_ALLOWED", msg)


# --------------------------------------------------------------------------
# Local doubles (default, fully offline)
# --------------------------------------------------------------------------


class LocalCalendar(CalendarPort):
    """In-database-free local calendar double persisted in memory per process."""

    def __init__(self) -> None:
        self._events: list[CalendarEvent] = []

    async def list_events(self, *, start: datetime, end: datetime) -> list[CalendarEvent]:
        return [e for e in self._events if start <= e.start <= end]

    async def create_event(
        self, *, title: str, start: datetime, end: datetime | None = None
    ) -> CalendarEvent:
        event = CalendarEvent(id=str(ULID()), title=title, start=start, end=end)
        self._events.append(event)
        return event


class LocalEmail(EmailPort):
    """Local email double: drafts are stored, sending is simulated."""

    def __init__(self) -> None:
        self._messages: list[EmailMessage] = []

    async def search(self, query: str, *, limit: int = 10) -> list[EmailMessage]:
        needle = query.lower()
        return [
            m
            for m in self._messages
            if needle in m.subject.lower() or needle in m.body.lower()
        ][:limit]

    async def draft(self, *, to: str, subject: str, body: str) -> EmailMessage:
        message = EmailMessage(
            id=str(ULID()),
            subject=subject,
            sender="me@local",
            recipient=to,
            body=body,
            sent=False,
        )
        self._messages.append(message)
        return message

    async def send(self, draft_id: str) -> EmailMessage:
        for index, message in enumerate(self._messages):
            if message.id == draft_id:
                sent = EmailMessage(
                    id=message.id,
                    subject=message.subject,
                    sender=message.sender,
                    recipient=message.recipient,
                    body=message.body,
                    sent=True,
                )
                self._messages[index] = sent
                return sent
        msg = f"Draft not found: {draft_id}"
        raise ConnectorError("DRAFT_NOT_FOUND", msg)


class LocalNotifications(NotificationPort):
    """Local notification double retaining a bounded history."""

    def __init__(self) -> None:
        self.history: list[dict[str, str]] = []

    async def notify(self, *, title: str, message: str) -> str:
        notification_id = str(ULID())
        self.history.append({"id": notification_id, "title": title, "message": message})
        del self.history[:-100]
        return notification_id


class LocalSmartHome(SmartHomePort):
    """Local smart-home double with a small set of virtual entities."""

    def __init__(self) -> None:
        self._states: dict[str, DeviceState] = {
            "light.office": DeviceState(entity_id="light.office", state="off"),
            "light.living_room": DeviceState(entity_id="light.living_room", state="off"),
            "switch.heater": DeviceState(entity_id="switch.heater", state="off"),
        }

    async def get_state(self, entity_id: str) -> DeviceState:
        state = self._states.get(entity_id)
        if state is None:
            msg = f"Unknown entity: {entity_id}"
            raise ConnectorError("ENTITY_NOT_FOUND", msg)
        return state

    async def list_states(self, *, domain: str | None = None) -> list[DeviceState]:
        states = list(self._states.values())
        if domain:
            states = [s for s in states if s.entity_id.startswith(f"{domain}.")]
        return states

    async def call_service(self, *, domain: str, service: str, entity_id: str) -> DeviceState:
        if entity_id not in self._states:
            msg = f"Unknown entity: {entity_id}"
            raise ConnectorError("ENTITY_NOT_FOUND", msg)
        new_state = "on" if service == "turn_on" else "off" if service == "turn_off" else service
        updated = DeviceState(entity_id=entity_id, state=new_state)
        self._states[entity_id] = updated
        return updated


class LocalSpeechToText(SpeechToTextPort):
    """Local STT double: browser performs recognition, server verifies shape."""

    @property
    def provider_id(self) -> str:
        return "local-browser"

    async def transcribe(
        self, *, audio_b64: str | None, text_hint: str | None
    ) -> Transcription:
        if text_hint:
            return Transcription(text=text_hint, provider_id=self.provider_id, confidence=1.0)
        if audio_b64:
            msg = "Server-side audio transcription requires a configured STT provider"
            raise ConnectorError("STT_NOT_CONFIGURED", msg)
        msg = "No audio or transcript provided"
        raise ConnectorError("EMPTY_INPUT", msg)


class LocalTextToSpeech(TextToSpeechPort):
    """Local TTS double: the browser SpeechSynthesis API renders the audio."""

    @property
    def provider_id(self) -> str:
        return "local-browser"

    async def speak(self, text: str) -> SpeechAudio:
        return SpeechAudio(provider_id=self.provider_id, text=text)


class LocalVision(VisionPort):
    """Local vision double reporting image receipt without cloud upload."""

    @property
    def provider_id(self) -> str:
        return "local-metadata"

    async def describe(self, *, image_b64: str, prompt: str | None = None) -> VisionDescription:
        size = len(image_b64) * 3 // 4
        description = (
            f"Image received ({size} bytes). A multimodal vision model is not configured; "
            "connect one to enable content understanding."
        )
        return VisionDescription(provider_id=self.provider_id, description=description)


# --------------------------------------------------------------------------
# Home Assistant HTTP adapter (opt-in via settings)
# --------------------------------------------------------------------------


class HomeAssistantConnector(SmartHomePort):
    """Real Home Assistant REST adapter, restricted by host allowlist."""

    def __init__(self, settings: Settings) -> None:
        if not settings.home_assistant_url or not settings.home_assistant_token:
            msg = "Home Assistant is not configured"
            raise ConnectorError("NOT_CONFIGURED", msg)
        _check_host_allowed(settings.home_assistant_url, settings.integration_allowed_hosts)
        self._base_url = settings.home_assistant_url.rstrip("/")
        self._token = settings.home_assistant_token.get_secret_value()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    async def get_state(self, entity_id: str) -> DeviceState:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self._base_url}/api/states/{entity_id}", headers=self._headers()
            )
            response.raise_for_status()
            data = response.json()
            return DeviceState(
                entity_id=data["entity_id"],
                state=data["state"],
                attributes=data.get("attributes", {}),
            )

    async def list_states(self, *, domain: str | None = None) -> list[DeviceState]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self._base_url}/api/states", headers=self._headers())
            response.raise_for_status()
            states = [
                DeviceState(
                    entity_id=item["entity_id"],
                    state=item["state"],
                    attributes=item.get("attributes", {}),
                )
                for item in response.json()
            ]
            if domain:
                states = [s for s in states if s.entity_id.startswith(f"{domain}.")]
            return states

    async def call_service(self, *, domain: str, service: str, entity_id: str) -> DeviceState:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self._base_url}/api/services/{domain}/{service}",
                headers=self._headers(),
                json={"entity_id": entity_id},
            )
            response.raise_for_status()
        return await self.get_state(entity_id)


class WebhookNotifications(NotificationPort):
    """Generic webhook notification adapter (ntfy/gotify style)."""

    def __init__(self, settings: Settings) -> None:
        if not settings.notify_webhook_url:
            msg = "Notification webhook is not configured"
            raise ConnectorError("NOT_CONFIGURED", msg)
        _check_host_allowed(settings.notify_webhook_url, settings.integration_allowed_hosts)
        self._url = settings.notify_webhook_url

    async def notify(self, *, title: str, message: str) -> str:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(self._url, json={"title": title, "message": message})
            response.raise_for_status()
        return str(ULID())


# --------------------------------------------------------------------------
# Connector registry
# --------------------------------------------------------------------------


class ConnectorRegistry:
    """Resolve configured adapters, defaulting to local doubles."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.calendar: CalendarPort = LocalCalendar()
        self.email: EmailPort = LocalEmail()
        self.speech_to_text: SpeechToTextPort = LocalSpeechToText()
        self.text_to_speech: TextToSpeechPort = LocalTextToSpeech()
        self.vision: VisionPort = LocalVision()

        self.notifications: NotificationPort
        if settings.notify_webhook_url:
            self.notifications = WebhookNotifications(settings)
        else:
            self.notifications = LocalNotifications()

        self.smart_home: SmartHomePort
        if settings.home_assistant_url and settings.home_assistant_token:
            self.smart_home = HomeAssistantConnector(settings)
        else:
            self.smart_home = LocalSmartHome()

    def status(self) -> dict[str, dict[str, object]]:
        return {
            "calendar": {"provider": type(self.calendar).__name__, "local": True},
            "email": {"provider": type(self.email).__name__, "local": True},
            "notifications": {
                "provider": type(self.notifications).__name__,
                "local": isinstance(self.notifications, LocalNotifications),
            },
            "smart_home": {
                "provider": type(self.smart_home).__name__,
                "local": isinstance(self.smart_home, LocalSmartHome),
            },
            "speech_to_text": {"provider": self.speech_to_text.provider_id, "local": True},
            "text_to_speech": {"provider": self.text_to_speech.provider_id, "local": True},
            "vision": {"provider": self.vision.provider_id, "local": True},
        }


def upcoming_window(days: int = 1) -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    return now, now + timedelta(days=days)
