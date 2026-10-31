import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import TypeVar, Any
from .resources import FHIRResource, Bundle, OperationOutcome

T = TypeVar("T", bound=FHIRResource)


class FHIRError(Exception):
    """Raised when a FHIR server responds with an HTTP error or OperationOutcome."""
    def __init__(self, status_code: int, message: str, outcome: "OperationOutcome | None" = None):
        super().__init__(f"FHIR HTTP {status_code}: {message}")
        self.status_code = status_code
        self.outcome: OperationOutcome | None = outcome


def _encode_body(data: dict | FHIRResource | None) -> bytes | None:
    if data is None:
        return None
    raw = data.to_dict() if isinstance(data, FHIRResource) else data
    return json.dumps(raw, ensure_ascii=False).encode("utf-8")


def _parse_error_outcome(err: urllib.error.HTTPError) -> tuple[str, OperationOutcome | None]:
    err_body = err.read().decode("utf-8") if err.fp else ""
    if not err_body:
        return str(err.reason), None

    try:
        raw = json.loads(err_body)
        if isinstance(raw, dict):
            if raw.get("resourceType") == "OperationOutcome":
                return err_body, OperationOutcome(raw)
            return err_body, OperationOutcome({
                "resourceType": "OperationOutcome",
                "issue": [{"severity": "error", "code": "processing", "diagnostics": err_body}],
            })
    except Exception:
        pass
    return err_body or str(err.reason), None


class FHIRClient:
    """Ultra-lightweight zero-dependency REST client for FHIR servers using urllib."""

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        auth: tuple[str, str] | str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {
            "Accept": "application/fhir+json, application/json",
            "Content-Type": "application/fhir+json; charset=utf-8",
        }
        if headers:
            self.headers.update(headers)
        if auth:
            if isinstance(auth, tuple):
                token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
                self.headers["Authorization"] = f"Basic {token}"
            elif isinstance(auth, str):
                if not auth.startswith(("Bearer ", "Basic ")):
                    self.headers["Authorization"] = f"Bearer {auth}"
                else:
                    self.headers["Authorization"] = auth

    def _resolve_type(self, resource_type: str | type[FHIRResource]) -> str:
        if isinstance(resource_type, str):
            return resource_type
        return getattr(resource_type, "resource_type", str(resource_type))

    def _build_url(self, path: str, params: dict[str, Any] | None) -> str:
        url = f"{self.base_url}/{path.lstrip('/')}"
        if not params:
            return url
        query = urllib.parse.urlencode(params, doseq=True)
        return f"{url}?{query}"

    def _request(
        self,
        method: str,
        path: str,
        data: dict | FHIRResource | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict | None:
        url = self._build_url(path, params)
        body_bytes = _encode_body(data)

        req = urllib.request.Request(
            url=url,
            data=body_bytes,
            headers=self.headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 204:
                    return None
                resp_bytes = resp.read()
                return json.loads(resp_bytes.decode("utf-8")) if resp_bytes else None
        except urllib.error.HTTPError as err:
            err_msg, outcome = _parse_error_outcome(err)
            raise FHIRError(err.code, err_msg, outcome=outcome) from err

    def read(self, resource_type: str | type[T], id: str) -> T:
        """Fetch a specific resource by ID: GET [base]/[resourceType]/[id]."""
        res_type = self._resolve_type(resource_type)
        data = self._request("GET", f"{res_type}/{id}")
        if data is None:
            raise FHIRError(404, f"Resource {res_type}/{id} returned empty content")
        return FHIRResource.from_dict(data)

    def search(self, resource_type: str | type[FHIRResource], **params) -> Bundle:
        """Search resources with query parameters: GET [base]/[resourceType]?params..."""
        res_type = self._resolve_type(resource_type)
        data = self._request("GET", res_type, params=params)
        if data is None:
            return Bundle(type="searchset", total=0, entry=[])
        return Bundle(data)

    def create(self, resource: FHIRResource | dict) -> FHIRResource:
        """Create a resource on the server: POST [base]/[resourceType]."""
        data = resource.to_dict() if isinstance(resource, FHIRResource) else resource
        res_type = data.get("resourceType")
        if not res_type:
            raise ValueError("Resource must have 'resourceType' to create")
        resp_data = self._request("POST", res_type, data=data)
        if resp_data is None:
            return FHIRResource.from_dict(data)
        return FHIRResource.from_dict(resp_data)

    def update(self, resource: FHIRResource | dict) -> FHIRResource:
        """Update a resource on the server: PUT [base]/[resourceType]/[id]."""
        data = resource.to_dict() if isinstance(resource, FHIRResource) else resource
        res_type = data.get("resourceType")
        res_id = data.get("id")
        if not res_type or not res_id:
            raise ValueError("Resource must have 'resourceType' and 'id' to update")
        resp_data = self._request("PUT", f"{res_type}/{res_id}", data=data)
        if resp_data is None:
            return FHIRResource.from_dict(data)
        return FHIRResource.from_dict(resp_data)

    def delete(self, resource_type: str | type[FHIRResource], id: str) -> bool:
        """Delete a resource by ID: DELETE [base]/[resourceType]/[id]."""
        res_type = self._resolve_type(resource_type)
        self._request("DELETE", f"{res_type}/{id}")
        return True
