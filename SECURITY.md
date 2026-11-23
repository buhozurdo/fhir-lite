# Security Policy — FHIR Lite

## Supported Versions

We provide security updates and patches for active release lines:

| Version | Supported          |
| ------- | ------------------ |
| 0.6.x   | :white_check_mark: |
| 0.5.x   | :white_check_mark: |
| < 0.5.0 | :x:                |

## Reporting a Vulnerability

The **FHIR Lite** team takes the security of clinical software and protected health information (PHI) seriously.

If you believe you have found a security vulnerability (such as a parser denial-of-service, XML External Entity injection risk, path traversal, or de-identification bypass):

1. **Do not** open a public issue.
2. Email details to: `raelcorrales@gmail.com` with the subject tag `[SECURITY: fhir-lite]`.
3. Provide a clear description, reproducible proof-of-concept payload, and the affected version.

### Response SLA

- **Initial Acknowledgment:** Within 24 hours.
- **Triage & Assessment:** Within 72 hours.
- **Patch Release:** Target within 7 calendar days for high-severity or critical vulnerabilities.

## Security Architecture & Design Guarantees

- **XXE and XML Entity Protection:** XML parsers explicitly forbid DTD declarations and entity expansions to prevent XML bombs (Billion Laughs) and external resource retrieval.
- **Path Traversal Defenses (CWE-22):** CLI path arguments undergo strict canonicalization and validation via `_resolve_safe_path()`, rejecting null bytes and traversal sequences.
- **Zero Third-Party Dependency Guarantee:** Eliminates supply-chain exposure from external packages in runtime environments.
- **Deterministic HIPAA Safe Harbor De-identification:** Implements salted cryptographic hashing (SHA-256) and strict date-shifting mechanisms with no data leakage.
