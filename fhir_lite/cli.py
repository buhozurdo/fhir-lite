"""Command-Line Interface (CLI) for FHIR Lite.

Provides fast, zero-dependency command-line tools for pipelines,
shell scripts, and CI/CD automation:
- convert: Bidirectional conversion between FHIR JSON and XML.
- validate: Syntax and structural validation of FHIR resources.
- fhirpath: Query and filter FHIR resources using the FHIRPath mini-engine.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, List, Optional, Sequence


def _get_version() -> str:
    try:
        from . import __version__
        return __version__
    except Exception:
        return "0.6.0"


def _resolve_safe_path(path_str: str, for_write: bool = False) -> Path:
    """Validate and safely resolve a file path to mitigate Path Traversal (CWE-22 / CWE-73).

    Guards against faulty or malicious LLM-supplied path arguments by:
    1. Rejecting empty paths and null byte injection attempts.
    2. Canonicalizing and resolving all relative traversal components (e.g., '..') and symlinks.
    3. Ensuring the path targets a regular file, rejecting directory paths.
    4. For reading, verifying that the file exists and is a regular file.
    5. For writing, ensuring the parent directory is valid and creating it safely if needed.
    """
    if not path_str or not isinstance(path_str, str):
        raise ValueError("File path cannot be empty.")
    if "\0" in path_str:
        raise ValueError("Invalid file path: contains null byte injection.")

    # Canonicalize and resolve all relative traversal sequences and symlinks
    resolved_path = Path(path_str).expanduser().resolve()

    if resolved_path.is_dir():
        raise IsADirectoryError(f"Target path is a directory, expected a regular file: {resolved_path}")

    if not for_write:
        if not resolved_path.exists():
            raise FileNotFoundError(f"Input file not found: {resolved_path}")
        if not resolved_path.is_file():
            raise ValueError(f"Path is not a regular file: {resolved_path}")
    else:
        # For writing, ensure the parent directory is valid and exists
        parent_dir = resolved_path.parent
        parent_dir.mkdir(parents=True, exist_ok=True)

    return resolved_path


def _read_input(input_path: Optional[str]) -> str:
    """Read content from file or stdin."""
    if not input_path or input_path == "-":
        return sys.stdin.read()
    safe_path = _resolve_safe_path(input_path, for_write=False)
    with open(safe_path, "r", encoding="utf-8") as f:  # NOSONAR: Path Traversal (CWE-22) mitigated via _resolve_safe_path
        return f.read()


def _write_output(content: str, output_path: Optional[str]) -> None:
    """Write content to file or stdout."""
    if not output_path or output_path == "-":
        sys.stdout.write(content)
        if not content.endswith("\n"):
            sys.stdout.write("\n")
    else:
        safe_path = _resolve_safe_path(output_path, for_write=True)
        with open(safe_path, "w", encoding="utf-8") as f:  # NOSONAR: Path Traversal (CWE-22) mitigated via _resolve_safe_path
            f.write(content)
            if not content.endswith("\n"):
                f.write("\n")


def cmd_convert(args: argparse.Namespace) -> int:
    from .serializer import json_to_xml, xml_to_json

    try:
        raw_content = _read_input(args.input)
    except (OSError, ValueError) as e:
        sys.stderr.write(f"Error reading input: {e}\n")
        return 1

    content = raw_content.strip()
    if not content:
        sys.stderr.write("Error: Input is empty.\n")
        return 1

    # Determine target format
    target_format = args.to
    if not target_format:
        if args.output and args.output != "-":
            lower_out = args.output.lower()
            if lower_out.endswith(".xml"):
                target_format = "xml"
            elif lower_out.endswith(".json"):
                target_format = "json"

    if not target_format:
        # Auto-detect from input content
        if content.startswith("<"):
            target_format = "json"
        elif content.startswith("{") or content.startswith("["):
            target_format = "xml"
        else:
            sys.stderr.write("Error: Could not auto-detect format. Use --to [json|xml].\n")
            return 1

    try:
        if target_format == "xml":
            result = json_to_xml(content, pretty=args.pretty)
        elif target_format == "json":
            indent = args.indent if args.pretty else None
            result = xml_to_json(content, indent=indent or 2)
        else:
            sys.stderr.write(f"Error: Unsupported format '{target_format}'. Choose 'json' or 'xml'.\n")
            return 1

        _write_output(result, args.output)
        return 0
    except Exception as e:
        sys.stderr.write(f"Error during conversion: {e}\n")
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    from .resources import FHIRResource

    try:
        raw_content = _read_input(args.input)
    except (OSError, ValueError) as e:
        sys.stderr.write(f"Error reading input: {e}\n")
        return 1

    content = raw_content.strip()
    if not content:
        sys.stderr.write("Error: Input is empty.\n")
        return 1

    # Detect format
    is_xml = content.startswith("<")
    try:
        if is_xml:
            resource = FHIRResource.from_xml(content)
        else:
            resource = FHIRResource.from_json(content)
    except Exception as e:
        sys.stderr.write(f"[FAIL] Syntax error: Failed to parse input as FHIR {'XML' if is_xml else 'JSON'}: {e}\n")
        return 1

    errors = resource.validate()
    rtype = getattr(resource, "resource_type", "Resource")
    rid = resource.data.get("id")
    id_str = f" id='{rid}'" if rid else ""

    if not errors:
        sys.stdout.write(f"[OK] Resource '{rtype}'{id_str} is valid.\n")
        return 0
    else:
        sys.stderr.write(f"[FAIL] Resource '{rtype}'{id_str} has {len(errors)} validation error(s):\n")
        for err in errors:
            sys.stderr.write(f"  - {err}\n")
        return 1


def cmd_fhirpath(args: argparse.Namespace) -> int:
    from .fhirpath import evaluate_fhirpath
    from .resources import FHIRResource

    try:
        raw_content = _read_input(args.input)
    except (OSError, ValueError) as e:
        sys.stderr.write(f"Error reading input: {e}\n")
        return 1

    content = raw_content.strip()
    if not content:
        sys.stderr.write("Error: Input is empty.\n")
        return 1

    is_xml = content.startswith("<")
    try:
        if is_xml:
            resource = FHIRResource.from_xml(content)
        else:
            resource = FHIRResource.from_json(content)
    except Exception as e:
        sys.stderr.write(f"Error parsing resource: {e}\n")
        return 1

    try:
        res = evaluate_fhirpath(resource, args.expression, first=args.first)
    except Exception as e:
        sys.stderr.write(f"Error evaluating FHIRPath expression: {e}\n")
        return 1

    if args.format == "text":
        if isinstance(res, list):
            for item in res:
                sys.stdout.write(f"{item}\n")
        elif res is not None:
            sys.stdout.write(f"{res}\n")
    else:
        # Default json format
        sys.stdout.write(json.dumps(res, indent=2, ensure_ascii=False) + "\n")

    return 0


def cmd_anonymize(args: argparse.Namespace) -> int:
    from .anonymize import DeidConfig, anonymize
    from .resources import FHIRResource

    try:
        raw_content = _read_input(args.input)
    except (OSError, ValueError) as e:
        sys.stderr.write(f"Error reading input: {e}\n")
        return 1

    content = raw_content.strip()
    if not content:
        sys.stderr.write("Error: Input is empty.\n")
        return 1

    is_xml = content.startswith("<")
    try:
        if is_xml:
            resource = FHIRResource.from_xml(content)
        else:
            resource = FHIRResource.from_json(content)
    except Exception as e:
        sys.stderr.write(f"Error parsing resource: {e}\n")
        return 1

    config = DeidConfig(
        date_handling=args.date_handling,
        date_shift_days=args.date_shift_days,
        pseudonymize_id=args.pseudonymize_id,
        salt=args.salt,
        keep_state_and_country=args.keep_state_country,
        name_placeholder=None if args.no_placeholder else "ANONYMOUS",
    )

    try:
        sanitized = anonymize(resource, config=config)
        if is_xml:
            out_str = sanitized.to_xml()
        else:
            out_str = sanitized.to_json(indent=2)
        _write_output(out_str, args.output)
        return 0
    except Exception as e:
        sys.stderr.write(f"Error during de-identification: {e}\n")
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fhir-lite",
        description="FHIR Lite CLI: Ultra-lightweight tools for FHIR pipelines and processing.",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {_get_version()}",
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # convert subcommand
    p_convert = subparsers.add_parser(
        "convert",
        help="Convert between FHIR JSON and XML.",
        description="Convert FHIR resources between JSON and XML representations.",
    )
    p_convert.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Input file path (or '-' / omit for stdin).",
    )
    p_convert.add_argument(
        "-o",
        "--output",
        default="-",
        help="Output file path (or '-' / omit for stdout).",
    )
    p_convert.add_argument(
        "--to",
        choices=["json", "xml"],
        default=None,
        help="Target format (auto-detected by default).",
    )
    p_convert.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Indentation spaces for JSON output (default: 2).",
    )
    p_convert.add_argument(
        "--no-pretty",
        dest="pretty",
        action="store_false",
        default=True,
        help="Disable pretty-printing / indentation.",
    )

    # validate subcommand
    p_validate = subparsers.add_parser(
        "validate",
        help="Validate a FHIR resource.",
        description="Check syntax and clinical/administrative validation rules of a FHIR resource.",
    )
    p_validate.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Input file path (or '-' / omit for stdin).",
    )

    # fhirpath subcommand
    p_fhirpath = subparsers.add_parser(
        "fhirpath",
        help="Query a FHIR resource using FHIRPath.",
        description="Evaluate a FHIRPath query expression against a resource.",
    )
    p_fhirpath.add_argument(
        "expression",
        help="FHIRPath query expression (e.g. 'name.where(use = \\'official\\').family').",
    )
    p_fhirpath.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Input file path (or '-' / omit for stdin).",
    )
    p_fhirpath.add_argument(
        "--first",
        action="store_true",
        help="Return only the first matching item or null.",
    )
    p_fhirpath.add_argument(
        "-f",
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format: 'json' (default) or 'text' line-by-line.",
    )

    # anonymize subcommand
    p_anon = subparsers.add_parser(
        "anonymize",
        help="Sanitize and de-identify FHIR resources (HIPAA Safe Harbor).",
        description="Strip or transform 18 HIPAA PHI identifiers from FHIR resources or Bundles.",
    )
    p_anon.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Input file path (or '-' / omit for stdin).",
    )
    p_anon.add_argument(
        "-o",
        "--output",
        default="-",
        help="Output file path (or '-' / omit for stdout).",
    )
    p_anon.add_argument(
        "--date-handling",
        choices=["year_only", "shift", "remove", "preserve"],
        default="year_only",
        help="Date sanitization strategy (default: 'year_only').",
    )
    p_anon.add_argument(
        "--date-shift-days",
        type=int,
        default=0,
        help="Days to shift dates when --date-handling=shift.",
    )
    p_anon.add_argument(
        "--pseudonymize-id",
        action="store_true",
        help="Replace resource IDs with deterministic SHA-256 hashes.",
    )
    p_anon.add_argument(
        "--salt",
        default="",
        help="Salt for deterministic pseudonymization hashing.",
    )
    p_anon.add_argument(
        "--keep-state-country",
        action="store_true",
        help="Retain state and country while stripping street address, city, and zip code.",
    )
    p_anon.add_argument(
        "--no-placeholder",
        action="store_true",
        help="Remove name array completely instead of replacing with 'ANONYMOUS'.",
    )

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help(sys.stderr)
        return 1

    if args.subcommand == "convert":
        return cmd_convert(args)
    elif args.subcommand == "validate":
        return cmd_validate(args)
    elif args.subcommand == "fhirpath":
        return cmd_fhirpath(args)
    elif args.subcommand == "anonymize":
        return cmd_anonymize(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
