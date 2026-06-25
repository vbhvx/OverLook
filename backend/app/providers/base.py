# backend/app/providers/base.py
import abc
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
import httpx
from backend.app.schemas.signals import SignalEnvelope, DataStatus
from backend.app.config import settings

def compute_record_hash(raw_data: Any) -> str:
    """Computes a deterministic SHA-256 hash for raw source record deduplication."""
    serialized = json.dumps(raw_data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()

class BaseProviderAdapter(abc.ABC):
    source_id: str
    category: str
    name: str

    def __init__(self):
        self.last_sync_at: Optional[datetime] = None
        self.last_status: str = "active"
        self.last_error: Optional[str] = None
        self.rate_limited_until: Optional[datetime] = None

    @abc.abstractmethod
    async def fetch_signals(self, bbox: Optional[List[float]] = None) -> List[SignalEnvelope]:
        """
        Fetches signals from the provider or authorized cache.
        Optionally bounded by bbox [west, south, east, north].
        """
        pass

    @abc.abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """
        Checks connectivity, rate-limit status, and schema health.
        """
        pass

    def get_http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=settings.PROVIDER_TIMEOUT_SECONDS,
            headers={
                "User-Agent": f"OverLook-Situational-Awareness/1.0 (+https://github.com/overlook-intel)"
            }
        )

