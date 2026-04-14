from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    """
    Every integration adapter must implement these two methods.
    normalize() converts the raw webhook payload into our standard Event Object.
    get_idempotency_key() extracts a unique key so we never process the same event twice.
    """

    @abstractmethod
    def normalize(self, payload: dict, headers: dict) -> dict:
        """Return a standardized event dict with keys:
        {
            source,event,title,body,
            actor,url,timestamp,metadata
        }
        """

    @abstractmethod
    def get_idempotency_key(self, payload: dict, headers: dict) -> str:
        """Return a string that uniquely identifies this webhook delivery."""
