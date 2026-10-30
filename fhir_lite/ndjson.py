import gzip
import io
import json
import os
from typing import Iterator, Iterable, IO
from .resources import FHIRResource


def iter_ndjson(source: str | os.PathLike | IO[str] | IO[bytes]) -> Iterator[FHIRResource]:
    """
    Stream and yield FHIRResource instances from an NDJSON source (file path or stream).
    Supports transparent decompression for .gz files. Consumes O(1) memory.
    """
    if isinstance(source, (str, os.PathLike)):
        file_path = str(source)
        if file_path.endswith(".gz"):
            with gzip.open(file_path, mode="rt", encoding="utf-8") as f:
                yield from _iter_stream(f)
        else:
            with open(file_path, mode="r", encoding="utf-8") as f:
                yield from _iter_stream(f)
    else:
        yield from _iter_stream(source)


def _iter_stream(stream: IO[str] | IO[bytes]) -> Iterator[FHIRResource]:
    for line in stream:
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        yield FHIRResource.from_dict(data)


def write_ndjson(
    resources: Iterable[FHIRResource | dict],
    target: str | os.PathLike | IO[str] | IO[bytes]
) -> int:
    """
    Stream and write FHIR resources as NDJSON into target (file path or stream).
    Supports transparent gzip compression if target path ends with .gz.
    Returns the count of written resources.
    """
    if isinstance(target, (str, os.PathLike)):
        file_path = str(target)
        if file_path.endswith(".gz"):
            with gzip.open(file_path, mode="wt", encoding="utf-8") as f:
                return _write_stream(resources, f)
        else:
            with open(file_path, mode="w", encoding="utf-8") as f:
                return _write_stream(resources, f)
    else:
        return _write_stream(resources, target)


def _write_stream(resources: Iterable[FHIRResource | dict], stream: IO[str] | IO[bytes]) -> int:
    count = 0
    is_bytes_stream = hasattr(stream, "write") and isinstance(stream, (io.RawIOBase, io.BufferedIOBase))
    for res in resources:
        data = res.to_dict() if isinstance(res, FHIRResource) else res
        line = json.dumps(data, separators=(",", ":"), ensure_ascii=False) + "\n"
        if is_bytes_stream:
            stream.write(line.encode("utf-8"))
        else:
            stream.write(line)
        count += 1
    return count


def loads_ndjson(ndjson_str: str) -> list[FHIRResource]:
    """Parse an in-memory NDJSON string into a list of FHIRResource instances."""
    return list(_iter_stream(io.StringIO(ndjson_str)))


def dumps_ndjson(resources: Iterable[FHIRResource | dict]) -> str:
    """Serialize an iterable of FHIR resources into an in-memory NDJSON string."""
    buf = io.StringIO()
    _write_stream(resources, buf)
    return buf.getvalue()
