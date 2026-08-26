import hashlib
import json
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

import matplotlib.pyplot as plt
import matplotlib.scale as mscale
import numpy as np
import olefile
import pytest
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.projections import register_projection
from matplotlib.scale import LinearScale, register_scale
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject

from matplotlib_extension.container import extract_ole_native_png, extract_payload
from matplotlib_extension.package import (
    PackageError,
    UnsupportedFigureWarning,
    dump_package,
    inspect_package,
    load_package,
)
from matplotlib_extension.pyplot import loadfig, recover_data, savefig


def _simple_figure():
    fig, ax = plt.subplots()
    ax.plot([0.0, 1.0], [2.0, 3.0])
    return fig


def _package_files(payload: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _write_package(files: dict[str, bytes], *, compression: int = zipfile.ZIP_STORED) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=compression) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


def test_package_is_deterministic_and_data_only() -> None:
    fig = _simple_figure()

    first = dump_package(fig)
    second = dump_package(fig)

    assert first == second
    with zipfile.ZipFile(BytesIO(first)) as archive:
        assert archive.namelist() == [
            "manifest.json",
            "figure.json",
            "arrays/00000000.npy",
            "arrays/00000001.npy",
        ]
        assert all(info.compress_type == zipfile.ZIP_STORED for info in archive.infolist())
        figure_spec = json.loads(archive.read("figure.json"))
        assert figure_spec["schema_version"] == 1
    assert inspect_package(first)["format_version"] == 1
    plt.close(fig)


def test_every_container_embeds_identical_payload(tmp_path: Path) -> None:
    fig = _simple_figure()
    payloads = []
    for filename in (
        "figure.mpl.pdf",
        "figure.mpl.png",
        "figure.mpl.svg",
        "figure.ole",
        "figure.mplpkg",
    ):
        path = tmp_path / filename
        savefig(fig, path)
        payloads.append(extract_payload(path.read_bytes()))

    assert all(payload == payloads[0] for payload in payloads)
    plt.close(fig)


def test_graphic_containers_remain_normally_readable(tmp_path: Path) -> None:
    fig = _simple_figure()
    png = tmp_path / "figure.mpl.png"
    pdf = tmp_path / "figure.mpl.pdf"
    svg = tmp_path / "figure.mpl.svg"
    ole = tmp_path / "figure.ole"
    for path in (png, pdf, svg, ole):
        savefig(fig, path)

    with Image.open(png) as image:
        image.verify()
    assert len(PdfReader(pdf).pages) == 1
    ElementTree.parse(svg)
    assert olefile.isOleFile(ole)
    with olefile.OleFileIO(ole) as container:
        assert container.exists("\x01Ole10Native")
    native_png = extract_ole_native_png(ole.read_bytes())
    with Image.open(BytesIO(native_png)) as image:
        image.verify()
    assert extract_payload(native_png) == extract_payload(ole.read_bytes())
    plt.close(fig)


def test_compressed_pdf_attachment_is_rejected_before_decoding(tmp_path: Path) -> None:
    fig = _simple_figure()
    path = tmp_path / "figure.mpl.pdf"
    savefig(fig, path)
    reader = PdfReader(path)
    entries = reader.root_object["/Names"]["/EmbeddedFiles"]["/Names"]
    file_spec = entries[1].get_object()
    embedded = file_spec["/EF"]["/F"].get_object()
    file_spec[NameObject("/EF")][NameObject("/F")] = embedded.flate_encode()
    output = BytesIO()
    PdfWriter(clone_from=reader).write(output)

    with pytest.raises(PackageError, match="Compressed or invalid PDF attachments are forbidden"):
        extract_payload(output.getvalue())
    plt.close(fig)


def test_manifest_integrity_failure_is_rejected() -> None:
    fig = _simple_figure()
    files = _package_files(dump_package(fig))
    figure_data = bytearray(files["figure.json"])
    figure_data[-2] ^= 1
    files["figure.json"] = bytes(figure_data)
    with pytest.raises(PackageError, match="Integrity check failed"):
        load_package(_write_package(files))
    plt.close(fig)


def test_object_dtype_npy_is_rejected_without_loading_objects() -> None:
    fig = _simple_figure()
    files = _package_files(dump_package(fig))
    object_array = BytesIO()
    np.lib.format.write_array_header_1_0(
        object_array,
        {"descr": "|O", "fortran_order": False, "shape": (1,)},
    )
    object_array.write(b"\x00")
    files["arrays/00000000.npy"] = object_array.getvalue()
    manifest = json.loads(files["manifest.json"])
    for record in manifest["files"]:
        if record["path"] == "arrays/00000000.npy":
            data = files[record["path"]]
            record["size"] = len(data)
            record["sha256"] = hashlib.sha256(data).hexdigest()
    files["manifest.json"] = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    with pytest.raises(PackageError, match="Invalid NumPy array"):
        load_package(_write_package(files))
    plt.close(fig)


