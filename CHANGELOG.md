# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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

[Unreleased]: https://github.com/BuhoZurdo/fhir-lite/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/BuhoZurdo/fhir-lite/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/BuhoZurdo/fhir-lite/releases/tag/v0.1.0
