"""Transport adapters for the future Orb Weaver Stage Governor contract."""

from __future__ import annotations

import json
from typing import Any, Callable, Mapping, Optional, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .stage_snapshot import StageSnapshot, StageSnapshotError


class StageContractError(RuntimeError):
    pass


class StageUnavailable(StageContractError):
    pass


class StageActionRejected(StageContractError):
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Mapping[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class StageTransport(Protocol):
    def fetch_stage(self, project_id: str) -> Mapping[str, Any]: ...

    def submit_action(self, payload: Mapping[str, Any], idempotency_key: str) -> Mapping[str, Any]: ...


class HttpStageTransport:
    """HTTP transport with caller-supplied contract URLs and no invented defaults."""

    def __init__(
        self,
        stage_url_template: str,
        action_url_template: str,
        token_provider: Callable[[], str],
        timeout_seconds: float = 10.0,
    ):
        if "{project_id}" not in stage_url_template or "{project_id}" not in action_url_template:
            raise ValueError("both URL templates must contain {project_id}")
        self._stage_url_template = stage_url_template
        self._action_url_template = action_url_template
        self._token_provider = token_provider
        self._timeout_seconds = timeout_seconds

    def fetch_stage(self, project_id: str) -> Mapping[str, Any]:
        return self._request("GET", self._stage_url_template.format(project_id=project_id))

    def submit_action(self, payload: Mapping[str, Any], idempotency_key: str) -> Mapping[str, Any]:
        project_id = str(payload["project_id"])
        return self._request(
            "POST",
            self._action_url_template.format(project_id=project_id),
            payload=payload,
            idempotency_key=idempotency_key,
        )

    def _request(
        self,
        method: str,
        url: str,
        payload: Optional[Mapping[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Mapping[str, Any]:
        token = self._token_provider().strip()
        if not token:
            raise StageUnavailable("Orb Weaver authentication is unavailable")
        headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        request = Request(url, data=body, method=method, headers=headers)
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                return self._decode(response.read())
        except HTTPError as exc:
            response = self._decode(exc.read(), allow_empty=True)
            if method == "POST":
                raise StageActionRejected(
                    str(response.get("detail") or response.get("error") or f"Orb Weaver rejected the action ({exc.code})"),
                    status_code=exc.code,
                    response=response,
                ) from exc
            raise StageUnavailable(f"Orb Weaver stage request failed ({exc.code})") from exc
        except (URLError, TimeoutError) as exc:
            raise StageUnavailable(f"Orb Weaver is unavailable: {exc}") from exc

    @staticmethod
    def _decode(body: bytes, allow_empty: bool = False) -> Mapping[str, Any]:
        if not body and allow_empty:
            return {}
        try:
            decoded = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StageContractError("Orb Weaver returned malformed JSON") from exc
        if not isinstance(decoded, Mapping):
            raise StageContractError("Orb Weaver response must be a JSON object")
        return decoded


class OrbWeaverStageClient:
    """Stateless client. Every read and action response is revalidated."""

    def __init__(self, transport: StageTransport):
        self._transport = transport

    @classmethod
    def from_orb_weaver(
        cls,
        base_url: str,
        token_provider: Callable[[], str],
        timeout_seconds: float = 10.0,
    ) -> "OrbWeaverStageClient":
        """Bind the adapter to Orb Weaver's implemented governor endpoints."""
        root = base_url.strip().rstrip("/")
        if not root.startswith(("http://", "https://")):
            raise ValueError("Orb Weaver base_url must be an absolute HTTP(S) URL")
        return cls(HttpStageTransport(
            stage_url_template=f"{root}/api/projects/{{project_id}}/orbs-stage",
            action_url_template=f"{root}/api/projects/{{project_id}}/orbs-stage/actions",
            token_provider=token_provider,
            timeout_seconds=timeout_seconds,
        ))

    def current_stage(self, project_id: str) -> StageSnapshot:
        try:
            return StageSnapshot.from_authoritative(self._transport.fetch_stage(str(project_id)))
        except StageSnapshotError as exc:
            raise StageContractError(f"invalid authoritative stage snapshot: {exc}") from exc

    def submit_action(self, payload: Mapping[str, Any], idempotency_key: str) -> StageSnapshot:
        if not idempotency_key or not idempotency_key.strip():
            raise ValueError("idempotency_key is required")
        try:
            snapshot = StageSnapshot.from_authoritative(self._transport.submit_action(payload, idempotency_key))
        except StageSnapshotError as exc:
            raise StageContractError(f"action response did not contain a valid fresh snapshot: {exc}") from exc
        if snapshot.project_id != str(payload.get("project_id")):
            raise StageContractError("action response changed the bound project")
        return snapshot
