# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.6.0] - 2026-11-19

### Added
- **Bundle Lazy Evaluation & High-Throughput Streaming:**
  - `Bundle.iter_entries()`: Yields raw entry dictionaries lazily without list allocations.
  - `Bundle.iter_resources()`: Generates typed `FHIRResource` instances on demand.
  - `Bundle.iter_resources_by_type()`: Filters on raw dictionaries (`resourceType`) before instantiating objects, eliminating 99% of class wrapper overhead on large bundles (7.4x to 15x faster on 2,000-entry bundles).
  - `Bundle.iter_raw_resources()`: Streams raw inner resource dictionaries directly with zero class overhead.
  - `Bundle.filter_entries()`: Arbitrary predicate-based filtering on raw entries/resources.
  - `Bundle.stream_json()` & `Bundle.iter_json()`: Incremental JSON serialization streaming chunks directly to IO text streams or network sockets without building monolithic in-memory strings.
- **NDJSON Bulk Data Streaming & Acceleration:**
  - Bounded 64KB I/O buffer (`buffering=65536`) on file streams for high-throughput batch reading/writing.
  - Optional auto-detected C serializers (`orjson` and `ujson`) with zero-dependency fallback to standard `json`.
  - Batching line buffer in `write_ndjson` to minimize system calls.
  - `iter_ndjson_raw()` & `iter_loads_ndjson_raw()`: Direct raw dictionary streaming for high-throughput ETL pipelines (Flatiron / Epic Systems FHIR Bulk Data).
  - `iter_loads_ndjson()`: Lazy in-memory parser yielding resources on demand.
  - `iter_dumps_ndjson()`: Lazy generator emitting serialized NDJSON lines.
- **Pre-compiled Fast-Path Validations:**
  - Migrated `VALID_STATUSES`, `VALID_GENDERS`, and `VALID_TYPES` to immutable `frozenset` for accelerated $O(1)$ set membership lookups.
  - Added pre-compiled `COMMON_UCUM_UNITS` in `Observation` for fast-path clinical unit validation.

### Fixed
- **Security Hardening in CLI (CWE-22 / CWE-73):**
  - Canonical path resolution and sanitization (`_resolve_safe_path`) in `fhir_lite/cli.py` mitigating Path Traversal vulnerabilities from faulty or adversarial LLM-supplied arguments.
  - Defensive error handling in CLI subcommands (`convert`, `validate`, `fhirpath`, `anonymize`) with clean error reporting to `sys.stderr` and exit code 1.

---

## [0.5.0] - 2026-11-16

### Added
- **Native Zero-Dependency FHIRPath Mini-Engine (`fhir_lite.fhirpath`):**
  - AST-based tokenizer, recursive-descent parser, and evaluator written in pure Python.
  - Dot-notation hierarchical navigation (`Patient.name.family`, `Observation.code.coding.code`).
  - Safe automatic array flattening and unpackaging (`name.given`).
  - `.where(...)` filtering with boolean logic (`and`, `or`), equality (`=`, `!=`), and numerical/relational comparisons (`<`, `<=`, `>`, `>=`).
  - Collection operators: `.exists([criteria])`, `.empty()`, `.first()`, `.last()`, `.count()`, `.skip(n)`, `.take(n)`, `.tail()`, `.distinct()`, `.as(ResourceType)`.
  - String manipulation functions: `.contains()`, `.startsWith()`, `.endsWith()`, `.lower()`, `.upper()`, `.join()`.
  - Direct integration method: `FHIRResource.fhirpath(expression, first=False)`.
  - Top-level function: `fhir_lite.evaluate_fhirpath(resource_or_data, expression, first=False)`.
- **Integrated Command-Line Interface (CLI - `fhir-lite` / `python -m fhir_lite`):**
  - Direct entrypoint script `fhir-lite` and module execution `python -m fhir_lite`.
  - `convert`: Bidirectional conversion between JSON and XML with auto-detection, `--to [json|xml]`, `--indent`, and `--no-pretty`.
  - `validate`: Syntax and clinical/structural rules validation with detailed issue breakdown.
  - `fhirpath`: Shell-level querying and filtering with JSON output or line-by-line text (`-f text`), `--first`.
  - `anonymize`: Terminal-driven HIPAA Safe Harbor de-identification.
  - Native Unix pipe streaming support (`cat input.json | fhir-lite convert --to xml > output.xml`).
