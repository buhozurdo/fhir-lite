"""Tests for TASK-005: Built-in Command-Line Interface (CLI).
"""

import json
import os
import tempfile
from fhir_lite.cli import main


def test_cli_help_and_version(capsys):
    # No args -> exit code 1
    code = main([])
    assert code == 1


def test_cli_convert_json_to_xml():
    patient_json = json.dumps({
        "resourceType": "Patient",
        "id": "cli-pat-1",
        "active": True,
        "gender": "female",
    })

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as in_f:
        in_f.write(patient_json)
        in_path = in_f.name

    with tempfile.NamedTemporaryFile("r+", delete=False, suffix=".xml") as out_f:
        out_path = out_f.name

    try:
        # 1. Convert with auto-detection via extensions
        code = main(["convert", in_path, "-o", out_path])
        assert code == 0

        with open(out_path, "r", encoding="utf-8") as f:
            xml_content = f.read()
        assert "<Patient" in xml_content
        assert 'gender value="female"' in xml_content

        # 2. Convert with explicit --to xml
        code2 = main(["convert", in_path, "-o", out_path, "--to", "xml"])
        assert code2 == 0
    finally:
        os.unlink(in_path)
        os.unlink(out_path)


def test_cli_convert_xml_to_json():
    patient_xml = '<Patient xmlns="http://hl7.org/fhir"><id value="cli-pat-2"/><gender value="male"/></Patient>'

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".xml") as in_f:
        in_f.write(patient_xml)
        in_path = in_f.name

    with tempfile.NamedTemporaryFile("r+", delete=False, suffix=".json") as out_f:
        out_path = out_f.name

    try:
        code = main(["convert", in_path, "-o", out_path])
        assert code == 0

        with open(out_path, "r", encoding="utf-8") as f:
            json_content = json.load(f)
        assert json_content.get("resourceType") == "Patient"
        assert json_content.get("id") == "cli-pat-2"
        assert json_content.get("gender") == "male"
    finally:
        os.unlink(in_path)
        os.unlink(out_path)


def test_cli_validate_success(capsys):
    valid_patient = json.dumps({
        "resourceType": "Patient",
        "id": "valid-pat",
        "gender": "other",
        "active": True,
    })

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as in_f:
        in_f.write(valid_patient)
        in_path = in_f.name

    try:
        code = main(["validate", in_path])
        captured = capsys.readouterr()
        assert code == 0
        assert "[OK]" in captured.out
    finally:
        os.unlink(in_path)


def test_cli_validate_failure(capsys):
    # Observation requires status and code
    invalid_obs = json.dumps({
        "resourceType": "Observation",
        "id": "bad-obs",
    })

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as in_f:
        in_f.write(invalid_obs)
        in_path = in_f.name

    try:
        code = main(["validate", in_path])
        captured = capsys.readouterr()
        assert code == 1
        assert "[FAIL]" in captured.err
    finally:
        os.unlink(in_path)


def test_cli_fhirpath(capsys):
    patient = json.dumps({
        "resourceType": "Patient",
        "id": "fp-pat",
        "name": [
            {"use": "official", "family": "Curie", "given": ["Marie"]},
            {"use": "maiden", "family": "Sklodowska"},
        ],
    })

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as in_f:
        in_f.write(patient)
        in_path = in_f.name

    try:
        capsys.readouterr()

        # 1. JSON format evaluation
        code = main(["fhirpath", "name.where(use = 'official').family", in_path])
        captured = capsys.readouterr()
        assert code == 0
        parsed = json.loads(captured.out.strip())
        assert parsed == ["Curie"]

        # 2. Text format with --first
        code2 = main(["fhirpath", "name.first().family", in_path, "--first", "-f", "text"])
        captured2 = capsys.readouterr()
        assert code2 == 0
        assert captured2.out.strip() == "Curie"
    finally:
        os.unlink(in_path)


def test_cli_errors(capsys):
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as in_f:
        in_path = in_f.name

    try:
        code = main(["convert", in_path])
        assert code == 1

        code_val = main(["validate", in_path])
        assert code_val == 1

        code_fp = main(["fhirpath", "name.family", in_path])
        assert code_fp == 1
    finally:
        os.unlink(in_path)

    # Malformed JSON validate
    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as in_f:
        in_f.write("{not valid json")
        bad_path = in_f.name
    try:
        code_bad = main(["validate", bad_path])
        assert code_bad == 1
    finally:
        os.unlink(bad_path)


def test_cli_piping_stdin_stdout(monkeypatch, capsys):
    import io
    sample_json = '{"resourceType": "Patient", "id": "stdin-1", "gender": "male"}'
    monkeypatch.setattr("sys.stdin", io.StringIO(sample_json))

    code = main(["convert", "--to", "xml"])
    captured = capsys.readouterr()
    assert code == 0
    assert "<Patient" in captured.out
    assert 'gender value="male"' in captured.out

    # Stdin into validate
    monkeypatch.setattr("sys.stdin", io.StringIO(sample_json))
    code_val = main(["validate"])
    captured_val = capsys.readouterr()
    assert code_val == 0
    assert "[OK]" in captured_val.out
