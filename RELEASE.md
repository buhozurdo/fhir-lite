# Release Process & Guidelines — FHIR Lite

This document outlines the branching strategy, release train pipeline, tagging conventions, step-by-step checklist, and the complete registry of release notes for all published tags in the **FHIR Lite** framework.

---

## 🌳 Branching Strategy

The repository follows a modified Gitflow / Release Train workflow with three core branch types:

```
[ feature/* ] ────────▶ [ dev ] ────────▶ [ release/vX.Y.0 ] ────────▶ [ main ]
(Individual features) (Integration &       (Stabilization & Beta)     (Production GA)
                       Alpha releases)
```

1. **`main` (Production / GA):**
   - Strictly reserved for stable, production-ready releases.
   - Every merge into `main` must be a non-fast-forward merge (`--no-ff`).
   - Every commit on `main` corresponding to a version bump receives an annotated Git tag: `vX.Y.Z`.
   - Direct commits to `main` are prohibited outside of release synchronizations.

2. **`dev` (Active Integration & Alphas):**
   - The primary staging branch for active engineering and feature integration.
   - Feature branches (`feature/*`) and bugfix branches (`fix/*`) merge into `dev` via `--no-ff`.
   - Alpha releases are cut and tagged directly on `dev`: `vX.Y.Z-alpha`.

3. **`release/vX.Y.0` (Stabilization & Betas):**
   - Forked from `dev` when all planned features for a release are feature-complete.
   - Enters feature freeze: only bug fixes, edge-case hardening, and documentation updates are accepted.
   - Tagged as `vX.Y.Z-beta`.
   - Once validated against CI/CD test matrices, merged with `--no-ff` into `main` (for GA tag `vX.Y.Z`) and merged back into `dev`.

---

## 🏷️ Versioning & Tagging Scheme