- **HIPAA Safe Harbor De-identification and Sanitization (`fhir_lite.anonymize`):**
  - Compliance with 45 CFR § 164.514(b)(2) (Safe Harbor Method), eliminating or sanitizing all 18 PHI identifier categories.
  - `DeidConfig` with configurable policies: `remove_names`, `name_placeholder`, `remove_telecom`, `remove_addresses`, `keep_state_and_country`, `remove_identifiers`, `pseudonymize_id`, `salt`, `remove_photos`, `remove_narratives`, `date_handling` (`year_only`, `shift`, `remove`, `preserve`), `date_shift_days`, `remove_extensions`.
  - Recursive `Bundle` sanitization with automatic cross-reference relinking (`Observation.subject.reference` updated to pseudonymized patient ID).
  - Direct integration: `FHIRResource.anonymize(config=None, in_place=False)`.
- **GitHub Actions Workflows Modernization:**
  - Standardized CI/CD pipelines across `build.yml`, `ci.yml`, `sonar.yml`, `python-publish.yml`, and `release.yml`.
  - PyPI publishing via OpenID Connect (OIDC) Trusted Publishing.
  - Automatic GitHub Release asset building and attachment.
  - SonarQube Cloud scanning and Codecov coverage aggregation.

---

## [0.4.0] - 2026-11-04

### Added
- **Intelligent Client Retries with Exponential Backoff & Jitter:**
  - `FHIRClient(max_retries=3, backoff_factor=0.5)` with automatic retry on `429 Too Many Requests`, `502`, `503`, and `504`.
  - Automatic inspection and adherence to standard HTTP `Retry-After` header seconds.
- **FHIR Conditional Create & Idempotency:**
  - `FHIRClient.create(resource, if_none_exist="...")` supporting standard FHIR `If-None-Exist` headers.
  - High-level `FHIRClient.get_or_create(resource, **search_params)` returning `(resource, created_bool)`.
- **FHIR JSON Patch:**
  - `FHIRClient.patch(resource_type, id, operations)` for atomic partial resource updates via `application/json-patch+json`.
- **Semantic Extractors for Identifiers and Medical Codes:**
  - `FHIRResource.get_identifier(system=..., type_code=...)` for instant extraction without manual array looping.
  - `FHIRResource.get_coding(system=..., field="code")` for extracting codes from `CodeableConcept` and `Coding` structures.
- **Fluent Transaction & Batch Builders:**
  - `Bundle.transaction(*entries)` and `Bundle.batch(*entries)`.
  - Fluent interaction helpers `Bundle.add_create()`, `Bundle.add_update()`, and `Bundle.add_delete()`.

---

## [0.3.0] - 2026-11-03

### Added
- **Enterprise FHIR REST Client Enhancements:**
  - Automatic multi-page search iterator (`FHIRClient.iter_search()`) and page navigation (`next_page()`, `prev_page()`).
  - Bundle link parsing helpers (`Bundle.next_url`, `Bundle.prev_url`, and `Bundle.get_link()`).
  - Atomic transactions and batch operations (`FHIRClient.transaction()` and `FHIRClient.batch()`).
  - Network hardening with custom SSL context (`ssl_context`) and HTTP/HTTPS proxy support.
- **Safe Deep Path Traversal:**
  - `FHIRResource.get_path()` for safe navigation of deeply nested FHIR data with dot notation or key sequences without `KeyError` or `IndexError`.
- **FHIR Reference Helpers:**
  - `Reference.parse()` and `Reference.create()` for handling relative, absolute, and contained reference identifiers.
- **CI/CD & Code Quality Automation:**
  - SonarQube Cloud scanning with automated test coverage reporting (>91% coverage).
  - Codecov test results and coverage reporting (`codecov-action@v5` and `test-results-action@v1`).
  - Automated PyPI publishing pipeline via GitHub Actions using OpenID Connect (OIDC) Trusted Publishing.

---

## [0.1.2] - 2026-10-31

### Added
- **Safe Path Traversal (`FHIRResource.get_path`):**
  - Safely traverse deeply nested FHIR data structures using dot notation (e.g. `patient.get_path("name.0.family")`) or key sequences (`["name", 0, "family"]`).
  - Gracefully handles missing keys, out-of-range list indices, and non-dict/list leaves, returning an optional `default` value without throwing `KeyError` or `IndexError`.
- **FHIR Reference Parsing & Creation Helper (`Reference`):**
  - `Reference.parse()` for parsing relative reference strings (`Patient/123`), absolute URLs (`https://hapi.fhir.org/.../Patient/123`), fragment references (`#contained`), or reference dictionaries (`{"reference": ..., "display": ...}`).
  - `Reference.create()` for generating valid FHIR reference dictionaries from resource types and IDs.
  - Exported at top-level package namespace with lazy-loading support.
- **Enterprise SSL & Proxy Support in `FHIRClient`:**
  - Added `ssl_context: ssl.SSLContext | None = None` support for corporate intranets, self-signed certificates, and mutual TLS (mTLS).
  - Added `proxy: str | None = None` support for HTTP/HTTPS proxy routing via `urllib.request.ProxyHandler`.

