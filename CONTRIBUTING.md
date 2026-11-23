# Contributing to FHIR Lite

Thank you for your interest in contributing to **FHIR Lite**. Our goal is to provide a zero-dependency, ultra-lightweight, and auditable foundation for healthcare engineering worldwide.

---

## Guiding Principles

1. **Zero External Runtime Dependencies:** We strictly avoid adding external packages to `project.dependencies`. Every core capability must execute using standard Python primitives.
2. **Deterministic Performance:** Low memory footprint and sub-millisecond execution times are fundamental requirements.
3. **Clinical Correctness:** Serialized representations must adhere losslessly to HL7 FHIR standards (R4, R4B, R5).
4. **Comprehensive Test Coverage:** Every bugfix, refactoring, or feature must maintain a test coverage threshold of at least 88% and pass 100% of unit tests.

---

## Local Development Workflow

### 1. Prerequisites
- Python 3.9 or higher (3.11+ recommended).
- Git.

### 2. Setup
```bash
git clone https://github.com/BuhoZurdo/fhir-lite.git
cd fhir-lite

# Create and activate an isolated virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install development tooling
pip install -e ".[dev]"
```

### 3. Running the Test Suite
```bash
python -m pytest tests/ --cov=fhir_lite --cov-branch
```

### 4. Running Benchmarks
```bash
python benchmarks/benchmark.py
```

---

## Submitting Pull Requests

- Keep pull requests focused on a single feature, optimization, or bug fix.
- Follow conventional commits format: `feat(...)`, `fix(...)`, `perf(...)`, `refactor(...)`, `docs(...)`.
- Verify that your changes maintain 100% pass rates across test matrices and do not introduce SonarQube code smells or cognitive complexity violations.
