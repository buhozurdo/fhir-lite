import gzip
import io
import json
import os
from typing import Any, Iterable, Iterator, IO
from .resources import FHIRResource

IO_BUFFER_SIZE = 65536  # 64KB bounded I/O buffer for high-throughput streaming

# Detect optional high-performance C deserializers/serializers (orjson/ujson)
try:
    import orjson  # type: ignore

    def _fast_loads(data: str | bytes) -> dict:
        return orjson.loads(data)

    def _fast_dumps(data: Any) -> str:
        return orjson.dumps(data).decode("utf-8")

    HAS_ORJSON = True
except ImportError:
    try:
        import ujson  # type: ignore

        def _fast_loads(data: str | bytes) -> dict:
            return ujson.loads(data)

        def _fast_dumps(data: Any) -> str:
            return ujson.dumps(data, ensure_ascii=False)

        HAS_ORJSON = False
    except ImportError:
        def _fast_loads(data: str | bytes) -> dict:
            return json.loads(data)

        def _fast_dumps(data: Any) -> str:
            return json.dumps(data, separators=(",", ":"), ensure_ascii=False)

        HAS_ORJSON = False


def iter_ndjson(source: str | os.PathLike | IO[str] | IO[bytes]) -> Iterator[FHIRResource]:
    """
    Stream and yield FHIRResource instances from an NDJSON source (file path or stream).
    Supports transparent decompression for .gz files. Consumes O(1) memory with bounded 64KB buffering.
    """
    if isinstance(source, (str, os.PathLike)):
        file_path = str(source)
        if file_path.endswith(".gz"):
            with gzip.open(file_path, mode="rt", encoding="utf-8") as f:
                yield from _iter_stream(f)
        else:
            with open(file_path, mode="r", encoding="utf-8", buffering=IO_BUFFER_SIZE) as f:
                yield from _iter_stream(f)
    else:
        yield from _iter_stream(source)


def iter_ndjson_raw(source: str | os.PathLike | IO[str] | IO[bytes]) -> Iterator[dict]:
    """
    Stream and yield raw dicts from an NDJSON source without class wrapping overhead.
    Optimal for high-throughput ETL / bulk data ingestion (Epic / Flatiron FHIR exports).
    """
    if isinstance(source, (str, os.PathLike)):
        file_path = str(source)
        if file_path.endswith(".gz"):
            with gzip.open(file_path, mode="rt", encoding="utf-8") as f:
                yield from _iter_stream_raw(f)
        else:
            with open(file_path, mode="r", encoding="utf-8", buffering=IO_BUFFER_SIZE) as f:
                yield from _iter_stream_raw(f)
    else:
        yield from _iter_stream_raw(source)


def _iter_stream_raw(stream: IO[str] | IO[bytes]) -> Iterator[dict]:
    for line in stream:
        if isinstance(line, bytes):
            if HAS_ORJSON:
                line_stripped = line.strip()
                if line_stripped:
                    yield _fast_loads(line_stripped)
                continue
            line = line.decode("utf-8")
        line = line.strip()
        if not line:
            continue
        yield _fast_loads(line)


def _iter_stream(stream: IO[str] | IO[bytes]) -> Iterator[FHIRResource]:
    for raw in _iter_stream_raw(stream):
        yield FHIRResource.from_dict(raw)


def write_ndjson(
    resources: Iterable[FHIRResource | dict],
    target: str | os.PathLike | IO[str] | IO[bytes]
) -> int:
    """
    Stream and write FHIR resources as NDJSON into target (file path or stream).
    Supports transparent gzip compression if target path ends with .gz.
    Uses bounded 64KB buffering to minimize system calls.
    Returns the count of written resources.
    """
    if isinstance(target, (str, os.PathLike)):
        file_path = str(target)
        if file_path.endswith(".gz"):
            with gzip.open(file_path, mode="wt", encoding="utf-8") as f:
                return _write_stream(resources, f)
        else:
            with open(file_path, mode="w", encoding="utf-8", buffering=IO_BUFFER_SIZE) as f:
                return _write_stream(resources, f)
    else:
        return _write_stream(resources, target)


def _write_stream(resources: Iterable[FHIRResource | dict], stream: IO[str] | IO[bytes], chunk_size: int = 128) -> int:
    count = 0
    is_bytes_stream = hasattr(stream, "write") and isinstance(stream, (io.RawIOBase, io.BufferedIOBase))
    buf: list[str] = []

    for res in resources:
        data = res.to_dict() if isinstance(res, FHIRResource) else res
        line = _fast_dumps(data) + "\n"
        buf.append(line)
        count += 1
        if len(buf) >= chunk_size:
            chunk = "".join(buf)
            if is_bytes_stream:
                stream.write(chunk.encode("utf-8"))
            else:
                stream.write(chunk)
            buf.clear()

    if buf:
        chunk = "".join(buf)
        if is_bytes_stream:
            stream.write(chunk.encode("utf-8"))
        else:
            stream.write(chunk)
        buf.clear()

    return count


def iter_loads_ndjson(ndjson_data: str | bytes) -> Iterator[FHIRResource]:
    """Parse an in-memory NDJSON string or bytes lazily yielding FHIRResource instances without list allocation."""
    stream: IO[str] | IO[bytes]
    if isinstance(ndjson_data, bytes):
        stream = io.BytesIO(ndjson_data)
    else:
        stream = io.StringIO(ndjson_data)
    return _iter_stream(stream)


def iter_loads_ndjson_raw(ndjson_data: str | bytes) -> Iterator[dict]:
    """Parse an in-memory NDJSON string or bytes lazily yielding raw dicts without FHIRResource wrapping."""
    stream: IO[str] | IO[bytes]
    if isinstance(ndjson_data, bytes):
        stream = io.BytesIO(ndjson_data)
    else:
        stream = io.StringIO(ndjson_data)
    return _iter_stream_raw(stream)


def loads_ndjson(ndjson_str: str | bytes) -> list[FHIRResource]:
    """Parse an in-memory NDJSON string or bytes into a list of FHIRResource instances."""
    return list(iter_loads_ndjson(ndjson_str))


def iter_dumps_ndjson(resources: Iterable[FHIRResource | dict]) -> Iterator[str]:
    """Yield serialized NDJSON lines lazily as strings without full buffer accumulation."""
    for res in resources:
        data = res.to_dict() if isinstance(res, FHIRResource) else res
        yield _fast_dumps(data) + "\n"


def dumps_ndjson(resources: Iterable[FHIRResource | dict]) -> str:
    """Serialize an iterable of FHIR resources into an in-memory NDJSON string."""
    buf = io.StringIO()
    _write_stream(resources, buf)
    return buf.getvalue()
