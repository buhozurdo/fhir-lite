import base64
import json
import random
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import TypeVar, Any
from .resources import FHIRResource, Bundle, OperationOutcome

T = TypeVar("T", bound=FHIRResource)

METHOD_GET = "GET"
METHOD_POST = "POST"
METHOD_PUT = "PUT"
METHOD_DELETE = "DELETE"
METHOD_PATCH = "PATCH"

HEADER_IF_NONE_EXIST = "If-None-Exist"
HEADER_RETRY_AFTER = "Retry-After"
HEADER_CONTENT_TYPE = "Content-Type"

CONTENT_TYPE_JSON_PATCH = "application/json-patch+json"
CONTENT_TYPE_FHIR_JSON = "application/fhir+json; charset=utf-8"

BUNDLE_TYPE_TRANSACTION = "transaction"
BUNDLE_TYPE_BATCH = "batch"

DEFAULT_RETRY_STATUSES = {429, 502, 503, 504}


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


def _parse_retry_after(val: str | None) -> float | None:
    if not val:
        return None
    try:
        seconds = float(val)
        return min(max(seconds, 0.0), 60.0)
    except ValueError:
        return None


def _calculate_backoff(attempt: int, factor: float, retry_after: str | None) -> float:
    parsed = _parse_retry_after(retry_after)
    if parsed is not None:
        return parsed
    base = factor * (2 ** attempt)
    jitter = random.uniform(0, 0.1 * factor) if factor > 0 else 0.0
    return min(base + jitter, 60.0)


