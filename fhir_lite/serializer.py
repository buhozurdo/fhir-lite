import json
import re
import xml.etree.ElementTree as ET

FHIR_NS = "http://hl7.org/fhir"
ET.register_namespace("", FHIR_NS)

_FORBIDDEN_DTD_RE = re.compile(r"<!(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)


def safe_fromstring(xml_str: str) -> ET.Element:
    """Safely parse XML string, rejecting DTD and entity declarations (XXE / DoS protection)."""
    if _FORBIDDEN_DTD_RE.search(xml_str):
        raise ValueError("Invalid FHIR XML: DTD and entity declarations are forbidden for security.")
    try:
        return ET.fromstring(xml_str)
    except ET.ParseError as err:
        raise ValueError(f"Malformed XML: {err}") from err


COMMON_ARRAY_FIELDS = {
    "identifier", "name", "telecom", "address", "contact",
    "generalPractitioner", "given", "prefix", "suffix", "line",
    "coding", "extension", "modifierExtension", "category",
    "performer", "interpretation", "note", "bodySite",
    "referenceRange", "hasMember", "derivedFrom", "component",
    "basedOn", "partOf", "entry", "issue", "link", "item", "contained"
}


def _parse_primitive(val: str, tag: str) -> bool | int | float | str:
    if val == "true":
        return True
    if val == "false":
        return False
    if tag.endswith(("Integer", "PositiveInt", "UnsignedInt")):
        try:
            return int(val)
        except ValueError:
            pass
    elif tag.endswith("Decimal"):
        try:
            return float(val)
        except ValueError:
            pass
    return val


def _add_to_res(target: dict, key: str, val, arrays: set):
    if key in target:
        if not isinstance(target[key], list):
            target[key] = [target[key]]
        target[key].append(val)
    else:
        if key in arrays:
            target[key] = [val]
        else:
            target[key] = val


def xml_to_dict(elem: ET.Element, array_fields: set | None = None) -> dict | list | str | bool | int | float:
    arrays = COMMON_ARRAY_FIELDS if array_fields is None else (COMMON_ARRAY_FIELDS | array_fields)
    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

    if tag == "div":
        return ET.tostring(elem, encoding="unicode").strip()

    if "value" in elem.attrib and len(elem) == 0:
        return _parse_primitive(elem.attrib["value"], tag)

    res = {}
    for attr_k, attr_v in elem.attrib.items():
        if attr_k != "value":
            res[attr_k] = attr_v

    for child in elem:
        child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if child_tag in ("resource", "contained") and len(child) == 1:
            inner = child[0]
            inner_tag = inner.tag.split("}")[-1] if "}" in inner.tag else inner.tag
            inner_val = xml_to_dict(inner, array_fields=arrays)
            if isinstance(inner_val, dict):
                inner_val["resourceType"] = inner_tag
            _add_to_res(res, child_tag, inner_val, arrays)
        elif "value" in child.attrib and len(child) > 0:
            val = _parse_primitive(child.attrib["value"], child_tag)
            ext_val = xml_to_dict(child, array_fields=arrays)
            _add_to_res(res, child_tag, val, arrays)
            _add_to_res(res, f"_{child_tag}", ext_val, arrays)
        else:
            child_val = xml_to_dict(child, array_fields=arrays)
            _add_to_res(res, child_tag, child_val, arrays)

    return res


def dict_to_xml(data: dict, root_tag: str | None = None) -> ET.Element:
    resource_type = root_tag or data.get("resourceType", "Resource")
    root = ET.Element(f"{{{FHIR_NS}}}{resource_type}")

    def _build(parent: ET.Element, key: str, value, ext=None):
        if key == "resourceType":
            return

        if key.startswith("_"):
            base_key = key[1:]
            if base_key not in data:
                node = ET.SubElement(parent, f"{{{FHIR_NS}}}{base_key}")
                if isinstance(value, dict):
                    for sub_k, sub_v in value.items():
                        _build(node, sub_k, sub_v)
            return

        if isinstance(value, list):
            for i, item in enumerate(value):
                item_ext = ext[i] if (isinstance(ext, list) and i < len(ext)) else None
                _build(parent, key, item, item_ext)
        elif isinstance(value, dict):
            node = ET.SubElement(parent, f"{{{FHIR_NS}}}{key}")
            if "url" in value and key in ("extension", "modifierExtension"):
                node.set("url", str(value["url"]))

            if key in ("resource", "contained") and "resourceType" in value:
                res_type = value["resourceType"]
                res_node = ET.SubElement(node, f"{{{FHIR_NS}}}{res_type}")
                for sub_k, sub_v in value.items():
                    _build(res_node, sub_k, sub_v)
            else:
                for sub_k, sub_v in value.items():
                    if sub_k == "url" and key in ("extension", "modifierExtension"):
                        continue
                    if sub_k.startswith("_") and sub_k[1:] in value:
                        continue
                    sub_ext = value.get(f"_{sub_k}")
                    _build(node, sub_k, sub_v, sub_ext)
                for sub_k, sub_v in value.items():
                    if sub_k.startswith("_") and sub_k[1:] not in value:
                        _build(node, sub_k, sub_v)
        else:
            if key == "div" and isinstance(value, str) and value.strip().startswith("<div"):
                try:
                    div_elem = safe_fromstring(value)
                    parent.append(div_elem)
                    return
                except (ET.ParseError, ValueError):
                    pass
            node = ET.SubElement(parent, f"{{{FHIR_NS}}}{key}")
            if isinstance(value, bool):
                node.set("value", "true" if value else "false")
            else:
                node.set("value", str(value))
            if isinstance(ext, dict):
                for ext_k, ext_v in ext.items():
                    _build(node, ext_k, ext_v)

    for k, v in data.items():
        if k.startswith("_") and k[1:] in data:
            continue
        ext = data.get(f"_{k}")
        _build(root, k, v, ext)

    return root


def json_to_xml(json_str: str, pretty: bool = True) -> str:
    data = json.loads(json_str)
    root = dict_to_xml(data)
    if pretty:
        ET.indent(root)
    return ET.tostring(root, encoding="unicode")


def xml_to_json(xml_str: str, indent: int = 2, array_fields: set | None = None) -> str:
    root = safe_fromstring(xml_str)
    resource_type = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    data = xml_to_dict(root, array_fields=array_fields)
    if isinstance(data, dict):
        data["resourceType"] = resource_type
    return json.dumps(data, indent=indent, ensure_ascii=False)
