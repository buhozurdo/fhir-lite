"""
FHIR Lite: Ultra-lightweight, zero-dependency FHIR library for Python.

Uses PEP 562 lazy module loading to ensure sub-millisecond cold starts
and minimal baseline memory footprint in serverless environments.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

__version__ = "0.1.2"

_MOD_RESOURCES = ".resources"
_MOD_CLIENT = ".client"
_MOD_SERIALIZER = ".serializer"
_MOD_NDJSON = ".ndjson"
_MOD_TYPES = ".types"
_MOD_VERSION = ".version"

# Mapping from public symbols to their internal modules for lazy loading
_SUBMODULE_MAP = {
    # Resources
    "FHIRResource": _MOD_RESOURCES,
    "Patient": _MOD_RESOURCES,
    "Observation": _MOD_RESOURCES,
    "Bundle": _MOD_RESOURCES,
    "Practitioner": _MOD_RESOURCES,
    "Encounter": _MOD_RESOURCES,
    "Condition": _MOD_RESOURCES,
    "MedicationRequest": _MOD_RESOURCES,
    "Medication": _MOD_RESOURCES,
    "OperationOutcome": _MOD_RESOURCES,
    "Reference": _MOD_RESOURCES,
    # Client
    "FHIRClient": _MOD_CLIENT,
    "FHIRError": _MOD_CLIENT,
    # Serializer
    "json_to_xml": _MOD_SERIALIZER,
    "xml_to_json": _MOD_SERIALIZER,
    "dict_to_xml": _MOD_SERIALIZER,
    "xml_to_dict": _MOD_SERIALIZER,
    "safe_fromstring": _MOD_SERIALIZER,
    # NDJSON
    "iter_ndjson": _MOD_NDJSON,
    "write_ndjson": _MOD_NDJSON,
    "loads_ndjson": _MOD_NDJSON,
    "dumps_ndjson": _MOD_NDJSON,
    # TypedDicts (fhir_lite.types)
    "ExtensionDict": _MOD_TYPES,
    "CodingDict": _MOD_TYPES,
    "CodeableConceptDict": _MOD_TYPES,
    "ReferenceDict": _MOD_TYPES,
    "QuantityDict": _MOD_TYPES,
    "PeriodDict": _MOD_TYPES,
    "IdentifierDict": _MOD_TYPES,
    "HumanNameDict": _MOD_TYPES,
    "ContactPointDict": _MOD_TYPES,
    "AddressDict": _MOD_TYPES,
    "MetaDict": _MOD_TYPES,
    "BundleEntryDict": _MOD_TYPES,
    "BundleEntryRequestDict": _MOD_TYPES,
    "BundleEntryResponseDict": _MOD_TYPES,
    "DosageDict": _MOD_TYPES,
    "NarrativeDict": _MOD_TYPES,
    "IssueDict": _MOD_TYPES,
    # Version API (fhir_lite.version)
    "FHIRVersion": _MOD_VERSION,
    "get_fhir_version": _MOD_VERSION,
    "set_fhir_version": _MOD_VERSION,
    "fhir_version_context": _MOD_VERSION,
    "normalize_field": _MOD_VERSION,
    "get_version_info": _MOD_VERSION,
}


def from_json(json_str: str):
    """Parse a FHIR JSON string into the appropriate FHIRResource instance."""
    from .resources import FHIRResource
    return FHIRResource.from_json(json_str)


def from_xml(xml_str: str):
    """Parse a FHIR XML string into the appropriate FHIRResource instance."""
    from .resources import FHIRResource
    return FHIRResource.from_xml(xml_str)


def __getattr__(name: str):
    """PEP 562 lazy loading: imports submodules on-demand when accessed."""
    submodule = _SUBMODULE_MAP.get(name)
    if submodule is not None:
        mod = importlib.import_module(submodule, __package__)
        val = getattr(mod, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    return __all__


__all__ = [
    # Resources
    "FHIRResource",
    "Patient",
    "Observation",
    "Bundle",
    "Practitioner",
    "Encounter",
    "Condition",
    "MedicationRequest",
    "Medication",
    "OperationOutcome",
    "Reference",
    # Client
    "FHIRClient",
    "FHIRError",
    # Convenience parsers
    "from_json",
    "from_xml",
    # Serializer
    "json_to_xml",
    "xml_to_json",
    "dict_to_xml",
    "xml_to_dict",
    "safe_fromstring",
    # NDJSON
    "iter_ndjson",
    "write_ndjson",
    "loads_ndjson",
    "dumps_ndjson",
    # TypedDicts (fhir_lite.types)
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
    # Version API (fhir_lite.version)
    "FHIRVersion",
    "get_fhir_version",
    "set_fhir_version",
    "fhir_version_context",
    "normalize_field",
    "get_version_info",
]


if TYPE_CHECKING:
    from .resources import (
        FHIRResource,
        Patient,
        Observation,
        Bundle,
        Practitioner,
        Encounter,
        Condition,
        MedicationRequest,
        Medication,
        OperationOutcome,
        Reference,
    )
    from .client import (
        FHIRClient,
        FHIRError,
    )
    from .serializer import (
        json_to_xml,
        xml_to_json,
        dict_to_xml,
        xml_to_dict,
        safe_fromstring,
    )
    from .ndjson import (
        iter_ndjson,
        write_ndjson,
        loads_ndjson,
        dumps_ndjson,
    )
    from .types import (
        ExtensionDict,
        CodingDict,
        CodeableConceptDict,
        ReferenceDict,
        QuantityDict,
        PeriodDict,
        IdentifierDict,
        HumanNameDict,
        ContactPointDict,
        AddressDict,
        MetaDict,
        BundleEntryDict,
        BundleEntryRequestDict,
        BundleEntryResponseDict,
        DosageDict,
        NarrativeDict,
        IssueDict,
    )
    from .version import (
        FHIRVersion,
        get_fhir_version,
        set_fhir_version,
        fhir_version_context,
        normalize_field,
        get_version_info,
    )
