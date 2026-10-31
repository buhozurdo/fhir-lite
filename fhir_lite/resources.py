import json
import xml.etree.ElementTree as ET
from typing import Any
from .serializer import dict_to_xml, xml_to_dict, safe_fromstring, COMMON_ARRAY_FIELDS


def _traverse_segment(current: Any, segment: str | int) -> tuple[bool, Any]:
    """Traverse one dictionary key or list index safely. Returns (found, value)."""
    if isinstance(current, dict):
        str_seg = str(segment)
        if str_seg in current:
            return True, current[str_seg]
        return False, None
    if isinstance(current, (list, tuple)):
        try:
            idx = int(segment)
            if 0 <= idx < len(current):
                return True, current[idx]
        except (ValueError, TypeError):
            pass
    return False, None



class FHIRResource:
    """Base FHIR resource class with dictionary-like access and bidirectional serialization."""
    __slots__ = ("data",)
    _registry: dict[str, type["FHIRResource"]] = {}
    resource_type: str = "Resource"
    array_fields: set[str] = set()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "resource_type") and cls.resource_type != "Resource":
            cls._registry[cls.resource_type] = cls

    def __init__(self, data: dict | None = None, **kwargs):
        self.data: dict = dict(data) if data is not None else {}
        self.data.update(kwargs)
        if "resourceType" not in self.data and self.resource_type != "Resource":
            self.data["resourceType"] = self.resource_type

    @classmethod
    def from_dict(cls, data: dict) -> "FHIRResource":
        res_type = data.get("resourceType", cls.resource_type)
        target_cls = cls if cls is not FHIRResource else cls._registry.get(res_type, cls)
        return target_cls(data)

    @classmethod
    def from_json(cls, json_str: str) -> "FHIRResource":
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_xml(cls, xml_str: str) -> "FHIRResource":
        root = safe_fromstring(xml_str)
        res_type = root.tag.split("}")[-1] if "}" in root.tag else root.tag
        target_cls = cls if cls is not FHIRResource else cls._registry.get(res_type, cls)
        arrays = target_cls.array_fields | COMMON_ARRAY_FIELDS
        parsed = xml_to_dict(root, array_fields=arrays)
        data = parsed if isinstance(parsed, dict) else {}
        data["resourceType"] = res_type
        return target_cls(data)

    @classmethod
    def from_pydantic(cls, model_instance) -> "FHIRResource":
        """Instantiate a FHIRResource from a Pydantic model (compatible with v1 or v2).
        
        Extracts raw dictionary representation and polymorphically returns
        the registered resource subclass if applicable.
        """
        if hasattr(model_instance, "model_dump"):
            data = model_instance.model_dump(exclude_unset=False, by_alias=True)
        elif hasattr(model_instance, "dict"):
            data = model_instance.dict(by_alias=True)
        else:
            raise TypeError(
                f"Expected Pydantic model instance with 'model_dump()' or 'dict()', got {type(model_instance).__name__}"
            )
        return cls.from_dict(data)

    def to_pydantic(self, model_cls: type):
        """Convert this resource to an instance of the given Pydantic model class (v1 or v2)."""
        if hasattr(model_cls, "model_validate"):
            return model_cls.model_validate(self.data)
        elif hasattr(model_cls, "parse_obj"):
            return model_cls.parse_obj(self.data)
        else:
            try:
                return model_cls(**self.data)
            except Exception as e:
                raise ValueError(f"Failed to instantiate {model_cls.__name__} from resource data: {e}") from e

    def to_dict(self) -> dict:
        return dict(self.data)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.data, indent=indent, ensure_ascii=False)

    def to_xml(self, pretty: bool = True) -> str:
        root_tag = self.data.get("resourceType", self.resource_type)
        elem = dict_to_xml(self.data, root_tag=root_tag)
        if pretty:
            ET.indent(elem)
        return ET.tostring(elem, encoding="unicode")

    def validate(self) -> list[str]:
        """Validate resource attributes. Returns list of error messages (empty if valid)."""
        errors = []
        expected = self.resource_type
        actual = self.data.get("resourceType")
        if expected != "Resource" and actual != expected:
            errors.append(f"Invalid resourceType: expected '{expected}', got '{actual}'")
        return errors

    @property
    def is_valid(self) -> bool:
        return len(self.validate()) == 0

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def get_path(self, path: str | list[str | int], default: Any = None) -> Any:
        """Safely traverse deeply nested FHIR data using dot-notation or a key/index sequence."""
        segments = path.split(".") if isinstance(path, str) else path
        if not isinstance(segments, (list, tuple)):
            return default
        current: Any = self.data
        for seg in segments:
            found, current = _traverse_segment(current, seg)
            if not found:
                return default
        return current if current is not None else default

    def __getitem__(self, key: str):
        return self.data[key]

    def __setitem__(self, key: str, value):
        self.data[key] = value

    def __delitem__(self, key: str):
        del self.data[key]

    def __contains__(self, key: str) -> bool:
        return key in self.data

    def __getattr__(self, name: str):
        if name in ("data", "_registry", "resource_type", "array_fields"):
            return super().__getattribute__(name)
        if name in self.data:
            return self.data[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value):
        if name == "data":
            super().__setattr__(name, value)
        elif hasattr(self, "data"):
            self.data[name] = value
        else:
            super().__setattr__(name, value)

    def __repr__(self) -> str:
        res_id = self.data.get("id")
        return f"<{self.__class__.__name__} id={res_id!r}>"


