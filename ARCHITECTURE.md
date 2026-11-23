# FHIR Lite — Architecture & Technical Design

This document details the internal design decisions, memory layouts, and algorithmic choices behind **FHIR Lite**.

---

## 1. Core Architectural Tenets

```
┌──────────────────────────────────────────────────────────────────┐
│                           FHIR Lite                              │
├────────────────────┬───────────────────────┬─────────────────────┤
│ 1. Zero Dependency │ 2. O(1) Memory Layout │ 3. Native AST Engine│
│    Standard Library│    Slotted Resources  │    FHIRPath Mini    │
└────────────────────┴───────────────────────┴─────────────────────┘
```

1. **Zero External Runtime Dependencies:**
   - Every core parser, validator, and network client operates entirely within the standard Python runtime (`json`, `xml.etree.ElementTree`, `urllib.request`).
   - Prevents supply-chain attack vectors and reduces packaging size to under 100 KB.

2. **Serverless Cold-Start Optimization:**
   - Traditional FHIR libraries carry deep object models that incur 300 ms to 600 ms of module import latency.
   - `fhir-lite` achieves cold-start times of approximately 1 to 2 milliseconds, making it ideal for AWS Lambda, Google Cloud Functions, and Azure Functions.

---

## 2. Resource Memory Architecture

To minimize memory overhead during multi-thousand resource operations:
- High-frequency models utilize `__slots__` to suppress instance `__dict__` creation.
- Raw payload dictionaries are referenced internally without eager transformation into heavy nested wrapper trees.
- Field lookups leverage constant-time attribute delegates, falling back to dictionary mapping.

```
+------------------------------------------+
|            FHIRResource Instance         |
|  - _data: dict (Underlying JSON payload) |
|  - __slots__ footprint: ~48-56 bytes     |
+------------------------------------------+
```

---

## 3. High-Throughput Bundle Streaming

For large datasets (e.g., bundles containing 500 to 2,000+ entries):
- **Lazy Traversal:** `Bundle.iter_entries()` and `Bundle.iter_resources()` yield items dynamically using generator pipelines.
- **Type-Filtered Generators:** `Bundle.iter_resources_by_type("Observation")` reads raw entry metadata before instantiating objects, bypassing unnecessary allocations for non-matching resources.
- **Chunked JSON Emission:** `stream_json()` emits serialized chunks directly to disk or network sockets with bounded 64KB buffers.

---

## 4. Native FHIRPath AST Engine

The FHIRPath engine (`fhir_lite.fhirpath`) executes queries via a three-tier design:

```
[FHIRPath Query String]
         │
         ▼
[Lexer / Tokenizer]  --> Yields stream of typed tokens (IDENT, DOT, LITERAL, FUNC)
         │
         ▼
[Recursive Descent]  --> Builds abstract syntax tree (ASTNode hierarchy)
         │
         ▼
[Tree Evaluator]     --> Dispatches operations against context collections
```

- **Collection Flattening:** Automatically unwraps single-item collections and flattens nested arrays during dot-traversal.
- **Cognitive Complexity Guard:** Evaluator methods delegate to specialized dispatch functions, keeping cyclomatic and cognitive complexity metrics below strict quality thresholds ($\le 15$).

---

## 5. HIPAA Safe Harbor De-identification

The de-identification pipeline (`fhir_lite.anonymize`) implements standard Safe Harbor transformations:
- **Date Transformation:** Supports full removal, truncation to year-only, or uniform date shifting.
- **Identifier Pseudonymization:** Deterministic SHA-256 hashing salted with enterprise secrets to generate consistent surrogate IDs across distributed datasets.
- **Bundle Reference Remapping:** Automatically scans and updates relational references (`Patient/123` -> `Patient/anon-hash`) across transaction entries.