class FHIRClient:
    """Ultra-lightweight zero-dependency REST client for FHIR servers using urllib."""

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str] | None = None,
        auth: tuple[str, str] | str | None = None,
        timeout: float = 30.0,
        ssl_context: ssl.SSLContext | None = None,
        proxy: str | None = None,
        max_retries: int = 0,
        backoff_factor: float = 0.5,
        retry_statuses: set[int] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.ssl_context = ssl_context
        self.proxy = proxy
        self.max_retries = max(max_retries, 0)
        self.backoff_factor = max(backoff_factor, 0.0)
        self.retry_statuses = retry_statuses if retry_statuses is not None else DEFAULT_RETRY_STATUSES
        self._opener = self._build_opener(ssl_context, proxy)
        self.headers = {
            "Accept": "application/fhir+json, application/json",
            HEADER_CONTENT_TYPE: CONTENT_TYPE_FHIR_JSON,
        }
        if headers:
            self.headers.update(headers)
        if auth:
            self._setup_auth(auth)

    @staticmethod
    def _build_opener(ssl_ctx: ssl.SSLContext | None, proxy: str | None):
        if proxy is None and ssl_ctx is None:
            return None
        handlers: list[urllib.request.BaseHandler] = []
        if proxy:
            handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
        if ssl_ctx is not None:
            handlers.append(urllib.request.HTTPSHandler(context=ssl_ctx))
        return urllib.request.build_opener(*handlers)

    def _setup_auth(self, auth: tuple[str, str] | str) -> None:
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
        if path.startswith(("http://", "https://")):
            url = path
        elif not path or path == "/":
            url = self.base_url
        else:
            url = f"{self.base_url}/{path.lstrip('/')}"
        if not params:
            return url
        separator = "&" if "?" in url else "?"
        query = urllib.parse.urlencode(params, doseq=True)
        return f"{url}{separator}{query}"

    def _open_request(self, req: urllib.request.Request):
        if self._opener is not None:
            return self._opener.open(req, timeout=self.timeout)
        if self.ssl_context is not None:
            return urllib.request.urlopen(req, timeout=self.timeout, context=self.ssl_context)
        return urllib.request.urlopen(req, timeout=self.timeout)

    def _handle_http_retry(self, err: urllib.error.HTTPError, attempt: int) -> None:
        if attempt >= self.max_retries or err.code not in self.retry_statuses:
            err_msg, outcome = _parse_error_outcome(err)
            raise FHIRError(err.code, err_msg, outcome=outcome) from err
        retry_hdr = err.headers.get(HEADER_RETRY_AFTER) if err.headers else None
        wait_sec = _calculate_backoff(attempt, self.backoff_factor, retry_hdr)
        time.sleep(wait_sec)

    def _handle_url_retry(self, err: urllib.error.URLError, attempt: int) -> None:
        if attempt >= self.max_retries:
            raise FHIRError(0, f"Network error: {err.reason}") from err
        wait_sec = _calculate_backoff(attempt, self.backoff_factor, None)
        time.sleep(wait_sec)

    def _execute_request(self, req: urllib.request.Request) -> dict | None:
        attempt = 0
        while True:
            try:
                with self._open_request(req) as resp:
                    if resp.status == 204:
                        return None
                    resp_bytes = resp.read()
                    return json.loads(resp_bytes.decode("utf-8")) if resp_bytes else None
            except urllib.error.HTTPError as err:
                self._handle_http_retry(err, attempt)
                attempt += 1
            except urllib.error.URLError as err:
                self._handle_url_retry(err, attempt)
                attempt += 1

    def _request(
        self,
        method: str,
        path: str,
        data: dict | FHIRResource | None = None,
        raw_body: bytes | None = None,
        params: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> dict | None:
        url = self._build_url(path, params)
        body_bytes = raw_body if raw_body is not None else _encode_body(data)
        req_headers = dict(self.headers)
        if extra_headers:
            req_headers.update(extra_headers)

        req = urllib.request.Request(
            url=url,
            data=body_bytes,
            headers=req_headers,
            method=method,
        )

        return self._execute_request(req)

    def read(self, resource_type: str | type[T], id: str) -> T:
        """Fetch a specific resource by ID: GET [base]/[resourceType]/[id]."""
        res_type = self._resolve_type(resource_type)
        data = self._request(METHOD_GET, f"{res_type}/{id}")
        if data is None:
            raise FHIRError(404, f"Resource {res_type}/{id} returned empty content")
        return FHIRResource.from_dict(data)

    def search(self, resource_type: str | type[FHIRResource], **params) -> Bundle:
        """Search resources with query parameters: GET [base]/[resourceType]?params..."""
        res_type = self._resolve_type(resource_type)
        data = self._request(METHOD_GET, res_type, params=params)
        if data is None:
            return Bundle(type="searchset", total=0, entry=[])
        return Bundle(data)

    def next_page(self, bundle: Bundle) -> Bundle | None:
        """Fetch the next page of a searchset bundle using its 'next' link."""
        url = bundle.next_url
        if not url:
            return None
        data = self._request(METHOD_GET, url)
        return Bundle(data) if data else None

    def prev_page(self, bundle: Bundle) -> Bundle | None:
        """Fetch the previous page of a searchset bundle using its 'previous' or 'prev' link."""
        url = bundle.prev_url
        if not url:
            return None
        data = self._request(METHOD_GET, url)
        return Bundle(data) if data else None

    def iter_search(
        self,
        resource_type: str | type[FHIRResource],
        max_pages: int | None = None,
        **params,
    ):
        """Generator yielding resources across all paginated search pages."""
        current_bundle: Bundle | None = self.search(resource_type, **params)
        page_count = 0

        while current_bundle is not None:
            yield from current_bundle.iter_resources()
            page_count += 1
            if max_pages is not None and page_count >= max_pages:
                break
            current_bundle = self.next_page(current_bundle)

    def create(self, resource: FHIRResource | dict, if_none_exist: str | None = None) -> FHIRResource:
        """Create a resource on the server: POST [base]/[resourceType].
        
        Supports standard FHIR conditional create via the 'if_none_exist' parameter.
        """
        data = resource.to_dict() if isinstance(resource, FHIRResource) else resource
        res_type = data.get("resourceType")
        if not res_type:
            raise ValueError("Resource must have 'resourceType' to create")
        extra_headers = {HEADER_IF_NONE_EXIST: if_none_exist} if if_none_exist else None
        resp_data = self._request(METHOD_POST, res_type, data=data, extra_headers=extra_headers)
        if resp_data is None:
            return FHIRResource.from_dict(data)
        return FHIRResource.from_dict(resp_data)

    def get_or_create(self, resource: FHIRResource | dict, **search_params) -> tuple[FHIRResource, bool]:
        """Perform an idempotent conditional create using search parameters. Returns (resource, created_bool)."""
        if not search_params:
            raise ValueError("get_or_create requires at least one search parameter (e.g. identifier='...')")
        query_str = urllib.parse.urlencode(search_params, doseq=True)
        res = self.create(resource, if_none_exist=query_str)
        existing_id = (resource.to_dict() if isinstance(resource, FHIRResource) else resource).get("id")
        created = (res.id != existing_id) if existing_id else True
        return res, created

    def patch(
        self,
        resource_type: str | type[FHIRResource],
        id: str,
        operations: list[dict],
    ) -> FHIRResource:
        """Partially update a resource using FHIR JSON Patch: PATCH [base]/[resourceType]/[id]."""
        res_type = self._resolve_type(resource_type)
        if not isinstance(operations, list):
            raise TypeError("Patch operations must be a list of patch dicts")
        raw = json.dumps(operations, ensure_ascii=False).encode("utf-8")
        resp_data = self._request(
            METHOD_PATCH,
            f"{res_type}/{id}",
            raw_body=raw,
            extra_headers={HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON_PATCH},
        )
        if resp_data is None:
            raise FHIRError(404, f"Resource {res_type}/{id} not found or empty response on patch")
        return FHIRResource.from_dict(resp_data)

    def update(self, resource: FHIRResource | dict) -> FHIRResource:
        """Update a resource on the server: PUT [base]/[resourceType]/[id]."""
        data = resource.to_dict() if isinstance(resource, FHIRResource) else resource
        res_type = data.get("resourceType")
        res_id = data.get("id")
        if not res_type or not res_id:
            raise ValueError("Resource must have 'resourceType' and 'id' to update")
        resp_data = self._request(METHOD_PUT, f"{res_type}/{res_id}", data=data)
        if resp_data is None:
            return FHIRResource.from_dict(data)
        return FHIRResource.from_dict(resp_data)

    def delete(self, resource_type: str | type[FHIRResource], id: str) -> bool:
        """Delete a resource by ID: DELETE [base]/[resourceType]/[id]."""
        res_type = self._resolve_type(resource_type)
        self._request(METHOD_DELETE, f"{res_type}/{id}")
        return True

    def _send_bundle(self, bundle: Bundle | dict, expected_type: str) -> Bundle:
        data = bundle.to_dict() if isinstance(bundle, FHIRResource) else dict(bundle)
        b_type = data.get("type")
        if b_type and b_type != expected_type:
            raise ValueError(f"Bundle type must be '{expected_type}', got '{b_type}'")
        data["resourceType"] = "Bundle"
        data["type"] = expected_type
        resp = self._request(METHOD_POST, "", data=data)
        if resp is None:
            return Bundle(type=f"{expected_type}-response", entry=[])
        return Bundle(resp)

    def transaction(self, bundle: Bundle | dict) -> Bundle:
        """Execute a FHIR transaction bundle: POST [base]."""
        return self._send_bundle(bundle, expected_type=BUNDLE_TYPE_TRANSACTION)

    def batch(self, bundle: Bundle | dict) -> Bundle:
        """Execute a FHIR batch bundle: POST [base]."""
        return self._send_bundle(bundle, expected_type=BUNDLE_TYPE_BATCH)