class Patient(FHIRResource):
    """FHIR Patient resource."""
    __slots__ = ()
    resource_type = "Patient"
    array_fields = {
        "identifier", "name", "telecom", "address", "contact",
        "communication", "generalPractitioner"
    }
    VALID_GENDERS = {"male", "female", "other", "unknown"}

    def validate(self) -> list[str]:
        errors = super().validate()
        gender = self.data.get("gender")
        if gender is not None and gender not in self.VALID_GENDERS:
            errors.append(f"Invalid gender '{gender}'. Must be one of: {', '.join(sorted(self.VALID_GENDERS))}")
        active = self.data.get("active")
        if active is not None and not isinstance(active, bool):
            errors.append(f"Field 'active' must be a boolean, got {type(active).__name__}")
        return errors


class Observation(FHIRResource):
    """FHIR Observation resource."""
    __slots__ = ()
    resource_type = "Observation"
    array_fields = {
        "identifier", "basedOn", "partOf", "category", "focus",
        "performer", "interpretation", "note", "bodySite",
        "referenceRange", "hasMember", "derivedFrom", "component"
    }
    VALID_STATUSES = {
        "registered", "preliminary", "final", "amended",
        "corrected", "cancelled", "entered-in-error", "unknown"
    }

    def validate(self) -> list[str]:
        errors = super().validate()
        status = self.data.get("status")
        if not status:
            errors.append("Observation requires 'status'")
        elif status not in self.VALID_STATUSES:
            errors.append(f"Invalid status '{status}'. Must be one of: {', '.join(sorted(self.VALID_STATUSES))}")
        if "code" not in self.data:
            errors.append("Observation requires 'code'")
        return errors


class Bundle(FHIRResource):
    """FHIR Bundle resource for batch, transaction, searchset, and collection interactions."""
    __slots__ = ()
    resource_type = "Bundle"
    array_fields = {"entry", "link", "identifier"}
    VALID_TYPES = {
        "document", "message", "transaction", "transaction-response",
        "batch", "batch-response", "history", "searchset", "collection"
    }

    def validate(self) -> list[str]:
        errors = super().validate()
        b_type = self.data.get("type")
        if not b_type:
            errors.append("Bundle requires 'type'")
        elif b_type not in self.VALID_TYPES:
            errors.append(f"Invalid Bundle type '{b_type}'. Must be one of: {', '.join(sorted(self.VALID_TYPES))}")
        return errors

    @property
    def entries(self) -> list[dict]:
        """Returns the list of raw entry dicts."""
        return self.data.get("entry", [])

    def get_link(self, relation: str) -> str | None:
        """Find the URL for a specific link relation (e.g. 'next', 'previous', 'self')."""
        links = self.data.get("link", [])
        if not isinstance(links, list):
            return None
        target = ("previous", "prev") if relation in ("previous", "prev") else (relation,)
        for item in links:
            if isinstance(item, dict) and item.get("relation") in target:
                return item.get("url")
        return None

    @property
    def next_url(self) -> str | None:
        """Returns the URL of the 'next' link in the Bundle, if present."""
        return self.get_link("next")

    @property
    def prev_url(self) -> str | None:
        """Returns the URL of the 'previous' or 'prev' link in the Bundle, if present."""
        return self.get_link("previous")

    def get_resources(self) -> list[FHIRResource]:
        """Extract all inner entry resources as typed FHIRResource instances."""
        resources = []
        for entry in self.entries:
            if isinstance(entry, dict) and "resource" in entry and isinstance(entry["resource"], dict):
                resources.append(FHIRResource.from_dict(entry["resource"]))
        return resources

    def iter_resources(self):
        """Generator yielding inner entry resources as typed FHIRResource instances."""
        for entry in self.entries:
            if isinstance(entry, dict) and "resource" in entry and isinstance(entry["resource"], dict):
                yield FHIRResource.from_dict(entry["resource"])

    def get_resources_by_type(self, resource_type: str | type[FHIRResource]) -> list[FHIRResource]:
        """Filter inner resources by resource type name or class."""
        type_str = resource_type if isinstance(resource_type, str) else getattr(resource_type, "resource_type", "")
        return [r for r in self.get_resources() if r.data.get("resourceType") == type_str]

    def add_entry(
        self,
        resource: FHIRResource | dict | None = None,
        full_url: str | None = None,
        request: dict | None = None,
        response: dict | None = None,
        search: dict | None = None,
    ) -> dict:
        """Helper to append an entry to the Bundle and update total."""
        entry: dict = {}
        if full_url:
            entry["fullUrl"] = full_url
        if resource is not None:
            entry["resource"] = resource.to_dict() if isinstance(resource, FHIRResource) else dict(resource)
        if request is not None:
            entry["request"] = request
        if response is not None:
            entry["response"] = response
        if search is not None:
            entry["search"] = search

        if "entry" not in self.data or not isinstance(self.data["entry"], list):
            self.data["entry"] = []
        self.data["entry"].append(entry)

        if isinstance(self.data.get("total"), int):
            self.data["total"] = len(self.data["entry"])
        return entry


