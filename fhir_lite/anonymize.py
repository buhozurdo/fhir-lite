"""HIPAA Safe Harbor De-identification and Sanitization for FHIR.

Compliant with 45 CFR § 164.514(b)(2) (Safe Harbor Method), eliminating
the 18 protected health information (PHI) identifiers while preserving
clinical data integrity for analytics, machine learning, and research.
"""

from __future__ import annotations

import copy
import datetime
import hashlib
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

# Common FHIR date fields that may link to individuals
COMMON_DATE_FIELDS = {
    "birthDate",
    "deceasedDateTime",
    "deceasedDate",
    "effectiveDateTime",
    "authoredOn",
    "issued",
    "recordedDate",
    "occurrenceDateTime",
    "onsetDateTime",
    "abatementDateTime",
    "date",
}


@dataclass
class DeidConfig:
    """Configuration for HIPAA Safe Harbor de-identification.

    Attributes
    ----------
    remove_names : bool
        Whether to remove patient and practitioner names (default: True).
    name_placeholder : str | None
        If provided, sets name to [{"use": "anonymous", "family": name_placeholder}].
        If None, removes the name field entirely (default: "ANONYMOUS").
    remove_telecom : bool
        Whether to remove phone, email, fax, and contact points (default: True).
    remove_addresses : bool
        Whether to remove addresses (default: True).
    keep_state_and_country : bool
        If True and remove_addresses is True, retains state and country while
        removing street lines, cities, and zip codes (default: False).
    remove_identifiers : bool
        Whether to remove SSN, MRN, driver licenses, and account IDs (default: True).
    pseudonymize_id : bool
        Whether to replace resource IDs with deterministic SHA-256 hashes (default: False).
    salt : str
        Salt used for deterministic hashing (default: "").
    remove_photos : bool
        Whether to remove biometric and face images (default: True).
    remove_narratives : bool
        Whether to remove text.div free-text clinical notes that may leak PHI (default: True).
    date_handling : str
        Method for handling dates: "year_only", "shift", "remove", or "preserve" (default: "year_only").
    date_shift_days : int
        Days to shift dates when date_handling == "shift" (can be negative or positive) (default: 0).
    remove_extensions : bool
        Whether to strip custom extensions (default: False).
    """
    remove_names: bool = True
    name_placeholder: Optional[str] = "ANONYMOUS"
    remove_telecom: bool = True
    remove_addresses: bool = True
    keep_state_and_country: bool = False
    remove_identifiers: bool = True
    pseudonymize_id: bool = False
    salt: str = ""
    remove_photos: bool = True
    remove_narratives: bool = True
    date_handling: str = "year_only"  # "year_only", "shift", "remove", "preserve"
    date_shift_days: int = 0
    remove_extensions: bool = False


# Regex for ISO date matching (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS...)
_ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}):(\d{2}))?")


def _hash_id(original_id: str, salt: str = "") -> str:
    h = hashlib.sha256((original_id + salt).encode("utf-8")).hexdigest()
    return f"anon-{h[:12]}"


def _shift_date_iso(m: re.Match[str], shift_days: int) -> str:
    """Helper to shift date components by given days."""
    year = int(m.group(1))
    try:
        month = int(m.group(2))
        day = int(m.group(3))
        hour = int(m.group(4) or 0)
        minute = int(m.group(5) or 0)
        second = int(m.group(6) or 0)

        dt = datetime.datetime(year, month, day, hour, minute, second)
        shifted = dt + datetime.timedelta(days=shift_days)

        if m.group(4) is not None:
            return shifted.strftime("%Y-%m-%dT%H:%M:%SZ")
        return shifted.strftime("%Y-%m-%d")
    except Exception:
        return f"{year:04d}-01-01"


def _transform_date_string(val: str, config: DeidConfig) -> Optional[str]:
    mode = config.date_handling
    if mode == "preserve":
        return val
    if mode == "remove":
        return None

    m = _ISO_DATE_RE.match(val)
    if not m:
        # If it's already just a year e.g. "1980", preserve it
        if re.match(r"^\d{4}$", val):
            return val
        return None

    year = m.group(1)
    if mode == "year_only":
        return f"{year}-01-01"
    if mode == "shift":
        return _shift_date_iso(m, config.date_shift_days)

    return val


def _sanitize_period(period_dict: dict, config: DeidConfig) -> None:
    """Sanitize start and end date fields inside a period dictionary."""
    for p_key in ("start", "end"):
        val = period_dict.get(p_key)
        if isinstance(val, str):
            tr = _transform_date_string(val, config)
            if tr is None:
                period_dict.pop(p_key, None)
            else:
                period_dict[p_key] = tr


def _sanitize_date_field(data: dict, key: str, val: str, config: DeidConfig) -> None:
    """Sanitize a single date field in place."""
    transformed = _transform_date_string(val, config)
    if transformed is None:
        data.pop(key, None)
    else:
        data[key] = transformed


def _sanitize_nested_containers(data: dict, config: DeidConfig) -> None:
    """Recursively traverse nested dicts and lists to sanitize date fields."""
    for val in data.values():
        if isinstance(val, dict):
            _sanitize_dates_in_dict(val, config)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    _sanitize_dates_in_dict(item, config)


def _sanitize_dates_in_dict(data: dict, config: DeidConfig) -> None:
    date_keys = tuple(k for k in data if k in COMMON_DATE_FIELDS or k == "period")
    for key in date_keys:
        val = data.get(key)
        if key in COMMON_DATE_FIELDS and isinstance(val, str):
            _sanitize_date_field(data, key, val, config)
        elif key == "period" and isinstance(val, dict):
            _sanitize_period(val, config)

    _sanitize_nested_containers(data, config)


