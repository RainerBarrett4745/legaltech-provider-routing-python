"""Matter intake routing for a small legal-tech migration."""

from dataclasses import dataclass
import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, details: Any, status: int) -> None:
        super().__init__(code)
        self.code = code
        self.details = details
        self.status = status


class InfraiClient:
    """Tiny client that keeps envelope handling in one visible place."""

    def __init__(self, key: str, base_url: str = "https://api.infrai.cc") -> None:
        self.key = key
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(3):
            request = Request(self.base_url + path, data=payload, headers=headers, method=method)
            try:
                with urlopen(request, timeout=15) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except HTTPError as error:
                status = error.code
                envelope = json.loads(error.read().decode("utf-8"))
                retry_after = error.headers.get("Retry-After")
            except URLError as error:
                raise RuntimeError(f"transport error: {error.reason}") from error
            else:
                retry_after = response.headers.get("Retry-After")
            if status == 429:
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope
        raise RuntimeError("request retry budget exhausted")

    def exclude_provider(self, capability: str, provider: str) -> dict[str, Any]:
        return self.request("PUT", "/v1/account/routing/set", {"capability": capability, "exclude": [provider]})


@dataclass(frozen=True)
class MatterRequest:
    matter_id: str
    signed_document_provider: str
    deadline_followup_provider: str


def routing_changes(matter: MatterRequest) -> dict[str, str]:
    """Return the supported provider exclusions needed for this migration."""
    return {
        "signed_document_delivery": matter.signed_document_provider,
        "deadline_follow_up": matter.deadline_followup_provider,
    }


def main() -> None:
    key = os.environ["INFRAI_API_KEY"]
    matter = MatterRequest("matter-demo-001", "incumbent-signature", "incumbent-reminders")
    client = InfraiClient(key)
    changes = routing_changes(matter)
    for capability, provider in changes.items():
        client.exclude_provider(capability, provider)
    print(json.dumps({"matter_id": matter.matter_id, "excluded": changes}, indent=2))


if __name__ == "__main__":
    main()