class Practitioner(FHIRResource):
    """FHIR Practitioner resource for healthcare providers."""
    __slots__ = ()
    resource_type = "Practitioner"
    array_fields = {
        "identifier", "name", "telecom", "address", "gender",
        "qualification", "communication"
    }
    VALID_GENDERS = {"male", "female", "other", "unknown"}

    def validate(self) -> list[str]:
        errors = super().validate()
        gender = self.data.get("gender")
        if gender is not None and gender not in self.VALID_GENDERS:
            errors.append(f"Invalid gender '{gender}'. Must be one of: {', '.join(sorted(self.VALID_GENDERS))}")
        active = self.data.get("active")
        if active is not None and not isinstance(active, bool):
            errors.append(f"Field 'active' must be a boolean, got {type(active).__name__}")
        return errors


class Encounter(FHIRResource):
    """FHIR Encounter resource for healthcare interactions."""
    __slots__ = ()
    resource_type = "Encounter"
    array_fields = {
        "identifier", "statusHistory", "type", "serviceType",
        "episodeOfCare", "basedOn", "participant", "appointment",
        "reasonCode", "reasonReference", "diagnosis", "account",
        "location", "serviceProvider"
    }
    VALID_STATUSES = {
        "planned", "arrived", "triaged", "in-progress", "onleave",
        "finished", "cancelled", "entered-in-error", "unknown"
    }

    def validate(self) -> list[str]:
        errors = super().validate()
        status = self.data.get("status")
        if not status:
            errors.append("Encounter requires 'status'")
        elif status not in self.VALID_STATUSES:
            errors.append(f"Invalid status '{status}'. Must be one of: {', '.join(sorted(self.VALID_STATUSES))}")
        if "class" not in self.data and "class_" not in self.data:
            errors.append("Encounter requires 'class'")
        return errors


class Condition(FHIRResource):
    """FHIR Condition resource for diagnoses, problems, and health concerns."""
    __slots__ = ()
    resource_type = "Condition"
    array_fields = {
        "identifier", "category", "bodySite", "evidence", "note", "stage"
    }

    def validate(self) -> list[str]:
        errors = super().validate()
        if "subject" not in self.data and "patient" not in self.data:
            errors.append("Condition requires 'subject' (or 'patient')")
        return errors


class MedicationRequest(FHIRResource):
    """FHIR MedicationRequest resource for prescriptions and medication orders."""
    __slots__ = ()
    resource_type = "MedicationRequest"
    array_fields = {
        "identifier", "basedOn", "priorPrescription", "category",
        "insurance", "note", "dosageInstruction", "dispenseRequest"
    }
    VALID_STATUSES = {
        "active", "on-hold", "cancelled", "completed",
        "entered-in-error", "stopped", "draft", "unknown"
    }
    VALID_INTENTS = {
        "proposal", "plan", "order", "original-order",
        "reflex-order", "filler-order", "instance-order", "option"
    }

    def validate(self) -> list[str]:
        errors = super().validate()
        status = self.data.get("status")
        if not status:
            errors.append("MedicationRequest requires 'status'")
        elif status not in self.VALID_STATUSES:
            errors.append(f"Invalid status '{status}'. Must be one of: {', '.join(sorted(self.VALID_STATUSES))}")

        intent = self.data.get("intent")
        if not intent:
            errors.append("MedicationRequest requires 'intent'")
        elif intent not in self.VALID_INTENTS:
            errors.append(f"Invalid intent '{intent}'. Must be one of: {', '.join(sorted(self.VALID_INTENTS))}")

        if "subject" not in self.data:
            errors.append("MedicationRequest requires 'subject'")
        return errors


