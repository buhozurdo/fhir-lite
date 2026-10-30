"""
fhir_lite.types — TypedDict definitions for common FHIR data structures.

These are optional structural types for IDE autocompletion and mypy checking.
They impose zero runtime cost and require no external dependencies.

Usage::

    from fhir_lite.types import HumanNameDict, CodingDict, IdentifierDict
"""

from __future__ import annotations

from typing import List, TypedDict


# ---------------------------------------------------------------------------
# Primitive-level helpers
# ---------------------------------------------------------------------------

class ExtensionDict(TypedDict, total=False):
    """FHIR Extension element."""
    url: str
    valueString: str
    valueBoolean: bool
    valueInteger: int
    valueDecimal: float
    valueCode: str
    valueCoding: "CodingDict"
    valueCodeableConcept: "CodeableConceptDict"
    valueReference: "ReferenceDict"
    extension: List["ExtensionDict"]


class CodingDict(TypedDict, total=False):
    """FHIR Coding — a code from a terminology system."""
    system: str
    version: str
    code: str
    display: str
    userSelected: bool


class CodeableConceptDict(TypedDict, total=False):
    """FHIR CodeableConcept — a concept that may be defined by a code."""
    coding: List[CodingDict]
    text: str


class ReferenceDict(TypedDict, total=False):
    """FHIR Reference — a reference to another resource."""
    reference: str
    type: str
    display: str


class QuantityDict(TypedDict, total=False):
    """FHIR Quantity — a measured amount."""
    value: float
    comparator: str
    unit: str
    system: str
    code: str


class PeriodDict(TypedDict, total=False):
    """FHIR Period — a time period with optional start/end."""
    start: str
    end: str


class IdentifierDict(TypedDict, total=False):
    """FHIR Identifier — a business identifier."""
    use: str
    type: CodeableConceptDict
    system: str
    value: str
    period: PeriodDict
    assigner: ReferenceDict


class HumanNameDict(TypedDict, total=False):
    """FHIR HumanName — a name for a human."""
    use: str
    text: str
    family: str
    given: List[str]
    prefix: List[str]
    suffix: List[str]
    period: PeriodDict


class ContactPointDict(TypedDict, total=False):
    """FHIR ContactPoint — details for telecom contact (phone, email, etc.)."""
    system: str
    value: str
    use: str
    rank: int
    period: PeriodDict


class AddressDict(TypedDict, total=False):
    """FHIR Address — a postal address."""
    use: str
    type: str
    text: str
    line: List[str]
    city: str
    district: str
    state: str
    postalCode: str
    country: str
    period: PeriodDict


class MetaDict(TypedDict, total=False):
    """FHIR Meta — metadata about a resource."""
    versionId: str
    lastUpdated: str
    source: str
    profile: List[str]
    security: List[CodingDict]
    tag: List[CodingDict]


# ---------------------------------------------------------------------------
# Resource-level dicts
# ---------------------------------------------------------------------------

class BundleEntryRequestDict(TypedDict, total=False):
    method: str
    url: str
    ifNoneMatch: str
    ifModifiedSince: str
    ifMatch: str
    ifNoneExist: str


class BundleEntryResponseDict(TypedDict, total=False):
    status: str
    location: str
    etag: str
    lastModified: str


class BundleEntryDict(TypedDict, total=False):
    """One entry inside a FHIR Bundle."""
    fullUrl: str
    resource: dict  # typed as dict since resource type varies
    request: BundleEntryRequestDict
    response: BundleEntryResponseDict


class DosageDict(TypedDict, total=False):
    """FHIR Dosage instruction for MedicationRequest."""
    sequence: int
    text: str
    patientInstruction: str
    route: CodeableConceptDict
    doseAndRate: List[dict]


class NarrativeDict(TypedDict, total=False):
    """FHIR Narrative — human-readable content."""
    status: str
    div: str


class IssueDict(TypedDict, total=False):
    """One issue inside an OperationOutcome."""
    severity: str  # fatal | error | warning | information
    code: str
    details: CodeableConceptDict
    diagnostics: str
    location: List[str]
    expression: List[str]


__all__ = [
    "ExtensionDict",
    "CodingDict",
    "CodeableConceptDict",
    "ReferenceDict",
    "QuantityDict",
    "PeriodDict",
    "IdentifierDict",
    "HumanNameDict",
    "ContactPointDict",
    "AddressDict",
    "MetaDict",
    "BundleEntryDict",
    "BundleEntryRequestDict",
    "BundleEntryResponseDict",
    "DosageDict",
    "NarrativeDict",
    "IssueDict",
]