---

## [0.1.1] - 2026-10-30

### Added
- **FHIR Search Pagination & Link Navigation:**
  - `Bundle.get_link(relation)`, `Bundle.next_url`, and `Bundle.prev_url` helper properties for parsing FHIR `link` arrays (supports both `previous` and `prev` relations).
  - `FHIRClient.next_page(bundle)` and `FHIRClient.prev_page(bundle)` to follow searchset pagination links transparently.
  - `FHIRClient.iter_search(resource_type, max_pages=None, **params)` generator to stream and yield resources seamlessly across multiple paginated pages.
- **FHIR Batch & Transaction Operations:**
  - `FHIRClient.transaction(bundle)` and `FHIRClient.batch(bundle)` to execute atomic operations via `POST [base]`.
  - Type validation verifying that incoming bundles match the expected `transaction` or `batch` type before submission.

---

## [0.1.0] - 2026-10-30

### Added
- **Bidirectional JSON $\leftrightarrow$ XML Serializer:**
  - `json_to_xml()` and `xml_to_json()` for high-performance direct payload conversion without class overhead.
  - Native XML namespace support (`http://hl7.org/fhir`) and primitive `value` attribute handling.
  - Lossless primitive extensions (`_element`) support in both XML and JSON representations.
- **Security Hardening:**
  - `safe_fromstring()` XML parsing utility rejecting DTD and external entities (XXE and entity expansion DoS prevention).
- **Core Clinical & Administrative Resources:**
  - Polymorphic base `FHIRResource` with dictionary and attribute access.
  - Pre-built resources with built-in validation rules:
    - `Patient` (gender, active validation)
    - `Observation` (mandatory status, code, status set validation)
    - `Bundle` (`add_entry()`, `get_resources()`, `iter_resources()`, `get_resources_by_type()`)
    - `Practitioner` (gender, active validation)
    - `Encounter` (status, class/class_ validation)
    - `Condition` (subject/patient validation)
    - `MedicationRequest` (status, intent, subject validation)
    - `Medication` (status validation)
    - `OperationOutcome` (severity, issues, `is_error`, `first_text()` convenience helpers)
- **NDJSON & FHIR Bulk Data Streaming:**
  - `iter_ndjson()` for memory-constant $O(1)$ streaming of massive datasets.
  - Transparent gzip (`.gz`) compression and decompression support.
  - In-memory `loads_ndjson()` and `dumps_ndjson()`.
- **Zero-Dependency FHIR REST Client:**
  - `FHIRClient` using Python's standard `urllib` supporting `read()`, `search()`, `create()`, `update()`, `delete()`.
  - HTTP Basic and Bearer token authentication.
  - Structured `FHIRError` parsing server error payloads into `OperationOutcome` instances.
- **Type Hints & Static Analysis:**
  - PEP 561 `py.typed` marker enabling full IDE autocompletion and mypy validation.
  - 17 standard `TypedDict` definitions (`HumanNameDict`, `CodingDict`, `IdentifierDict`, `IssueDict`, etc.).
- **FHIR Version Profiles (R4 / R4B / R5):**
  - `FHIRVersion` enum and `fhir_version_context()` context manager for multi-version workloads.
  - Automatic field normalization (`normalize_field()`) across R4 and R5 differences.
- **Optional Pydantic Interoperability:**
  - `FHIRResource.from_pydantic()` and `resource.to_pydantic()` compatible with Pydantic v1 and v2.
  - Zero base dependencies preserved (`[project.optional-dependencies] pydantic = ["pydantic>=2.0"]`).
- **Performance Optimizations:**
  - `__slots__ = ("data",)` implemented across all resource classes, eliminating per-instance `__dict__` and saving ~40-50% RAM.
  - PEP 562 lazy module loading in `fhir_lite/__init__.py`, achieving sub-millisecond cold start times in serverless environments.
- **Packaging:**
  - PEP 517/621 `pyproject.toml` configuration with strict packaging exclusions.
- **Test Suites:**
  - 9 standalone test suites covering security, serialization, streaming, typing, versions, optimization, and client without external dependencies.

[Unreleased]: https://github.com/BuhoZurdo/fhir-lite/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/BuhoZurdo/fhir-lite/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/BuhoZurdo/fhir-lite/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/BuhoZurdo/fhir-lite/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/BuhoZurdo/fhir-lite/compare/v0.1.2...v0.3.0
[0.1.2]: https://github.com/BuhoZurdo/fhir-lite/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/BuhoZurdo/fhir-lite/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/BuhoZurdo/fhir-lite/releases/tag/v0.1.0