class Medication(FHIRResource):
    """FHIR Medication resource for drug definitions and ingredients."""
    __slots__ = ()
    resource_type = "Medication"
    array_fields = {"identifier", "ingredient", "extension"}
    VALID_STATUSES = {"active", "inactive", "entered-in-error"}

    def validate(self) -> list[str]:
        errors = super().validate()
        status = self.data.get("status")
        if status is not None and status not in self.VALID_STATUSES:
            errors.append(f"Invalid status '{status}'. Must be one of: {', '.join(sorted(self.VALID_STATUSES))}")
        return errors


class OperationOutcome(FHIRResource):
    """FHIR OperationOutcome resource for operation results and error details."""
    __slots__ = ()
    resource_type = "OperationOutcome"
    array_fields = {"issue"}

    VALID_SEVERITIES = {"fatal", "error", "warning", "information"}
    VALID_CODES = {
        "invalid", "structure", "required", "value", "invariant",
        "security", "login", "unknown", "expired", "forbidden",
        "suppressed", "processing", "not-supported", "duplicate",
        "multiple-matches", "not-found", "deleted", "too-long",
        "code-invalid", "extension", "too-costly", "business-rule",
        "conflict", "transient", "lock-error", "no-store", "exception",
        "timeout", "incomplete", "throttled", "informational",
    }

    def validate(self) -> list[str]:
        errors = super().validate()
        issues = self.data.get("issue", [])
        if not issues:
            errors.append("OperationOutcome requires at least one 'issue'")
        for i, issue in enumerate(issues):
            if not isinstance(issue, dict):
                errors.append(f"issue[{i}] must be a dict")
                continue
            sev = issue.get("severity")
            if not sev:
                errors.append(f"issue[{i}] requires 'severity'")
            elif sev not in self.VALID_SEVERITIES:
                errors.append(f"issue[{i}] invalid severity '{sev}'")
            code = issue.get("code")
            if not code:
                errors.append(f"issue[{i}] requires 'code'")
            elif code not in self.VALID_CODES:
                errors.append(f"issue[{i}] invalid code '{code}'")
        return errors

    @property
    def issues(self) -> list[dict]:
        """Returns the list of issue dicts."""
        return self.data.get("issue", [])

    @property
    def severity(self) -> str | None:
        """Returns the severity of the first issue, if any."""
        issues = self.issues
        return issues[0].get("severity") if issues else None

    @property
    def is_error(self) -> bool:
        """True if any issue has severity 'fatal' or 'error'."""
        return any(i.get("severity") in ("fatal", "error") for i in self.issues)

    def first_text(self) -> str | None:
        """Returns the diagnostics text of the first issue, if any."""
        issues = self.issues
        if not issues:
            return None
        return issues[0].get("diagnostics") or issues[0].get("details", {}).get("text")


class Reference:
    """Helper for parsing, creating, and validating FHIR Reference strings and dictionaries."""
    __slots__ = ("reference", "resource_type", "id", "display")

    def __init__(
        self,
        reference: str,
        resource_type: str | None = None,
        id: str | None = None,
        display: str | None = None,
    ):
        self.reference = reference
        self.resource_type = resource_type
        self.id = id
        self.display = display

    @classmethod
    def parse(cls, reference: str | dict) -> "Reference":
        """Parse a FHIR reference string or dictionary."""
        display: str | None = None
        if isinstance(reference, dict):
            ref_str = reference.get("reference", "")
            display = reference.get("display")
        elif isinstance(reference, str):
            ref_str = reference
        else:
            raise TypeError(f"Expected str or dict for reference, got {type(reference).__name__}")

        if not ref_str:
            return cls(reference="", display=display)

        if ref_str.startswith("#"):
            return cls(reference=ref_str, id=ref_str[1:], display=display)

        clean_url = ref_str.split("?")[0].rstrip("/")
        parts = clean_url.split("/")
        if len(parts) >= 2 and parts[-2] and parts[-1]:
            return cls(
                reference=ref_str,
                resource_type=parts[-2],
                id=parts[-1],
                display=display,
            )

        return cls(reference=ref_str, display=display)

    @classmethod
    def create(
        cls,
        resource_type: str | type[FHIRResource],
        id: str,
        display: str | None = None,
    ) -> dict[str, str]:
        """Create a standard FHIR reference dictionary."""
        type_str = resource_type if isinstance(resource_type, str) else getattr(resource_type, "resource_type", str(resource_type))
        ref_dict = {"reference": f"{type_str}/{id}"}
        if display:
            ref_dict["display"] = display
        return ref_dict

    def to_dict(self) -> dict[str, str]:
        """Convert Reference instance to a FHIR Reference dict."""
        out: dict[str, str] = {"reference": self.reference}
        if self.display:
            out["display"] = self.display
        if self.resource_type:
            out["type"] = self.resource_type
        return out

    def __repr__(self) -> str:
        return f"<Reference {self.reference!r}>"
