"""
fhir_lite.version — FHIR version declarations and version-aware field aliases.

Provides a lightweight FHIRVersion enum and per-resource field alias maps so
that resources can be parsed and validated correctly for both R4 and R5 payloads
without adding any external dependency or megabyte-heavy schemas.

Usage::

    import fhir_lite
    fhir_lite.set_fhir_version("R5")

    # or as a context manager:
    from fhir_lite.version import fhir_version_context, FHIRVersion
    with fhir_version_context(FHIRVersion.R5):
        patient = fhir_lite.from_json(json_str)
"""

from __future__ import annotations

import threading
from enum import Enum
from contextlib import contextmanager
from typing import Generator


# ---------------------------------------------------------------------------
# Version enum
# ---------------------------------------------------------------------------

class FHIRVersion(str, Enum):
    """Supported FHIR specification versions."""
    R4 = "R4"
    R4B = "R4B"
    R5 = "R5"

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Thread-local active version
# ---------------------------------------------------------------------------

_local = threading.local()
_DEFAULT_VERSION: FHIRVersion = FHIRVersion.R4


def get_fhir_version() -> FHIRVersion:
    """Return the currently active FHIR version (thread-local, default R4)."""
    return getattr(_local, "version", _DEFAULT_VERSION)


def set_fhir_version(version: FHIRVersion | str) -> None:
    """Set the active FHIR version for the current thread.

    Args:
        version: A ``FHIRVersion`` member or string ``'R4'``, ``'R4B'``, ``'R5'``.

    Raises:
        ValueError: If the version string is not recognized.
    """
    if isinstance(version, str):
        try:
            version = FHIRVersion(version.upper())
        except ValueError:
            valid = ", ".join(v.value for v in FHIRVersion)
            raise ValueError(f"Unknown FHIR version '{version}'. Must be one of: {valid}")
    _local.version = version


@contextmanager
def fhir_version_context(version: FHIRVersion | str) -> Generator[FHIRVersion, None, None]:
    """Context manager to temporarily switch the active FHIR version.

    Restores the previous version when the block exits, even on exception.

    Example::

        with fhir_version_context("R5"):
            r5_resource = fhir_lite.from_json(r5_json)
    """
    previous = get_fhir_version()
    set_fhir_version(version)
    try:
        yield get_fhir_version()
    finally:
        _local.version = previous


# ---------------------------------------------------------------------------
# Version-aware field aliases
# ---------------------------------------------------------------------------
# Maps (resource_type, field_name) -> canonical field name for the given version.
# This allows resources to accept both R4 and R5 field names transparently.
#
# Currently known differences (non-exhaustive, focused on implemented resources):
#
#   Encounter.class  -> R4: CodeableConcept, R5: array of CodeableConcept (class_)
#   MedicationRequest.medicationCodeableConcept / medicationReference
#     -> R5 unified into medication[x] as CodeableReference
#   Condition.category -> mostly identical, minor value set changes
# ---------------------------------------------------------------------------

# Alias map: {resource_type: {r5_field: r4_field}}
# Used to normalize R5 field names to R4 canonical form
_R5_TO_R4_ALIASES: dict[str, dict[str, str]] = {
    "Encounter": {
        # R5 renamed class to class_ (array), we keep R4 semantics by default
        "class_": "class",
    },
    "MedicationRequest": {
        # R5 uses CodeableReference; we normalize gracefully
        "medication": "medicationCodeableConcept",
    },
    "Observation": {
        # R5 renamed some value types
        "valueAttachment": "valueAttachment",  # same, listed for completeness
    },
}

# Alias map: {resource_type: {r4_field: r5_field}}
_R4_TO_R5_ALIASES: dict[str, dict[str, str]] = {
    resource: {v: k for k, v in aliases.items()}
    for resource, aliases in _R5_TO_R4_ALIASES.items()
}


def normalize_field(resource_type: str, field: str) -> str:
    """Normalize a field name to the canonical form for the active FHIR version.

    In practice this is a no-op for most fields. It only applies when
    version is R5 and a known alias mapping exists.

    Args:
        resource_type: The FHIR resource type (e.g. ``'Encounter'``).
        field: The field name as received in a payload.

    Returns:
        The canonical field name for the active version.
    """
    version = get_fhir_version()
    if version == FHIRVersion.R5:
        aliases = _R5_TO_R4_ALIASES.get(resource_type, {})
        return aliases.get(field, field)
    # R4 / R4B: passthrough
    return field


def get_version_info() -> dict:
    """Return version metadata as a plain dict.

    Returns structured information about the active FHIR version and
    what compatibility modes are available.

    Example::

        >>> fhir_lite.get_version_info()
        {'active': 'R4', 'supported': ['R4', 'R4B', 'R5'], 'default': 'R4'}
    """
    return {
        "active": get_fhir_version().value,
        "supported": [v.value for v in FHIRVersion],
        "default": _DEFAULT_VERSION.value,
        "aliases": {
            "r5_to_r4": _R5_TO_R4_ALIASES,
            "r4_to_r5": _R4_TO_R5_ALIASES,
        },
    }


__all__ = [
    "FHIRVersion",
    "get_fhir_version",
    "set_fhir_version",
    "fhir_version_context",
    "normalize_field",
    "get_version_info",
]
