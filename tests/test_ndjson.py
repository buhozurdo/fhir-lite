import io
import os
import tempfile
from fhir_lite import (
    Patient,
    Observation,
    Encounter,
    iter_ndjson,
    iter_ndjson_raw,
    write_ndjson,
    loads_ndjson,
    iter_loads_ndjson,
    iter_loads_ndjson_raw,
    dumps_ndjson,
    iter_dumps_ndjson,
)


def test_ndjson_streaming():
    # 1. In-memory dumps and loads
    resources = [
        Patient(id="pat-ndjson-1", gender="male", active=True),
        Observation(id="obs-ndjson-1", status="final", code={"text": "Weight"}),
        Encounter(id="enc-ndjson-1", status="finished", class_={"code": "IMP"}),
    ]

    ndjson_str = dumps_ndjson(resources)
    lines = [line for line in ndjson_str.split("\n") if line.strip()]
    assert len(lines) == 3
    # Verify each line is valid JSON without indentation
    assert "\n" not in lines[0]
    assert '"resourceType":"Patient"' in lines[0] or '"resourceType": "Patient"' in lines[0]

    loaded = loads_ndjson(ndjson_str)
    assert len(loaded) == 3
    assert isinstance(loaded[0], Patient)
    assert isinstance(loaded[1], Observation)
    assert isinstance(loaded[2], Encounter)
    assert loaded[0].id == "pat-ndjson-1"
    assert loaded[1].status == "final"
    assert loaded[2].status == "finished"

    # 2. Streaming via StringIO (O(1) memory generator)
    stream = io.StringIO(ndjson_str)
    gen = iter_ndjson(stream)
    first = next(gen)
    assert isinstance(first, Patient)
    assert first.id == "pat-ndjson-1"

    second = next(gen)
    assert isinstance(second, Observation)

    third = next(gen)
    assert isinstance(third, Encounter)

    # 3. File streaming and transparent Gzip (.ndjson.gz)
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Standard .ndjson file
        plain_path = os.path.join(tmp_dir, "patients.ndjson")
        written_count = write_ndjson(resources, plain_path)
        assert written_count == 3
        assert os.path.exists(plain_path)

        streamed_plain = list(iter_ndjson(plain_path))
        assert len(streamed_plain) == 3
        assert isinstance(streamed_plain[0], Patient)

        # Gzipped .ndjson.gz file
        gz_path = os.path.join(tmp_dir, "patients.ndjson.gz")
        written_gz_count = write_ndjson(resources, gz_path)
        assert written_gz_count == 3
        assert os.path.exists(gz_path)
        # Gzip file must be binary and not plain text
        with open(gz_path, "rb") as gf:
            magic = gf.read(2)
            assert magic == b"\x1f\x8b", "Expected gzip magic bytes"

        # Read back transparently with iter_ndjson
        streamed_gz = list(iter_ndjson(gz_path))
        assert len(streamed_gz) == 3
        assert isinstance(streamed_gz[0], Patient)
        assert isinstance(streamed_gz[1], Observation)
        assert streamed_gz[0].gender == "male"

        # Raw streaming without class overhead
        streamed_raw = list(iter_ndjson_raw(plain_path))
        assert len(streamed_raw) == 3
        assert isinstance(streamed_raw[0], dict)
        assert streamed_raw[0]["id"] == "pat-ndjson-1"

        # Raw streaming from gzip
        streamed_raw_gz = list(iter_ndjson_raw(gz_path))
        assert len(streamed_raw_gz) == 3
        assert isinstance(streamed_raw_gz[0], dict)

    # 4. Lazy in-memory streaming (string and bytes)
    lazy_items = list(iter_loads_ndjson(ndjson_str))
    assert len(lazy_items) == 3
    assert isinstance(lazy_items[0], Patient)

    lazy_bytes = list(iter_loads_ndjson(ndjson_str.encode("utf-8")))
    assert len(lazy_bytes) == 3

    lazy_raw = list(iter_loads_ndjson_raw(ndjson_str))
    assert len(lazy_raw) == 3
    assert isinstance(lazy_raw[0], dict)

    lazy_raw_bytes = list(iter_loads_ndjson_raw(ndjson_str.encode("utf-8")))
    assert len(lazy_raw_bytes) == 3

    # 5. Lazy dumps streaming
    dumped_lines = list(iter_dumps_ndjson(resources))
    assert len(dumped_lines) == 3
    assert dumped_lines[0].endswith("\n")

    print("All NDJSON Bulk Data streaming tests passed successfully!")


if __name__ == "__main__":
    test_ndjson_streaming()