We strictly adhere to [Semantic Versioning 2.0.0](https://semver.org/) and [PEP 440](https://peps.python.org/pep-0440/):

| Stage | Git Tag Format | `pyproject.toml` version | Purpose |
| :--- | :--- | :--- | :--- |
| **Alpha** | `vX.Y.0-alpha` | `X.Y.0a0` | Active feature development on `dev`. |
| **Beta** | `vX.Y.0-beta` | `X.Y.0b0` | Feature-frozen stabilization on `release/vX.Y.0`. |
| **Release (GA)** | `vX.Y.0` | `X.Y.0` | Production general availability on `main`. |
| **Patch** | `vX.Y.Z` | `X.Y.Z` | Critical bug fixes or security patches. |

### 🏷️ Official Git Tag Registry (All Published Tags)

| Git Tag | Release Date | Target Commit | Channel | Release Summary |
| :--- | :---: | :---: | :---: | :--- |
| [`v0.5.0`](#v050--native-zero-dependency-fhirpath-mini-engine-cli-tools--hipaa-safe-harbor-de-identification) | 2026-11-16 | `baece2e` | **GA** | Native FHIRPath mini-engine, CLI tools & HIPAA Safe Harbor de-identification |
| [`v0.4.0`](#v040--http-resiliency-intelligent-retries-json-patch-conditional-create--semantic-extractors) | 2026-11-05 | `8907f76` | **GA** | Intelligent retries, JSON Patch, conditional create, semantic extractors & fluent builders |
| [`v0.3.0`](#v030--enterprise-rest-client-safe-deep-traversal--automated-cicd) | 2026-11-03 | `9b9defc` | **GA** | Enterprise FHIR client pagination, deep path traversal & automated CI/CD pipelines |
| [`v0.1.2`](#v012--safe-path-traversal-reference-helpers--enterprise-sslproxy-support) | 2026-10-31 | `b72014b` | **Patch** | Safe path traversal (`get_path`), Reference helper & enterprise SSL/proxy support |
| [`v0.1.1`](#v011--search-pagination-iter_search--batch-and-transaction-operations) | 2026-10-30 | `ddf78e0` | **Minor** | Multi-page search pagination (`iter_search`), batch & atomic transaction operations |
| [`v0.1.0`](#v010--zero-dependency-hl7-fhir-r4r4br5-foundational-engine) | 2026-10-30 | `6cd93ae` | **GA** | Foundational zero-dependency JSON/XML serializer, NDJSON streaming & core clinical models |

---

## 📋 Release Checklist & Release Train Pipeline

Before cutting an official release, the following checklist must be satisfied in order:

### 1. Pre-Release Validation & Quality Gates
- [ ] Run complete test suite: `pytest -v --cov=fhir_lite` (must pass 100% across all supported Python versions: 3.10, 3.11, 3.12, 3.13).
- [ ] Verify test coverage gate ($\ge 85\%$ line coverage required, zero regressions).
- [ ] Verify zero external runtime dependencies (`pip list` in isolated environment must show zero third-party wheels required for base `fhir-lite`).
- [ ] Validate typing: `mypy fhir_lite` passes with zero errors.

### 2. Version Synchronization & Documentation
- [ ] Update version in `pyproject.toml` (`version = "X.Y.Z"`).
- [ ] Update `__version__ = "X.Y.Z"` in `fhir_lite/__init__.py`.
- [ ] Update `CHANGELOG.md` with complete categorized changes under `## [X.Y.Z] - YYYY-MM-DD`.
- [ ] Update `RELEASE.md` with entry in Official Git Tag Registry and full Release Notes.

### 3. Packaging & Build Verification
- [ ] Clean previous artifacts: `Remove-Item -Recurse -Force dist, build, *.egg-info`.
- [ ] Build distribution packages: `python -m build`.
- [ ] Validate package metadata and rendering: `twine check dist/*`.

### 4. Git Tagging & Publishing
- [ ] Commit version bump: `git commit -m "chore(release): bump version to X.Y.Z"`.
- [ ] Create annotated Git tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z: <Summary>"`.
- [ ] Push to all designated remotes:
  - `git push origin main --tags`
  - `git push github main --tags`
- [ ] Monitor GitHub Actions workflow `Release and Publish` (`.github/workflows/python-publish.yml` and `release.yml`).
- [ ] Verify package index publication on PyPI: `https://pypi.org/project/fhir-lite/`.

---

## 📦 Official Release Notes Registry

---

### `v0.5.0` — Native Zero-Dependency FHIRPath Mini-Engine, CLI Tools & HIPAA Safe Harbor De-identification

> **Release Metadata**
>
> | Attribute | Details |
> | :--- | :--- |
> | **Git Tag** | `v0.5.0` |
> | **Release Date** | `2026-11-16` |
> | **Target Commit** | `baece2e` |
> | **Release Channel** | **GA (General Availability / Production)** |
> | **PR / Merge Title** | `feat: release v0.5.0 - FHIRPath mini-engine, CLI tools & HIPAA Safe Harbor de-identification` |
> | **PR Description** | Implements pure Python AST-based FHIRPath evaluation engine, complete HIPAA Safe Harbor de-identification pipeline with date shifting and reference pseudonymization, integrated `fhir-lite` CLI tool suite, and modernized CI/CD automation. |

#### 🚀 Key Highlights & Architectural Additions
- **Pure-Python FHIRPath Mini-Engine (`fhir_lite.fhirpath`):**
  - Zero third-party dependencies AST tokenizer, recursive-descent parser, and tree evaluator.
  - Dot-notation hierarchical navigation (`Patient.name.family`, `Observation.code.coding.code`).
  - Automatic collection flattening and unboxing (`name.given`).
  - `.where(...)` filtering with boolean logic (`and`, `or`), string matches, and numerical/relational comparisons (`<`, `<=`, `=`, `!=`, `>=`, `>`).
  - Comprehensive collection functions: `.exists()`, `.empty()`, `.first()`, `.last()`, `.count()`, `.skip(n)`, `.take(n)`, `.tail()`, `.distinct()`, `.as(Type)`.
  - String manipulation functions: `.contains()`, `.startsWith()`, `.endsWith()`, `.lower()`, `.upper()`, `.join()`.
  - Direct integration into resources: `FHIRResource.fhirpath("expression")` and module-level `evaluate_fhirpath()`.
- **HIPAA Safe Harbor De-identification (`fhir_lite.anonymize`):**
  - Fully compliant with 45 CFR § 164.514(b)(2) (Safe Harbor Method), eliminating or sanitizing all 18 PHI identifier categories.
  - `DeidConfig` with granular policies: names, telecom, addresses, identifiers, photos, narratives, and date manipulation (`year_only`, `shift`, `remove`, `preserve`).
  - Cryptographic salted pseudonymization for resource IDs.
  - Recursive `Bundle` anonymization with automatic cross-reference relinking (e.g. `Observation.subject.reference` points to pseudonymized Patient ID).
  - Direct helper: `resource.anonymize(config=None, in_place=False)`.
- **Integrated Command-Line Interface (`fhir-lite` CLI):**
  - Entrypoint `fhir-lite` and module executable `python -m fhir_lite`.
  - Subcommands: `convert` (bidirectional JSON $\leftrightarrow$ XML), `validate` (structural and clinical rule checking), `fhirpath` (shell query/filtering), and `anonymize` (terminal de-identification).
  - Full Unix pipeline support via stdin/stdout streaming.
- **CI/CD Hardening & PyPI Publishing:**
  - Automated multi-OS test matrix across Python 3.10, 3.11, 3.12, 3.13 on GitHub Actions.
  - PyPI publishing via OpenID Connect (OIDC) Trusted Publishing.
  - SonarQube Cloud automated quality gate scan.

#### 🧪 Validation & Test Suite Metrics
- Total Tests: **69 tests passing (100% success rate)**
- Line Coverage: **88% overall project coverage**
- Test Matrix: Python 3.10, 3.11, 3.12, 3.13 on Ubuntu and Windows runners
- Runtime Dependencies: **0 external dependencies (100% Python standard library)**

#### 🔄 Next Release Train Step
- `v0.6.0-alpha`: Embedded SQLite in-memory FHIR query engine, Bulk Data export parsing, and US-Core/IPS profile validation extensions.

---

### `v0.4.0` — HTTP Resiliency, Intelligent Retries, JSON Patch, Conditional Create & Semantic Extractors

> **Release Metadata**
>
> | Attribute | Details |
> | :--- | :--- |
> | **Git Tag** | `v0.4.0` |
> | **Release Date** | `2026-11-05` |
> | **Target Commit** | `8907f76` |
> | **Release Channel** | **GA (General Availability / Production)** |
> | **PR / Merge Title** | `feat: add retries, patch, conditional create, semantic extractors & fluent bundles (v0.4.0)` |
> | **PR Description** | Adds exponential backoff retries with Retry-After adherence, FHIR JSON Patch operations, conditional create idempotency headers, semantic extractors for identifiers/codes, and fluent Bundle transaction builders. |

#### 🚀 Key Highlights & Architectural Additions
- **Intelligent Client Retries with Exponential Backoff & Jitter:**
  - Configurable `FHIRClient(max_retries=3, backoff_factor=0.5)` with automatic retry logic on HTTP `429 Too Many Requests`, `502 Bad Gateway`, `503 Service Unavailable`, and `504 Gateway Timeout`.
  - Automatic inspection and parsing of standard HTTP `Retry-After` response headers (delta seconds).
- **Conditional Create & Idempotency:**
  - `FHIRClient.create(resource, if_none_exist="...")` supporting FHIR `If-None-Exist` HTTP header.
  - High-level `FHIRClient.get_or_create(resource, **search_params)` returning `(resource, created_bool)`.
- **FHIR JSON Patch:**
  - `FHIRClient.patch(resource_type, id, operations)` executing atomic partial updates using `application/json-patch+json`.
- **Semantic Extractors for Identifiers and Medical Codes:**
  - `FHIRResource.get_identifier(system=..., type_code=...)` for direct value extraction without manual nested dictionary/array loops.
  - `FHIRResource.get_coding(system=..., field="code")` for extracting code strings from `CodeableConcept` and `Coding` structures.
- **Fluent Transaction & Batch Builders:**
  - `Bundle.transaction(*entries)` and `Bundle.batch(*entries)` factory constructors.
  - Fluent interaction helpers: `Bundle.add_create()`, `Bundle.add_update()`, and `Bundle.add_delete()`.

#### 🧪 Validation & Test Suite Metrics
- Total Tests: **48 tests passing**
- Line Coverage: **91% overall project coverage**
- Test Matrix: Python 3.10, 3.11, 3.12

#### 🔄 Next Release Train Step
- `v0.5.0-alpha`: Implementation of pure-Python zero-dependency FHIRPath parser and evaluator.

---

### `v0.3.0` — Enterprise REST Client, Safe Deep Traversal & Automated CI/CD

> **Release Metadata**
>
> | Attribute | Details |
> | :--- | :--- |
> | **Git Tag** | `v0.3.0` |
> | **Release Date** | `2026-11-03` |
> | **Target Commit** | `9b9defc` |
> | **Release Channel** | **GA (General Availability / Production)** |
> | **PR / Merge Title** | `chore(release): bump version to 0.3.0` |
> | **PR Description** | Enterprise FHIR REST Client enhancements with link pagination, transaction bundles, safe nested path traversal, enterprise SSL/proxy support, and automated CI/CD pipeline integration. |

#### 🚀 Key Highlights & Architectural Additions
- **Enterprise FHIR REST Client Enhancements:**
  - Automatic multi-page search iterator (`FHIRClient.iter_search()`) and pagination navigation (`next_page()`, `prev_page()`).
  - Bundle link parsing helpers: `Bundle.next_url`, `Bundle.prev_url`, and `Bundle.get_link()`.
  - Atomic transactions and batch operations (`FHIRClient.transaction()` and `FHIRClient.batch()`).
  - Enterprise network hardening with custom `ssl.SSLContext` and HTTP/HTTPS proxy routing.
- **Safe Deep Path Traversal:**
  - `FHIRResource.get_path()` for safe navigation of nested FHIR dictionaries and lists using dot notation (`"name.0.family"`) or key sequences without raising `KeyError` or `IndexError`.
- **FHIR Reference Helpers:**
  - `Reference.parse()` and `Reference.create()` for parsing and constructing relative, absolute, and fragment references.
- **CI/CD & Code Quality Automation:**
  - Integrated SonarQube Cloud scanning and Codecov test results reporting.
  - Automated PyPI publishing pipeline configured via GitHub Actions.

#### 🧪 Validation & Test Suite Metrics
- Total Tests: **36 tests passing**
- Line Coverage: **91% project coverage**
- Test Matrix: Python 3.10, 3.11, 3.12

#### 🔄 Next Release Train Step
- `v0.4.0-alpha`: HTTP backoff retries, JSON Patch, conditional create, and fluent builders.

---

### `v0.1.2` — Safe Path Traversal, Reference Helpers & Enterprise SSL/Proxy Support

> **Release Metadata**
>
> | Attribute | Details |
> | :--- | :--- |
> | **Git Tag** | `v0.1.2` |
> | **Release Date** | `2026-10-31` |
> | **Target Commit** | `b72014b` |
> | **Release Channel** | **Patch** |
> | **PR / Merge Title** | `feat: add get_path, Reference helper, and SSL/proxy client support (v0.1.2)` |
> | **PR Description** | Adds safe path traversal for deeply nested dictionaries, Reference parsing and construction utilities, and enterprise SSL/proxy configuration for corporate networking. |

#### 🚀 Key Highlights & Architectural Additions
- **Safe Path Traversal (`FHIRResource.get_path`):**
  - Traverse deeply nested structures via string path (`"contact.0.telecom.0.value"`) or sequence (`["contact", 0, "telecom", 0, "value"]`).
  - Graceful fallback returning default value when keys or indices are missing.
- **FHIR Reference Parsing & Creation Helper (`Reference`):**
  - Parsing helper supporting relative references (`"Patient/123"`), absolute URLs (`"https://server/Patient/123"`), fragment references (`"#p1"`), and dictionary payloads.
  - Factory method `Reference.create(resource_type, id, display=None)`.
- **Enterprise SSL & Proxy Support:**
  - Custom `ssl_context` support in `FHIRClient` for private certificate authorities, self-signed certs, and mutual TLS (mTLS).
  - Explicit HTTP/HTTPS proxy support via `urllib.request.ProxyHandler`.

#### 🧪 Validation & Test Suite Metrics
- Total Tests: **28 tests passing**
- Line Coverage: **89% project coverage**

#### 🔄 Next Release Train Step
- `v0.3.0-alpha`: Comprehensive client overhaul and automated CI/CD integration.

---

### `v0.1.1` — Search Pagination (`iter_search`), Batch and Transaction Operations

> **Release Metadata**
>
> | Attribute | Details |
> | :--- | :--- |
> | **Git Tag** | `v0.1.1` |
> | **Release Date** | `2026-10-30` |
> | **Target Commit** | `ddf78e0` |
> | **Release Channel** | **Minor** |
> | **PR / Merge Title** | `chore(release): bump version to 0.1.1` |
> | **PR Description** | Adds search pagination iteration, Bundle link parsing helpers, and batch/transaction submission support in FHIRClient. |

#### 🚀 Key Highlights & Architectural Additions
- **FHIR Search Pagination & Link Navigation:**
  - `Bundle.get_link(relation)`, `Bundle.next_url`, and `Bundle.prev_url` properties.
  - `FHIRClient.next_page(bundle)` and `FHIRClient.prev_page(bundle)` for following searchset pagination links.
  - `FHIRClient.iter_search(resource_type, max_pages=None, **params)` generator streaming resources across pages transparently.
- **FHIR Batch & Transaction Operations:**
  - `FHIRClient.transaction(bundle)` and `FHIRClient.batch(bundle)` executing multi-entry operations via `POST [base]`.
  - Type-checking validation ensuring bundles match the expected bundle type.

#### 🧪 Validation & Test Suite Metrics
- Total Tests: **22 tests passing**
- Line Coverage: **88% project coverage**

#### 🔄 Next Release Train Step
- `v0.1.2`: Path traversal utility and network SSL/proxy configuration.

---

### `v0.1.0` — Zero-Dependency HL7 FHIR (R4/R4B/R5) Foundational Engine

> **Release Metadata**
>
> | Attribute | Details |
> | :--- | :--- |
> | **Git Tag** | `v0.1.0` |
> | **Release Date** | `2026-10-30` |
> | **Target Commit** | `6cd93ae` |
> | **Release Channel** | **GA (General Availability / Foundation)** |
> | **PR / Merge Title** | `ci: fix test collection in CI and remove tracked pycache` |
> | **PR Description** | Initial MVP release of FHIR Lite: zero-dependency bidirectional JSON/XML converter, NDJSON streaming, core clinical resources with __slots__ memory optimization, and pure-urllib REST client. |

#### 🚀 Key Highlights & Architectural Additions
- **Bidirectional JSON $\leftrightarrow$ XML Serializer:**
  - High-performance `json_to_xml()` and `xml_to_json()` converters without class overhead.
  - XML namespace support (`http://hl7.org/fhir`) and primitive `value` attribute mapping.
  - Lossless primitive extensions (`_element`) support in both directions.
  - XXE and XML entity expansion DoS prevention via `safe_fromstring()`.
- **Core Clinical & Administrative Resources:**
  - Base `FHIRResource` polymorphic model with `__slots__ = ("data",)` saving 40-50% memory.
  - Pre-built models: `Patient`, `Observation`, `Bundle`, `Practitioner`, `Encounter`, `Condition`, `MedicationRequest`, `Medication`, and `OperationOutcome`.
- **NDJSON & FHIR Bulk Data Streaming:**
  - Constant memory $O(1)$ streaming via `iter_ndjson()` with transparent gzip compression.
  - In-memory `loads_ndjson()` and `dumps_ndjson()`.
- **Zero-Dependency FHIR REST Client:**
  - Built exclusively on Python's standard `urllib.request`.
  - CRUD operations (`read`, `search`, `create`, `update`, `delete`), Basic & Bearer authentication, and `FHIRError` parsing into `OperationOutcome`.
- **Static Typing & Multi-version Support:**
  - PEP 561 `py.typed` marker and 17 `TypedDict` definitions.
  - Multi-version context: R4, R4B, R5 compatibility normalizer.
  - Lazy module loading via PEP 562 for sub-millisecond cold starts.

#### 🧪 Validation & Test Suite Metrics
- Total Tests: **18 tests passing**
- Line Coverage: **86% project coverage**
- Runtime Dependencies: **0 external dependencies**

#### 🔄 Next Release Train Step
- `v0.1.1`: Search pagination and transaction/batch operations.