def _sanitize_names(data: dict, config: DeidConfig) -> None:
    if not config.remove_names or "name" not in data:
        return
    if config.name_placeholder:
        data["name"] = [{"use": "anonymous", "family": config.name_placeholder}]
    else:
        del data["name"]


def _sanitize_addresses(data: dict, config: DeidConfig) -> None:
    if not config.remove_addresses or "address" not in data:
        return
    if not config.keep_state_and_country or not isinstance(data["address"], list):
        del data["address"]
        return

    safe_addresses = []
    for addr in data["address"]:
        if isinstance(addr, dict):
            safe_addr = {
                k: addr[k]
                for k in ("state", "country", "use")
                if k in addr
            }
            if safe_addr:
                safe_addresses.append(safe_addr)
    if safe_addresses:
        data["address"] = safe_addresses
    else:
        del data["address"]


def _sanitize_contacts(data: dict, config: DeidConfig) -> None:
    contacts = data.get("contact")
    if not isinstance(contacts, list):
        return
    for c in contacts:
        if isinstance(c, dict):
            if config.remove_names:
                c.pop("name", None)
            if config.remove_telecom:
                c.pop("telecom", None)
            if config.remove_addresses:
                c.pop("address", None)


def _pseudonymize_resource_id(
    data: dict,
    config: DeidConfig,
    id_map: Optional[dict[str, str]],
) -> None:
    if not config.pseudonymize_id or "id" not in data:
        return
    old_id = data["id"]
    new_id = _hash_id(old_id, config.salt)
    data["id"] = new_id
    if id_map is not None:
        rtype = data.get("resourceType", "Resource")
        id_map[f"{rtype}/{old_id}"] = f"{rtype}/{new_id}"
        id_map[old_id] = new_id


def _anonymize_single_resource(data: dict, config: DeidConfig, id_map: Optional[dict[str, str]] = None) -> dict:
    """Anonymize a single FHIR resource dictionary according to HIPAA Safe Harbor."""
    _sanitize_names(data, config)

    if config.remove_telecom:
        data.pop("telecom", None)

    _sanitize_addresses(data, config)

    if config.remove_identifiers:
        data.pop("identifier", None)
    if config.remove_photos:
        data.pop("photo", None)
    if config.remove_narratives:
        data.pop("text", None)

    _sanitize_contacts(data, config)

    if config.remove_extensions:
        data.pop("extension", None)
        data.pop("modifierExtension", None)

    _sanitize_dates_in_dict(data, config)
    _pseudonymize_resource_id(data, config, id_map)

    return data


def _remap_reference_uri(ref: str, id_map: dict[str, str]) -> str:
    """Remap a reference URI using the pseudonymization ID map."""
    if ref in id_map:
        return id_map[ref]
    for old_ref, new_ref in id_map.items():
        if ref == old_ref or ref.endswith(f"/{old_ref}"):
            return new_ref
    return ref


def _update_bundle_references(bundle_data: dict, id_map: dict[str, str]) -> None:
    """Replace old reference URIs with new pseudonymized ones inside bundle entries."""
    def _traverse(node: Any) -> None:
        if isinstance(node, dict):
            ref = node.get("reference")
            if isinstance(ref, str):
                node["reference"] = _remap_reference_uri(ref, id_map)
            for v in node.values():
                _traverse(v)
        elif isinstance(node, list):
            for item in node:
                _traverse(item)

    _traverse(bundle_data)


def _anonymize_bundle(
    bundle_data: dict,
    config: DeidConfig,
    id_map: dict[str, str],
) -> None:
    """Anonymize all resources within a FHIR Bundle and update cross-references."""
    entries = bundle_data.get("entry")
    if not isinstance(entries, list):
        return
    for entry in entries:
        if isinstance(entry, dict):
            resource = entry.get("resource")
            if isinstance(resource, dict):
                _anonymize_single_resource(resource, config, id_map=id_map)

    if config.pseudonymize_id and id_map:
        _update_bundle_references(bundle_data, id_map)


def anonymize(
    resource_or_data: Any,
    config: Optional[DeidConfig] = None,
    in_place: bool = False,
) -> Any:
    """Anonymize a FHIR resource or Bundle in compliance with HIPAA Safe Harbor.

    Parameters
    ----------
    resource_or_data : Any
        FHIRResource instance or dictionary.
    config : DeidConfig, optional
        De-identification options (uses strict Safe Harbor defaults if None).
    in_place : bool, default False
        Whether to modify the resource in place or return a deep copy.

    Returns
    -------
    Any
        The sanitized resource instance or dictionary.
    """
    cfg = config or DeidConfig()

    is_fhir_resource = hasattr(resource_or_data, "data") and isinstance(resource_or_data.data, dict)
    data = resource_or_data.data if is_fhir_resource else resource_or_data

    if not isinstance(data, dict):
        raise TypeError(f"Expected FHIRResource or dict, got {type(resource_or_data).__name__}")

    working_data = data if in_place else copy.deepcopy(data)

    id_map: dict[str, str] = {}

    # Check if resource is a Bundle
    if working_data.get("resourceType") == "Bundle" and "entry" in working_data:
        _anonymize_bundle(working_data, cfg, id_map)
    else:
        _anonymize_single_resource(working_data, cfg, id_map=id_map)

    if not is_fhir_resource:
        return working_data
    if in_place:
        return resource_or_data
    cls = resource_or_data.__class__
    return cls(working_data)


__all__ = ["DeidConfig", "anonymize"]
