"""Embed one canonical figure package in normal graphics and OLE containers."""

from __future__ import annotations

import base64
import binascii
import re
import struct
import uuid
import zlib
from io import BytesIO
from typing import Any, Final, cast

import olefile
from pypdf import PdfReader, PdfWriter

from matplotlib_extension.package import (
    MAX_PACKAGE_BYTES,
    PackageError,
    inspect_package,
)

PNG_SIGNATURE: Final = b"\x89PNG\r\n\x1a\n"
PDF_SIGNATURE: Final = b"%PDF-"
CFB_SIGNATURE: Final = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
PNG_CHUNK: Final = b"mpFg"
PDF_ATTACHMENT: Final = "matplotlib-extension.mplpkg"
OLE_STREAM: Final = "\x01Ole10Native"
OLE_NATIVE_NAME: Final = b"figure.mpl.png"
SVG_NAMESPACE: Final = "https://github.com/y-marui/python-matplotlib-extension"
MAX_RENDERED_BYTES: Final = 512 * 1024 * 1024
MAX_EDITABLE_PNG_BYTES: Final = MAX_PACKAGE_BYTES + MAX_RENDERED_BYTES
MAX_OLE_BYTES: Final = MAX_EDITABLE_PNG_BYTES + 16 * 1024 * 1024

_SVG_PACKAGE_RE = re.compile(
    rb'<mplex:package\s+xmlns:mplex="https://github\.com/y-marui/python-matplotlib-extension"'
    rb'\s+encoding="base64">([A-Za-z0-9+/=\r\n]+)</mplex:package>'
)


def _validated_payload(payload: bytes) -> bytes:
    inspect_package(payload)
    return payload


def embed_png(rendered: bytes, payload: bytes) -> bytes:
    """Insert the canonical payload as a private ancillary PNG chunk."""
    _validated_payload(payload)
    if not rendered.startswith(PNG_SIGNATURE):
        raise PackageError("Matplotlib did not produce a PNG file")
    position = len(PNG_SIGNATURE)
    iend_position: int | None = None
    while position + 12 <= len(rendered):
        length = struct.unpack(">I", rendered[position : position + 4])[0]
        end = position + 12 + length
        if end > len(rendered):
            raise PackageError("Invalid PNG chunk length")
        chunk_type = rendered[position + 4 : position + 8]
        if chunk_type == PNG_CHUNK:
            raise PackageError("PNG already contains an editable payload")
        if chunk_type == b"IEND":
            if length != 0 or end != len(rendered):
                raise PackageError("Invalid PNG IEND chunk")
            iend_position = position
            break
        position = end
    if iend_position is None:
        raise PackageError("PNG IEND chunk is missing")
    chunk = struct.pack(">I", len(payload)) + PNG_CHUNK + payload
    chunk += struct.pack(">I", zlib.crc32(PNG_CHUNK + payload) & 0xFFFFFFFF)
    return rendered[:iend_position] + chunk + rendered[iend_position:]


def extract_png(data: bytes) -> bytes:
    """Extract and validate the canonical payload from a PNG."""
    if not data.startswith(PNG_SIGNATURE):
        raise PackageError("Not a PNG file")
    position = len(PNG_SIGNATURE)
    payloads: list[bytes] = []
    while position + 12 <= len(data):
        length = struct.unpack(">I", data[position : position + 4])[0]
        end = position + 12 + length
        if end > len(data):
            raise PackageError("Invalid PNG chunk length")
        chunk_type = data[position + 4 : position + 8]
        chunk_data = data[position + 8 : position + 8 + length]
        if chunk_type == PNG_CHUNK:
            expected_crc = struct.unpack(">I", data[position + 8 + length : end])[0]
            if zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF != expected_crc:
                raise PackageError("Editable PNG chunk failed its CRC check")
            payloads.append(chunk_data)
        if chunk_type == b"IEND":
            break
        position = end
    if len(payloads) != 1:
        raise PackageError("PNG must contain exactly one editable payload")
    return _validated_payload(payloads[0])


