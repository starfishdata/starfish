from dataclasses import dataclass, field
from os import environ, makedirs, path
from typing import Dict, Optional
from uuid import UUID, uuid4

import posthog

from starfish.data_factory.constants import APP_DATA_DIR


class TelemetryConfig:
    """Handles telemetry configuration and distinct ID management."""

    @staticmethod
    def generate_client_id() -> UUID:
        """Generate or retrieve a unique client identifier."""
        config_path = path.join(path.expanduser(APP_DATA_DIR), ".starfish_config")
        makedirs(path.dirname(config_path), exist_ok=True)

        if path.exists(config_path):
            with open(config_path) as f:
                return UUID(f.read().strip())

        new_id = uuid4()
        with open(config_path, "w") as f:
            f.write(str(new_id))
        return new_id


@dataclass
class Event:
    """Represents a telemetry event."""

    name: str
    data: Dict
    client_id: str = field(default_factory=lambda: str(TelemetryConfig.generate_client_id()))


@dataclass
class AnalyticsConfig:
    """Configuration for analytics service."""

    api_key: str
    active: bool = True
    verbose: bool = False
    endpoint: Optional[str] = None


class AnalyticsService:
    """Service for sending analytics data."""

    def __init__(self, settings: AnalyticsConfig):
        """Initialize the analytics service with the given configuration.

        Args:
            settings (AnalyticsConfig): Configuration object containing API key,
                activation status, verbosity, and optional custom endpoint.
        """
        self.settings = settings
        self._setup_client()

    def _setup_client(self) -> None:
        """Configure the analytics client."""
        posthog.project_api_key = self.settings.api_key
        posthog.debug = self.settings.verbose
        posthog.disable_geoip = False

        if self.settings.endpoint:
            posthog.host = self.settings.endpoint

    def send_event(self, event: Event) -> None:
        """Transmit an analytics event."""
        if not self.settings.active:
            return

        try:
            posthog.capture(distinct_id=event.client_id, event=event.name, properties=event.data)
        except Exception:
            pass


# Initialize analytics service with environment configuration
analytics = AnalyticsService(
    AnalyticsConfig(
        api_key="phc_egjc8W2y5TEVEk54fAZjMcpnD56sOMuoZUUGiH50riA",
        active=environ.get("TELEMETRY_ENABLED", "true").lower() in ("true", "1", "t"),
        verbose=environ.get("DEBUG_MODE", "false").lower() in ("true", "1", "t"),
        endpoint=environ.get("POSTHOG_HOST", "https://us.i.posthog.com"),
    )
)
