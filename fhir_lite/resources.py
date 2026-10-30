import json
import xml.etree.ElementTree as ET
from .serializer import dict_to_xml, xml_to_dict, safe_fromstring, COMMON_ARRAY_FIELDS



class FHIRResource:
    """Base FHIR resource class with dictionary-like access and bidirectional serialization."""
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
        if name in ("data",):
            super().__setattr__(name, value)
        elif hasattr(self, "data") and name in self.data:
            self.data[name] = value
        else:
            super().__setattr__(name, value)

    def __repr__(self) -> str:
        res_id = self.data.get("id")
        return f"<{self.__class__.__name__} id={res_id!r}>"


class Patient(FHIRResource):
    """FHIR Patient resource."""
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
    resource_type = "Medication"
    array_fields = {"identifier", "ingredient", "extension"}
    VALID_STATUSES = {"active", "inactive", "entered-in-error"}

    def validate(self) -> list[str]:
        errors = super().validate()
        status = self.data.get("status")
        if status is not None and status not in self.VALID_STATUSES:
            errors.append(f"Invalid status '{status}'. Must be one of: {', '.join(sorted(self.VALID_STATUSES))}")
        return errors