def embed_pdf(rendered: bytes, payload: bytes, *, title: str = "Figure") -> bytes:
    """Attach the canonical payload to an otherwise normal PDF."""
    _validated_payload(payload)
    if not rendered.startswith(PDF_SIGNATURE):
        raise PackageError("Matplotlib did not produce a PDF file")
    try:
        reader = PdfReader(BytesIO(rendered), strict=True)
        writer = PdfWriter(clone_from=reader)
        writer.add_attachment(PDF_ATTACHMENT, payload)
        if len(writer.pages):
            writer.add_outline_item(title, 0)
        output = BytesIO()
        writer.write(output)
    except Exception as exc:
        raise PackageError("Unable to construct editable PDF") from exc
    return output.getvalue()


def extract_pdf(data: bytes) -> bytes:
    """Extract and validate the canonical payload from a PDF attachment."""
    if not data.startswith(PDF_SIGNATURE):
        raise PackageError("Not a PDF file")
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        names = cast(Any, reader.root_object["/Names"].get_object())
        embedded_files = names["/EmbeddedFiles"].get_object()
        if set(embedded_files) != {"/Names"}:
            raise PackageError("PDF embedded-file name trees are not supported")
        entries = embedded_files["/Names"].get_object()
        if len(entries) != 2 or str(entries[0]) != PDF_ATTACHMENT:
            raise PackageError("PDF must contain exactly one editable payload")
        file_spec = entries[1].get_object()
        if (
            str(file_spec.get("/Type")) != "/Filespec"
            or str(file_spec.get("/F")) != PDF_ATTACHMENT
        ):
            raise PackageError("Invalid PDF attachment file specification")
        embedded = file_spec["/EF"]["/F"].get_object()
        if str(embedded.get("/Type")) != "/EmbeddedFile" or "/Filter" in embedded:
            raise PackageError("Compressed or invalid PDF attachments are forbidden")
        payload = embedded.get_data()
    except Exception as exc:
        if isinstance(exc, PackageError):
            raise
        raise PackageError("Invalid PDF file") from exc
    if not isinstance(payload, bytes):
        raise PackageError("Invalid PDF attachment")
    return _validated_payload(payload)


def embed_svg(rendered: bytes, payload: bytes) -> bytes:
    """Embed the canonical payload as base64 in SVG metadata."""
    _validated_payload(payload)
    if _SVG_PACKAGE_RE.search(rendered):
        raise PackageError("SVG already contains an editable payload")
    match = re.search(rb"<svg(?:\s|>)", rendered)
    if match is None:
        raise PackageError("Matplotlib did not produce an SVG file")
    end = rendered.find(b">", match.start())
    if end < 0:
        raise PackageError("Invalid SVG root element")
    encoded = base64.b64encode(payload)
    metadata = (
        b'\n <metadata><mplex:package xmlns:mplex="'
        + SVG_NAMESPACE.encode("ascii")
        + b'" encoding="base64">'
        + encoded
        + b"</mplex:package></metadata>"
    )
    return rendered[: end + 1] + metadata + rendered[end + 1 :]


def extract_svg(data: bytes) -> bytes:
    """Extract and validate the canonical payload from SVG metadata."""
    matches = _SVG_PACKAGE_RE.findall(data)
    if len(matches) != 1:
        raise PackageError("SVG must contain exactly one editable payload")
    try:
        payload = base64.b64decode(matches[0], validate=True)
    except binascii.Error as exc:
        raise PackageError("Invalid base64 SVG payload") from exc
    return _validated_payload(payload)


def _ole_native_stream(editable_png: bytes) -> bytes:
    name = OLE_NATIVE_NAME + b"\x00"
    path = b"C:\\" + name
    body = BytesIO()
    body.write(b"\x00\x00\x00\x00")
    body.write(struct.pack("<H", 2))
    body.write(name)
    body.write(path)
    body.write(struct.pack("<II", 0, 0))
    body.write(name)
    body.write(struct.pack("<I", len(editable_png)))
    body.write(editable_png)
    value = bytearray(body.getvalue())
    struct.pack_into("<I", value, 0, len(value) - 4)
    return bytes(value)


