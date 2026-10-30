import json
import xml.etree.ElementTree as ET

FHIR_NS = "http://hl7.org/fhir"
ET.register_namespace("", FHIR_NS)

COMMON_ARRAY_FIELDS = {
    "identifier", "name", "telecom", "address", "contact",
    "generalPractitioner", "given", "prefix", "suffix", "line",
    "coding", "extension", "modifierExtension", "category",
    "performer", "interpretation", "note", "bodySite",
    "referenceRange", "hasMember", "derivedFrom", "component",
    "basedOn", "partOf", "focus", "subject", "result", "entry",
    "issue", "link", "item", "contained"
}


def xml_to_dict(elem: ET.Element, array_fields: set | None = None) -> dict | list | str | bool | int | float:
    arrays = COMMON_ARRAY_FIELDS if array_fields is None else (COMMON_ARRAY_FIELDS | array_fields)
    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

    if tag == "div":
        return ET.tostring(elem, encoding="unicode").strip()

    if "value" in elem.attrib and len(elem) == 0:
        val = elem.attrib["value"]
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

    res = {}
    for child in elem:
        child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if child_tag in ("resource", "contained") and len(child) == 1:
            inner = child[0]
            inner_tag = inner.tag.split("}")[-1] if "}" in inner.tag else inner.tag
            inner_val = xml_to_dict(inner, array_fields=arrays)
            if isinstance(inner_val, dict):
                inner_val["resourceType"] = inner_tag
            child_val = inner_val
        else:
            child_val = xml_to_dict(child, array_fields=arrays)

        if child_tag in res:
            if not isinstance(res[child_tag], list):
                res[child_tag] = [res[child_tag]]
            res[child_tag].append(child_val)
        else:
            if child_tag in arrays:
                res[child_tag] = [child_val]
            else:
                res[child_tag] = child_val

    return res


def dict_to_xml(data: dict, root_tag: str | None = None) -> ET.Element:
    resource_type = root_tag or data.get("resourceType", "Resource")
    root = ET.Element(f"{{{FHIR_NS}}}{resource_type}")

    def _build(parent: ET.Element, key: str, value):
        if key == "resourceType":
            return

        if isinstance(value, list):
            for item in value:
                _build(parent, key, item)
        elif isinstance(value, dict):
            node = ET.SubElement(parent, f"{{{FHIR_NS}}}{key}")
            if key in ("resource", "contained") and "resourceType" in value:
                res_type = value["resourceType"]
                res_node = ET.SubElement(node, f"{{{FHIR_NS}}}{res_type}")
                for sub_k, sub_v in value.items():
                    _build(res_node, sub_k, sub_v)
            else:
                for sub_k, sub_v in value.items():
                    _build(node, sub_k, sub_v)
        else:
            if key == "div" and isinstance(value, str) and value.strip().startswith("<div"):
                try:
                    div_elem = ET.fromstring(value)
                    parent.append(div_elem)
                    return
                except ET.ParseError:
                    pass
            node = ET.SubElement(parent, f"{{{FHIR_NS}}}{key}")
            if isinstance(value, bool):
                node.set("value", "true" if value else "false")
            else:
                node.set("value", str(value))

    for k, v in data.items():
        _build(root, k, v)

    return root


def json_to_xml(json_str: str, pretty: bool = True) -> str:
    data = json.loads(json_str)
    root = dict_to_xml(data)
    if pretty:
        ET.indent(root)
    return ET.tostring(root, encoding="unicode")


def xml_to_json(xml_str: str, indent: int = 2, array_fields: set | None = None) -> str:
    root = ET.fromstring(xml_str)
    resource_type = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    data = xml_to_dict(root, array_fields=array_fields)
    if isinstance(data, dict):
        data["resourceType"] = resource_type
    return json.dumps(data, indent=indent, ensure_ascii=False)