def test_compressed_package_entries_are_rejected() -> None:
    fig = _simple_figure()
    files = _package_files(dump_package(fig))

    with pytest.raises(PackageError, match="Compressed package entries are forbidden"):
        load_package(_write_package(files, compression=zipfile.ZIP_DEFLATED))
    plt.close(fig)


def test_unsafe_package_path_is_rejected() -> None:
    fig = _simple_figure()
    files = _package_files(dump_package(fig))
    files["../escape"] = b"data"

    with pytest.raises(PackageError, match="Unsafe package path"):
        load_package(_write_package(files))
    plt.close(fig)


def test_unknown_package_version_is_rejected() -> None:
    fig = _simple_figure()
    files = _package_files(dump_package(fig))
    manifest = json.loads(files["manifest.json"])
    manifest["format_version"] = 999
    files["manifest.json"] = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode() + b"\n"

    with pytest.raises(PackageError, match="Unsupported package format or version"):
        load_package(_write_package(files))
    plt.close(fig)


def test_code_like_text_is_restored_only_as_text() -> None:
    fig, ax = plt.subplots()
    content = "__import__('os').system('never run')"
    ax.set_title(content)

    restored = load_package(dump_package(fig))

    assert restored.axes[0].get_title() == content
    plt.close(fig)
    plt.close(restored)


def test_unsupported_subclass_is_warned_and_skipped() -> None:
    class CustomLine(Line2D):
        pass

    fig, ax = plt.subplots()
    ax.add_line(CustomLine([0, 1], [2, 3]))

    with pytest.warns(UnsupportedFigureWarning, match="CustomLine"):
        payload = dump_package(fig)

    restored = load_package(payload)
    assert len(restored.axes[0].lines) == 0
    assert inspect_package(payload)["warnings"] == ["Skipped unsupported line class CustomLine"]
    plt.close(fig)
    plt.close(restored)


def test_scatter_numeric_data_remains_recoverable(tmp_path: Path) -> None:
    fig, ax = plt.subplots()
    ax.scatter([1.0, 2.0], [3.0, 4.0], s=[5.0, 6.0], c=[7.0, 8.0], label="samples")
    path = tmp_path / "scatter.mpl.png"

    with pytest.warns(UnsupportedFigureWarning, match="Stored raw numeric data"):
        savefig(fig, path)

    records = recover_data(path)
    assert len(records) == 1
    assert records[0]["artist_type"] == "PathCollection"
    assert records[0]["label"] == "samples"
    np.testing.assert_allclose(records[0]["offsets"], [[1.0, 3.0], [2.0, 4.0]])
    np.testing.assert_allclose(records[0]["sizes"], [5.0, 6.0])
    np.testing.assert_allclose(records[0]["values"], [7.0, 8.0])
    plt.close(fig)


def test_legacy_object_attachment_is_never_restored(tmp_path: Path) -> None:
    fig = _simple_figure()
    rendered = BytesIO()
    fig.savefig(rendered, format="pdf")
    reader = PdfReader(BytesIO(rendered.getvalue()))
    writer = PdfWriter(clone_from=reader)
    writer.add_attachment("fig.dill", b"malicious object stream")
    legacy = tmp_path / "legacy.plt.pdf"
    with legacy.open("wb") as stream:
        writer.write(stream)

    with pytest.raises(PackageError, match="exactly one editable payload"):
        loadfig(legacy)
    plt.close(fig)


def test_restore_does_not_use_mutable_class_registries() -> None:
    fig = _simple_figure()
    payload = dump_package(fig)

    class RegistryAxes(Axes):
        name = "rectilinear"

        def __init__(self, *args, **kwargs):
            raise AssertionError("projection registry was used")

    class RegistryScale(LinearScale):
        name = "linear"

        def __init__(self, *args, **kwargs):
            raise AssertionError("scale registry was used")

    register_projection(RegistryAxes)
    try:
        restored = load_package(payload)
    finally:
        register_projection(Axes)

    assert type(restored.axes[0]) is Axes
    assert type(restored.axes[0].xaxis._scale) is LinearScale

    original_scale = mscale._scale_mapping["linear"]
    original_has_axis = mscale._scale_has_axis_parameter["linear"]
    register_scale(RegistryScale)
    try:
        with pytest.raises(PackageError, match="linear scale registry has been replaced"):
            load_package(payload)
    finally:
        mscale._scale_mapping["linear"] = original_scale
        mscale._scale_has_axis_parameter["linear"] = original_has_axis

    plt.close(fig)
    plt.close(restored)