def _directory_entry(
    name: str,
    object_type: int,
    *,
    child: int = 0xFFFFFFFF,
    clsid: uuid.UUID | None = None,
    start_sector: int = 0xFFFFFFFE,
    stream_size: int = 0,
) -> bytes:
    encoded_name = (name + "\x00").encode("utf-16le")
    if len(encoded_name) > 64:
        raise PackageError("OLE stream name is too long")
    return struct.pack(
        "<64sHBBIII16sIQQIQ",
        encoded_name.ljust(64, b"\x00"),
        len(encoded_name),
        object_type,
        1,
        0xFFFFFFFF,
        0xFFFFFFFF,
        child,
        (clsid or uuid.UUID(int=0)).bytes_le,
        0,
        0,
        0,
        start_sector,
        stream_size,
    )


def _chain(fat: list[int], sectors: list[int]) -> None:
    for index, sector in enumerate(sectors):
        fat[sector] = sectors[index + 1] if index + 1 < len(sectors) else 0xFFFFFFFE


def embed_ole(editable_png: bytes) -> bytes:
    """Wrap one validated editable PNG in a generic OLE Package CFB object."""
    if len(editable_png) > MAX_EDITABLE_PNG_BYTES:
        raise PackageError("Editable PNG exceeds the OLE native size limit")
    extract_png(editable_png)
    native = _ole_native_stream(editable_png)
    sector_size = 4096
    mini_sector_size = 64
    sectors: list[bytes] = []
    regular_chains: list[list[int]] = []

    def allocate(content: bytes) -> list[int]:
        count = max(1, (len(content) + sector_size - 1) // sector_size)
        indexes = list(range(len(sectors), len(sectors) + count))
        sectors.extend(
            content[offset : offset + sector_size].ljust(sector_size, b"\x00")
            for offset in range(0, count * sector_size, sector_size)
        )
        regular_chains.append(indexes)
        return indexes

    mini_fat_indexes: list[int] = []
    if len(native) < 4096:
        mini_count = (len(native) + mini_sector_size - 1) // mini_sector_size
        mini_stream = native.ljust(mini_count * mini_sector_size, b"\x00")
        stream_indexes = [0]
        mini_stream_indexes = allocate(mini_stream)
        mini_entries = [index + 1 for index in range(mini_count)]
        mini_entries[-1] = 0xFFFFFFFE
        mini_fat_data = struct.pack(f"<{len(mini_entries)}I", *mini_entries)
        mini_fat_indexes = allocate(mini_fat_data)
        root_start = mini_stream_indexes[0]
        root_size = len(mini_stream)
        stream_start = stream_indexes[0]
    else:
        stream_indexes = allocate(native)
        root_start = 0xFFFFFFFE
        root_size = 0
        stream_start = stream_indexes[0]

    directory_index = len(sectors)
    package_clsid = uuid.UUID("0003000c-0000-0000-c000-000000000046")
    directory = _directory_entry(
        "Root Entry",
        5,
        child=1,
        clsid=package_clsid,
        start_sector=root_start,
        stream_size=root_size,
    )
    directory += _directory_entry(
        OLE_STREAM,
        2,
        start_sector=stream_start,
        stream_size=len(native),
    )
    directory += b"\x00" * (sector_size - len(directory))
    sectors.append(directory)
    regular_chains.append([directory_index])

    fat_count = 1
    while True:
        required = (len(sectors) + fat_count + (sector_size // 4) - 1) // (
            sector_size // 4
        )
        if required == fat_count:
            break
        fat_count = required
    if fat_count > 109:
        raise PackageError("OLE container exceeds the supported CFB size")
    fat_indexes = list(range(len(sectors), len(sectors) + fat_count))
    total_sector_count = len(sectors) + fat_count
    fat = [0xFFFFFFFF] * (fat_count * (sector_size // 4))
    for chain in regular_chains:
        _chain(fat, chain)
    for sector in fat_indexes:
        fat[sector] = 0xFFFFFFFD
    fat_data = struct.pack(f"<{len(fat)}I", *fat)
    sectors.extend(
        fat_data[offset : offset + sector_size]
        for offset in range(0, len(fat_data), sector_size)
    )
    if len(sectors) != total_sector_count:
        raise PackageError("Internal OLE sector allocation error")

    header = struct.pack(
        "<8s16sHHHHH6sIIIIIIIII",
        CFB_SIGNATURE,
        bytes(16),
        0x003E,
        4,
        0xFFFE,
        12,
        6,
        bytes(6),
        1,
        fat_count,
        directory_index,
        0,
        4096,
        mini_fat_indexes[0] if mini_fat_indexes else 0xFFFFFFFE,
        len(mini_fat_indexes),
        0xFFFFFFFE,
        0,
    )
    header += struct.pack(
        "<109I", *(fat_indexes + [0xFFFFFFFF] * (109 - len(fat_indexes)))
    )
    header = header.ljust(sector_size, b"\x00")
    return header + b"".join(sectors)


def _read_cstring(data: bytes, position: int) -> tuple[bytes, int]:
    end = data.find(b"\x00", position)
    if end < 0 or end - position > 4096:
        raise PackageError("Invalid OLE native string")
    return data[position:end], end + 1


def extract_ole_native_png(data: bytes) -> bytes:
    """Extract and validate the editable PNG from a generic OLE Package."""
    if not data.startswith(CFB_SIGNATURE):
        raise PackageError("Not an OLE compound file")
    if len(data) > MAX_OLE_BYTES:
        raise PackageError("OLE container exceeds the size limit")
    try:
        with olefile.OleFileIO(
            BytesIO(data), raise_defects=olefile.DEFECT_INCORRECT
        ) as container:
            paths = container.listdir(streams=True, storages=True)
            if paths != [[OLE_STREAM]]:
                raise PackageError("OLE container has unexpected streams or storages")
            if container.get_size(OLE_STREAM) > MAX_EDITABLE_PNG_BYTES + 1_000_000:
                raise PackageError("OLE native stream exceeds the size limit")
            native = container.openstream(OLE_STREAM).read(
                MAX_EDITABLE_PNG_BYTES + 1_000_000
            )
    except PackageError:
        raise
    except Exception as exc:
        raise PackageError("Invalid OLE compound file") from exc
    if not isinstance(native, bytes):
        raise PackageError("Invalid OLE native stream")
    if len(native) < 32:
        raise PackageError("OLE native stream is truncated")
    total_size = struct.unpack_from("<I", native, 0)[0]
    if total_size != len(native) - 4:
        raise PackageError("OLE native stream size is invalid")
    position = 4
    version = struct.unpack_from("<H", native, position)[0]
    position += 2
    if version != 2:
        raise PackageError("Unsupported OLE native stream version")
    display_name, position = _read_cstring(native, position)
    _source_path, position = _read_cstring(native, position)
    if display_name != OLE_NATIVE_NAME or position + 8 > len(native):
        raise PackageError("Unexpected OLE package metadata")
    position += 8
    _temp_path, position = _read_cstring(native, position)
    if position + 4 > len(native):
        raise PackageError("OLE native stream is truncated")
    editable_png_size = struct.unpack_from("<I", native, position)[0]
    position += 4
    if (
        editable_png_size > MAX_EDITABLE_PNG_BYTES
        or position + editable_png_size != len(native)
    ):
        raise PackageError("OLE native payload size is invalid")
    editable_png = native[position:]
    extract_png(editable_png)
    return editable_png


def extract_ole(data: bytes) -> bytes:
    """Extract the canonical payload from an editable-PNG OLE Package."""
    return extract_png(extract_ole_native_png(data))


def extract_payload(data: bytes) -> bytes:
    """Extract a canonical package from any supported editable container."""
    if data.startswith(PNG_SIGNATURE):
        return extract_png(data)
    if data.startswith(PDF_SIGNATURE):
        return extract_pdf(data)
    if data.startswith(CFB_SIGNATURE):
        return extract_ole(data)
    if data.startswith(b"PK\x03\x04"):
        return _validated_payload(data)
    if b"<svg" in data[:1_000_000]:
        return extract_svg(data)
    raise PackageError("Unsupported editable figure container")
