"""Safe, data-only serialization for editable Matplotlib figures.

The package format is intentionally small and explicit.  It contains canonical
JSON plus NumPy ``.npy`` arrays and never deserializes Python objects.
"""

from __future__ import annotations

import hashlib
import json
import math
import warnings
import zipfile
from collections.abc import Mapping, Sequence
from io import BytesIO
from typing import Any, Final, cast

import matplotlib
import matplotlib.scale as mscale
import numpy as np
from matplotlib import colors
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection
from matplotlib.figure import Figure
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from matplotlib.markers import MarkerStyle
from matplotlib.scale import (
    AsinhScale,
    LinearScale,
    LogitScale,
    LogScale,
    ScaleBase,
    SymmetricalLogScale,
)
from matplotlib.text import Text
from matplotlib.ticker import (
    AutoLocator,
    AutoMinorLocator,
    FixedFormatter,
    FixedLocator,
    FormatStrFormatter,
    IndexLocator,
    LinearLocator,
    LogFormatter,
    LogFormatterExponent,
    LogFormatterMathtext,
    LogFormatterSciNotation,
    LogLocator,
    MaxNLocator,
    MultipleLocator,
    NullFormatter,
    NullLocator,
    PercentFormatter,
    ScalarFormatter,
    StrMethodFormatter,
)

PACKAGE_FORMAT: Final = "org.matplotlib-extension.figure-package"
PACKAGE_VERSION: Final = 1
FIGURE_SCHEMA_VERSION: Final = 1
MAX_PACKAGE_BYTES: Final = 256 * 1024 * 1024
MAX_JSON_BYTES: Final = 16 * 1024 * 1024
MAX_ARRAY_BYTES: Final = 128 * 1024 * 1024
MAX_ARRAY_COUNT: Final = 10_000
MAX_AXES: Final = 1_000
MAX_ARTISTS_PER_AXES: Final = 100_000
MAX_TEXT_LENGTH: Final = 1_000_000
_LEGEND_LOCATIONS: Final = {
    "best",
    "upper right",
    "upper left",
    "lower left",
    "lower right",
    "right",
    "center left",
    "center right",
    "lower center",
    "upper center",
    "center",
}
_SCALE_TYPES: Final = {
    "asinh": AsinhScale,
    "linear": LinearScale,
    "log": LogScale,
    "logit": LogitScale,
    "symlog": SymmetricalLogScale,
}


class PackageError(ValueError):
    """Raised when an editable figure package is invalid or unsafe."""


class UnsupportedFigureWarning(UserWarning):
    """Warning emitted when an unsupported object is skipped safely."""


def _json_bytes(value: object) -> bytes:
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise PackageError("Figure metadata is not canonical JSON") from exc
    return (text + "\n").encode("utf-8")


def _color(value: Any) -> str:
    return colors.to_hex(value, keep_alpha=True)


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(
        value, int | float | np.integer | np.floating
    ):
        raise PackageError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise PackageError(f"{name} must be finite")
    return result


def _warn(message: str, collected: list[str] | None = None) -> None:
    if collected is not None:
        collected.append(message)
    warnings.warn(message, UnsupportedFigureWarning, stacklevel=3)


class _ArrayStore:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def add(self, value: object) -> str:
        if len(self.files) >= MAX_ARRAY_COUNT:
            raise PackageError("Figure contains too many numeric arrays")
        array = np.asanyarray(value)
        if (
            array.dtype.hasobject
            or array.dtype.fields is not None
            or array.dtype.kind not in "biufc"
        ):
            raise PackageError(f"Unsupported array dtype: {array.dtype}")
        if array.nbytes > MAX_ARRAY_BYTES:
            raise PackageError("An individual array exceeds the size limit")
        if array.dtype.byteorder == ">" or (
            array.dtype.byteorder == "=" and not np.little_endian
        ):
            array = array.astype(array.dtype.newbyteorder("<"), copy=False)
        array = np.ascontiguousarray(array)
        stream = BytesIO()
        np.save(stream, array, allow_pickle=False)
        name = f"arrays/{len(self.files):08d}.npy"
        self.files[name] = stream.getvalue()
        return name


def _text_spec(text: Text, *, transform: str | None = None) -> dict[str, Any]:
    content = text.get_text()
    if len(content) > MAX_TEXT_LENGTH:
        raise PackageError("Text exceeds the length limit")
    font = text.get_fontproperties()
    family = [str(item) for item in font.get_family()]
    spec: dict[str, Any] = {
        "alpha": text.get_alpha(),
        "color": _color(text.get_color()),
        "fontfamily": family,
        "fontsize": float(text.get_fontsize()),
        "fontstretch": str(font.get_stretch()),
        "fontstyle": str(font.get_style()),
        "fontvariant": str(font.get_variant()),
        "fontweight": font.get_weight(),
        "horizontalalignment": str(text.get_horizontalalignment()),
        "rotation": float(text.get_rotation()),
        "text": content,
        "usetex": False,
        "verticalalignment": str(text.get_verticalalignment()),
        "visible": bool(text.get_visible()),
        "zorder": float(text.get_zorder()),
    }
    if transform is not None:
        x, y = text.get_position()
        spec.update({"position": [float(x), float(y)], "transform": transform})
    return spec


def _apply_text_spec(text: Text, spec: Mapping[str, Any]) -> None:
    text.set_text(_string(spec, "text", max_length=MAX_TEXT_LENGTH))
    text.set_alpha(_optional_number(spec, "alpha"))
    text.set_color(_safe_color(spec, "color"))
    text.set_fontfamily(_string_list(spec, "fontfamily", max_items=100))
    text.set_fontsize(_number(spec, "fontsize", minimum=0, maximum=1_000_000))
    text.set_fontstretch(_string(spec, "fontstretch", max_length=100))
    text.set_fontstyle(_enum(spec, "fontstyle", {"normal", "italic", "oblique"}))
    text.set_fontvariant(_enum(spec, "fontvariant", {"normal", "small-caps"}))
    weight = spec.get("fontweight")
    if not isinstance(weight, str | int | float) or isinstance(weight, bool):
        raise PackageError("fontweight is invalid")
    text.set_fontweight(weight)  # type: ignore[arg-type]
    text.set_horizontalalignment(
        _enum(spec, "horizontalalignment", {"left", "center", "right"})
    )
    text.set_rotation(_number(spec, "rotation", minimum=-1_000_000, maximum=1_000_000))
    text.set_usetex(False)
    text.set_verticalalignment(
        _enum(
            spec,
            "verticalalignment",
            {"top", "bottom", "center", "baseline", "center_baseline"},
        )
    )
    text.set_visible(_boolean(spec, "visible"))
    text.set_zorder(_number(spec, "zorder", minimum=-1_000_000, maximum=1_000_000))


def _line_spec(line: Line2D, arrays: _ArrayStore) -> dict[str, Any]:
    marker = line.get_marker()
    if (
        not isinstance(marker, str | int)
        or isinstance(marker, bool)
        or marker not in MarkerStyle.markers
    ):
        raise PackageError("Custom marker paths are not supported")
    return {
        "alpha": line.get_alpha(),
        "antialiased": bool(line.get_antialiased()),
        "color": _color(line.get_color()),
        "dash_capstyle": str(line.get_dash_capstyle()),
        "dash_joinstyle": str(line.get_dash_joinstyle()),
        "drawstyle": str(line.get_drawstyle()),
        "label": str(line.get_label()),
        "linestyle": str(line.get_linestyle()),
        "linewidth": float(line.get_linewidth()),
        "marker": marker,
        "markeredgecolor": _color(line.get_markeredgecolor()),
        "markeredgewidth": float(line.get_markeredgewidth()),
        "markerfacecolor": _color(line.get_markerfacecolor()),
        "markersize": float(line.get_markersize()),
        "visible": bool(line.get_visible()),
        "xdata": arrays.add(line.get_xdata(orig=False)),
        "ydata": arrays.add(line.get_ydata(orig=False)),
        "zorder": float(line.get_zorder()),
    }


def _locator_spec(
    locator: Any, arrays: _ArrayStore, collected: list[str]
) -> dict[str, Any] | None:
    locator_type = type(locator)
    if locator_type is NullLocator:
        return {"type": "NullLocator"}
    if locator_type is AutoLocator:
        return {"type": "AutoLocator"}
    if locator_type is AutoMinorLocator:
        ndivs = getattr(locator, "ndivs", getattr(locator, "n", None))
        return {
            "ndivs": ndivs if isinstance(ndivs, int) else None,
            "type": "AutoMinorLocator",
        }
    if locator_type is FixedLocator:
        return {
            "locs": arrays.add(locator.locs),
            "nbins": locator.nbins,
            "type": "FixedLocator",
        }
    if locator_type is MultipleLocator:
        return {
            "base": float(locator._edge.step),
            "offset": float(getattr(locator, "_offset", 0.0)),
            "type": "MultipleLocator",
        }
    if locator_type is LinearLocator:
        return {"numticks": locator.numticks, "type": "LinearLocator"}
    if locator_type is IndexLocator:
        return {
            "base": float(locator._base),
            "offset": float(locator.offset),
            "type": "IndexLocator",
        }
    if locator_type is MaxNLocator:
        return {
            "integer": bool(locator._integer),
            "min_n_ticks": int(locator._min_n_ticks),
            "nbins": locator._nbins,
            "prune": locator._prune,
            "steps": arrays.add(locator._steps),
            "symmetric": bool(locator._symmetric),
            "type": "MaxNLocator",
        }
    if locator_type is LogLocator:
        return {
            "base": float(locator._base),
            "numticks": locator.numticks,
            "subs": None if locator._subs is None else arrays.add(locator._subs),
            "type": "LogLocator",
        }
    _warn(f"Skipped unsupported locator {locator_type.__name__}", collected)
    return None


def _formatter_spec(formatter: Any, collected: list[str]) -> dict[str, Any] | None:
    formatter_type = type(formatter)
    if formatter_type is NullFormatter:
        return {"type": "NullFormatter"}
    if formatter_type is ScalarFormatter:
        use_offset = formatter.get_useOffset()
        return {
            "powerlimits": list(formatter._powerlimits),
            "scientific": bool(formatter._scientific),
            "type": "ScalarFormatter",
            "use_math_text": bool(formatter.get_useMathText()),
            "use_offset": use_offset,
        }
    if formatter_type is FixedFormatter:
        return {
            "seq": [str(value) for value in formatter.seq],
            "type": "FixedFormatter",
        }
    if formatter_type is FormatStrFormatter:
        return {"fmt": formatter.fmt, "type": "FormatStrFormatter"}
    if formatter_type is StrMethodFormatter:
        return {"fmt": formatter.fmt, "type": "StrMethodFormatter"}
    if formatter_type is PercentFormatter:
        return {
            "decimals": formatter.decimals,
            "is_latex": bool(formatter._is_latex),
            "symbol": formatter.symbol,
            "type": "PercentFormatter",
            "xmax": float(formatter.xmax),
        }
    if formatter_type in {
        LogFormatter,
        LogFormatterExponent,
        LogFormatterMathtext,
        LogFormatterSciNotation,
    }:
        return {
            "base": float(formatter._base),
            "label_only_base": bool(formatter.labelOnlyBase),
            "minor_thresholds": list(formatter.minor_thresholds),
            "type": formatter_type.__name__,
        }
    _warn(f"Skipped unsupported formatter {formatter_type.__name__}", collected)
    return None


def _axis_spec(
    axis: matplotlib.axis.Axis, arrays: _ArrayStore, collected: list[str]
) -> dict[str, Any]:
    return {
        "major_formatter": _formatter_spec(axis.get_major_formatter(), collected),
        "major_locator": _locator_spec(axis.get_major_locator(), arrays, collected),
        "minor_formatter": _formatter_spec(axis.get_minor_formatter(), collected),
        "minor_locator": _locator_spec(axis.get_minor_locator(), arrays, collected),
        "visible": bool(axis.get_visible()),
    }


def _scale_name(axis: matplotlib.axis.Axis, collected: list[str]) -> str:
    scale = getattr(axis, "_scale", None)
    for name, scale_type in _SCALE_TYPES.items():
        if type(scale) is scale_type:
            return name
    _warn(
        f"Replaced unsupported scale class {type(scale).__name__} with LinearScale",
        collected,
    )
    return "linear"


def _axes_spec(
    ax: matplotlib.axes.Axes, arrays: _ArrayStore, collected: list[str]
) -> dict[str, Any]:
    lines: list[dict[str, Any]] = []
    for line in ax.lines:
        if type(line) is not Line2D:
            _warn(f"Skipped unsupported line class {type(line).__name__}", collected)
            continue
        try:
            lines.append(_line_spec(line, arrays))
        except (PackageError, TypeError, ValueError) as exc:
            _warn(f"Skipped Line2D: {exc}", collected)

    texts: list[dict[str, Any]] = []
    for text in ax.texts:
        if type(text) is not Text:
            _warn(f"Skipped unsupported text class {type(text).__name__}", collected)
            continue
        transform = text.get_transform()
        if transform is ax.transData:
            transform_name = "data"
        elif transform is ax.transAxes:
            transform_name = "axes"
        elif transform is ax.figure.transFigure:
            transform_name = "figure"
        else:
            _warn("Skipped Text with an unsupported transform", collected)
            continue
        texts.append(_text_spec(text, transform=transform_name))

    recovery: list[dict[str, Any]] = []
    for collection in ax.collections:
        if type(collection) is PathCollection:
            try:
                values = collection.get_array()
                recovery.append(
                    {
                        "artist_type": "PathCollection",
                        "label": str(collection.get_label()),
                        "offsets": arrays.add(np.ma.getdata(collection.get_offsets())),
                        "sizes": arrays.add(collection.get_sizes()),
                        "values": None
                        if values is None
                        else arrays.add(np.ma.getdata(values)),
                    }
                )
                _warn(
                    "Stored raw numeric data for unsupported PathCollection; "
                    "artist skipped",
                    collected,
                )
            except (PackageError, TypeError, ValueError) as exc:
                _warn(f"Skipped PathCollection recovery data: {exc}", collected)
        else:
            _warn(
                f"Skipped unsupported collection class {type(collection).__name__}",
                collected,
            )
    for image in ax.images:
        if type(image) is AxesImage:
            try:
                image_data = image.get_array()
                if image_data is None:
                    raise PackageError("AxesImage has no numeric data")
                recovery.append(
                    {
                        "artist_type": "AxesImage",
                        "data": arrays.add(np.ma.getdata(image_data)),
                        "extent": [
                            _finite_number(value, "extent")
                            for value in cast(Sequence[object], image.get_extent())
                        ],
                        "label": str(image.get_label()),
                    }
                )
                _warn(
                    "Stored raw numeric data for unsupported AxesImage; artist skipped",
                    collected,
                )
            except (PackageError, TypeError, ValueError) as exc:
                _warn(f"Skipped AxesImage recovery data: {exc}", collected)
        else:
            _warn(f"Skipped unsupported image class {type(image).__name__}", collected)
    unsupported_groups: dict[str, Sequence[Any]] = {
        "artist": cast(Sequence[Any], ax.artists),
        "patch": cast(Sequence[Any], ax.patches),
        "table": cast(Sequence[Any], ax.tables),
    }
    for group_name, artists in unsupported_groups.items():
        for artist in artists:
            _warn(
                f"Skipped unsupported {group_name} class {type(artist).__name__}",
                collected,
            )

    legend_spec: dict[str, Any] | None = None
    legend = ax.get_legend()
    if legend is not None:
        loc = getattr(legend, "_loc", None)
        if (
            not isinstance(loc, str | int)
            or isinstance(loc, bool)
            or (isinstance(loc, str) and loc not in _LEGEND_LOCATIONS)
            or (isinstance(loc, int) and not 0 <= loc <= 10)
        ):
            _warn("Skipped legend with an unsupported location", collected)
        else:
            legend_spec = {
                "frameon": bool(legend.get_frame_on()),
                "labels": [item.get_text() for item in legend.get_texts()],
                "loc": loc,
                "title": legend.get_title().get_text(),
                "visible": bool(legend.get_visible()),
            }

    aspect = ax.get_aspect()
    if not isinstance(aspect, str | int | float) or isinstance(aspect, bool):
        aspect = "auto"
    return {
        "aspect": aspect,
        "axis_on": bool(ax.axison),
        "facecolor": _color(ax.get_facecolor()),
        "legend": legend_spec,
        "lines": lines,
        "position": [float(value) for value in ax.get_position(original=True).bounds],
        "recovery": recovery,
        "texts": texts,
        "title": _text_spec(ax.title),
        "xaxis": _axis_spec(ax.xaxis, arrays, collected),
        "xlabel": _text_spec(ax.xaxis.label),
        "xlim": [float(value) for value in ax.get_xlim()],
        "xscale": _scale_name(ax.xaxis, collected),
        "yaxis": _axis_spec(ax.yaxis, arrays, collected),
        "ylabel": _text_spec(ax.yaxis.label),
        "ylim": [float(value) for value in ax.get_ylim()],
        "yscale": _scale_name(ax.yaxis, collected),
    }


def figure_to_spec(
    figure: Figure,
) -> tuple[dict[str, Any], dict[str, bytes], list[str]]:
    """Convert a Figure to a data-only specification and NumPy array files."""
    if type(figure) is not Figure:
        raise PackageError(
            "Only the allowlisted matplotlib.figure.Figure class is supported"
        )
    if len(figure.axes) > MAX_AXES:
        raise PackageError("Figure contains too many axes")
    arrays = _ArrayStore()
    collected: list[str] = []
    axes_specs = []
    for ax in figure.axes:
        if type(ax) is not Axes:
            _warn(f"Skipped unsupported axes class {type(ax).__name__}", collected)
            continue
        axes_specs.append(_axes_spec(ax, arrays, collected))
    suptitle = getattr(figure, "_suptitle", None)
    spec = {
        "axes": axes_specs,
        "figure": {
            "dpi": float(figure.dpi),
            "edgecolor": _color(figure.get_edgecolor()),
            "facecolor": _color(figure.get_facecolor()),
            "frameon": bool(figure.get_frameon()),
            "size_inches": [float(value) for value in figure.get_size_inches()],
            "suptitle": _text_spec(suptitle) if type(suptitle) is Text else None,
        },
        "schema_version": FIGURE_SCHEMA_VERSION,
    }
    return spec, arrays.files, collected


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def dump_package(figure: Figure) -> bytes:
    """Serialize *figure* into a deterministic, data-only package."""
    spec, arrays, collected = figure_to_spec(figure)
    figure_data = _json_bytes(spec)
    if len(figure_data) > MAX_JSON_BYTES:
        raise PackageError("figure.json exceeds the JSON size limit")
    files: dict[str, bytes] = {"figure.json": figure_data, **arrays}
    file_records = [
        {
            "media_type": "application/json"
            if name.endswith(".json")
            else "application/x-npy",
            "path": name,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        }
        for name, data in sorted(files.items())
    ]
    manifest = {
        "figure_schema_version": FIGURE_SCHEMA_VERSION,
        "files": file_records,
        "format": PACKAGE_FORMAT,
        "format_version": PACKAGE_VERSION,
        "warnings": collected,
    }
    manifest_data = _json_bytes(manifest)
    if len(manifest_data) > MAX_JSON_BYTES:
        raise PackageError("manifest.json exceeds the JSON size limit")
    output = BytesIO()
    with zipfile.ZipFile(output, "w", allowZip64=True) as archive:
        archive.writestr(_zip_info("manifest.json"), manifest_data)
        for name in ["figure.json", *sorted(arrays)]:
            archive.writestr(_zip_info(name), files[name])
    payload = output.getvalue()
    if len(payload) > MAX_PACKAGE_BYTES:
        raise PackageError("Figure package exceeds the size limit")
    return payload


def _read_json(data: bytes, name: str) -> Mapping[str, Any]:
    if len(data) > MAX_JSON_BYTES:
        raise PackageError(f"{name} exceeds the JSON size limit")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise PackageError(f"{name} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise PackageError(f"{name} must contain a JSON object")
    return value


def _validated_files(payload: bytes) -> tuple[Mapping[str, Any], dict[str, bytes]]:
    if len(payload) > MAX_PACKAGE_BYTES:
        raise PackageError("Figure package exceeds the size limit")
    try:
        archive = zipfile.ZipFile(BytesIO(payload), "r")
    except zipfile.BadZipFile as exc:
        raise PackageError("Invalid figure package ZIP") from exc
    with archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise PackageError("Duplicate package entries are forbidden")
        if len(names) > MAX_ARRAY_COUNT + 2:
            raise PackageError("Figure package contains too many files")
        for info in infos:
            name = info.filename
            if (
                name.startswith("/")
                or "\\" in name
                or any(part in {"", ".", ".."} for part in name.split("/"))
            ):
                raise PackageError("Unsafe package path")
            if info.file_size > MAX_ARRAY_BYTES:
                raise PackageError("Package entry exceeds the size limit")
            if (
                info.compress_size != info.file_size
                or info.compress_type != zipfile.ZIP_STORED
            ):
                raise PackageError("Compressed package entries are forbidden")
        if "manifest.json" not in names or "figure.json" not in names:
            raise PackageError("Required package files are missing")
        manifest = _read_json(archive.read("manifest.json"), "manifest.json")
        if (
            manifest.get("format") != PACKAGE_FORMAT
            or manifest.get("format_version") != PACKAGE_VERSION
        ):
            raise PackageError("Unsupported package format or version")
        if manifest.get("figure_schema_version") != FIGURE_SCHEMA_VERSION:
            raise PackageError("Unsupported figure schema version")
        records = manifest.get("files")
        if not isinstance(records, list):
            raise PackageError("Manifest files must be a list")
        expected_names = {"manifest.json"}
        files: dict[str, bytes] = {}
        for record in records:
            if not isinstance(record, dict):
                raise PackageError("Invalid manifest file record")
            path = record.get("path")
            digest = record.get("sha256")
            size = record.get("size")
            if (
                not isinstance(path, str)
                or path == "manifest.json"
                or path in expected_names
            ):
                raise PackageError("Invalid or duplicate manifest path")
            if not isinstance(digest, str) or len(digest) != 64:
                raise PackageError("Invalid manifest digest")
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                raise PackageError("Invalid manifest size")
            if path not in names:
                raise PackageError("Manifest references a missing file")
            data = archive.read(path)
            if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
                raise PackageError(f"Integrity check failed for {path}")
            expected_names.add(path)
            files[path] = data
        if expected_names != set(names):
            raise PackageError("Package contains unlisted files")
        return manifest, files


def inspect_package(payload: bytes) -> Mapping[str, Any]:
    """Validate *payload* and return its manifest without restoring a Figure."""
    manifest, _ = _validated_files(payload)
    return manifest


def recover_numeric_data(payload: bytes) -> list[dict[str, Any]]:
    """Return numeric recovery records without constructing Matplotlib artists."""
    _manifest, files = _validated_files(payload)
    spec = _read_json(files["figure.json"], "figure.json")
    if spec.get("schema_version") != FIGURE_SCHEMA_VERSION:
        raise PackageError("Unsupported figure schema version")
    recovered: list[dict[str, Any]] = []
    axes_specs = _sequence(spec.get("axes"), "axes", max_items=MAX_AXES)
    for axes_index, axes_value in enumerate(axes_specs):
        axes_spec = _mapping(axes_value, "axes")
        records = _sequence(
            axes_spec.get("recovery", []), "recovery", max_items=MAX_ARTISTS_PER_AXES
        )
        for record_value in records:
            record = _mapping(record_value, "recovery record")
            artist_type = _enum(record, "artist_type", {"PathCollection", "AxesImage"})
            result: dict[str, Any] = {
                "artist_type": artist_type,
                "axes_index": axes_index,
                "label": _string(record, "label", max_length=MAX_TEXT_LENGTH),
            }
            if artist_type == "PathCollection":
                result["offsets"] = _load_array(files, record.get("offsets"))
                result["sizes"] = _load_array(files, record.get("sizes"))
                result["values"] = (
                    None
                    if record.get("values") is None
                    else _load_array(files, record.get("values"))
                )
            else:
                result["data"] = _load_array(files, record.get("data"))
                result["extent"] = _number_list(record.get("extent"), "extent", 4)
            recovered.append(result)
    return recovered


def _load_array(files: Mapping[str, bytes], path: object) -> np.ndarray:
    if not isinstance(path, str) or not path.startswith("arrays/") or path not in files:
        raise PackageError("Invalid array reference")
    try:
        array = np.load(BytesIO(files[path]), allow_pickle=False)
    except (OSError, ValueError, EOFError) as exc:
        raise PackageError(f"Invalid NumPy array {path}") from exc
    if (
        not isinstance(array, np.ndarray)
        or array.dtype.hasobject
        or array.dtype.fields is not None
    ):
        raise PackageError("Object or structured NumPy arrays are forbidden")
    if array.dtype.kind not in "biufc" or array.nbytes > MAX_ARRAY_BYTES:
        raise PackageError("Unsupported or oversized NumPy array")
    return array


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise PackageError(f"{name} must be an object")
    return value


def _sequence(
    value: object, name: str, *, length: int | None = None, max_items: int | None = None
) -> Sequence[Any]:
    if not isinstance(value, list):
        raise PackageError(f"{name} must be a list")
    if length is not None and len(value) != length:
        raise PackageError(f"{name} must contain {length} items")
    if max_items is not None and len(value) > max_items:
        raise PackageError(f"{name} contains too many items")
    return value


def _string(spec: Mapping[str, Any], key: str, *, max_length: int = 10_000) -> str:
    value = spec.get(key)
    if not isinstance(value, str) or len(value) > max_length:
        raise PackageError(f"{key} must be a bounded string")
    return value


def _string_list(spec: Mapping[str, Any], key: str, *, max_items: int) -> list[str]:
    values = _sequence(spec.get(key), key, max_items=max_items)
    if any(not isinstance(item, str) or len(item) > 1_000 for item in values):
        raise PackageError(f"{key} must contain bounded strings")
    return list(values)


def _boolean(spec: Mapping[str, Any], key: str) -> bool:
    value = spec.get(key)
    if not isinstance(value, bool):
        raise PackageError(f"{key} must be a boolean")
    return value


def _number(
    spec: Mapping[str, Any],
    key: str,
    *,
    minimum: float = -1e300,
    maximum: float = 1e300,
) -> float:
    value = _finite_number(spec.get(key), key)
    if not minimum <= value <= maximum:
        raise PackageError(f"{key} is outside the allowed range")
    return value


def _optional_number(spec: Mapping[str, Any], key: str) -> float | None:
    if spec.get(key) is None:
        return None
    return _number(spec, key)


def _enum(spec: Mapping[str, Any], key: str, allowed: set[str]) -> Any:
    value = _string(spec, key, max_length=100)
    if value not in allowed:
        raise PackageError(f"Unsupported {key}: {value}")
    return value


def _safe_color(spec: Mapping[str, Any], key: str) -> str:
    value = _string(spec, key, max_length=64)
    if not colors.is_color_like(value):
        raise PackageError(f"Invalid {key}")
    return value


def _number_list(value: object, name: str, length: int) -> list[float]:
    items = _sequence(value, name, length=length)
    return [_finite_number(item, name) for item in items]


def _restore_locator(
    spec: object, files: Mapping[str, bytes]
) -> matplotlib.ticker.Locator | None:
    if spec is None:
        return None
    item = _mapping(spec, "locator")
    locator_type = _string(item, "type", max_length=100)
    if locator_type == "NullLocator":
        return NullLocator()
    if locator_type == "AutoLocator":
        return AutoLocator()
    if locator_type == "AutoMinorLocator":
        ndivs = item.get("ndivs")
        if ndivs is not None and (
            not isinstance(ndivs, int)
            or isinstance(ndivs, bool)
            or not 1 <= ndivs <= 1000
        ):
            raise PackageError("Invalid AutoMinorLocator ndivs")
        return AutoMinorLocator(ndivs)
    if locator_type == "FixedLocator":
        nbins = item.get("nbins")
        if nbins is not None and (
            not isinstance(nbins, int) or isinstance(nbins, bool) or nbins < 1
        ):
            raise PackageError("Invalid FixedLocator nbins")
        return FixedLocator(_load_array(files, item.get("locs")).tolist(), nbins=nbins)
    if locator_type == "MultipleLocator":
        return MultipleLocator(
            base=_number(item, "base", minimum=1e-300), offset=_number(item, "offset")
        )
    if locator_type == "LinearLocator":
        numticks = item.get("numticks")
        if numticks is not None and (
            not isinstance(numticks, int)
            or isinstance(numticks, bool)
            or not 0 <= numticks <= 1_000_000
        ):
            raise PackageError("Invalid LinearLocator numticks")
        return LinearLocator(numticks=numticks)
    if locator_type == "IndexLocator":
        return IndexLocator(
            base=_number(item, "base", minimum=1e-300), offset=_number(item, "offset")
        )
    if locator_type == "MaxNLocator":
        nbins = item.get("nbins")
        if not (nbins == "auto" or isinstance(nbins, int)) or isinstance(nbins, bool):
            raise PackageError("Invalid MaxNLocator nbins")
        prune = item.get("prune")
        if prune not in {None, "lower", "upper", "both"}:
            raise PackageError("Invalid MaxNLocator prune")
        return MaxNLocator(
            nbins=nbins,
            steps=_load_array(files, item.get("steps")),
            integer=_boolean(item, "integer"),
            symmetric=_boolean(item, "symmetric"),
            prune=prune,
            min_n_ticks=int(_number(item, "min_n_ticks", minimum=1, maximum=1000)),
        )
    if locator_type == "LogLocator":
        subs_ref = item.get("subs")
        subs = None if subs_ref is None else _load_array(files, subs_ref).tolist()
        numticks = item.get("numticks")
        if not (
            numticks is None or numticks == "auto" or isinstance(numticks, int)
        ) or isinstance(numticks, bool):
            raise PackageError("Invalid LogLocator numticks")
        return LogLocator(
            base=_number(item, "base", minimum=1e-300), subs=subs, numticks=numticks
        )
    raise PackageError(f"Locator is not allowlisted: {locator_type}")


def _restore_formatter(spec: object) -> matplotlib.ticker.Formatter | None:
    if spec is None:
        return None
    item = _mapping(spec, "formatter")
    formatter_type = _string(item, "type", max_length=100)
    if formatter_type == "NullFormatter":
        return NullFormatter()
    if formatter_type == "ScalarFormatter":
        formatter = ScalarFormatter(
            useOffset=item.get("use_offset", True),
            useMathText=_boolean(item, "use_math_text"),
        )
        formatter.set_scientific(_boolean(item, "scientific"))
        limits = _number_list(item.get("powerlimits"), "powerlimits", 2)
        formatter.set_powerlimits((int(limits[0]), int(limits[1])))
        return formatter
    if formatter_type == "FixedFormatter":
        return FixedFormatter(_string_list(item, "seq", max_items=1_000_000))
    if formatter_type == "FormatStrFormatter":
        return FormatStrFormatter(_string(item, "fmt", max_length=1_000))
    if formatter_type == "StrMethodFormatter":
        return StrMethodFormatter(_string(item, "fmt", max_length=1_000))
    if formatter_type == "PercentFormatter":
        decimals = item.get("decimals")
        if decimals is not None and (
            not isinstance(decimals, int)
            or isinstance(decimals, bool)
            or not 0 <= decimals <= 100
        ):
            raise PackageError("Invalid PercentFormatter decimals")
        return PercentFormatter(
            xmax=_number(item, "xmax", minimum=1e-300),
            decimals=decimals,
            symbol=_string(item, "symbol", max_length=100),
            is_latex=_boolean(item, "is_latex"),
        )
    log_types = {
        "LogFormatter": LogFormatter,
        "LogFormatterExponent": LogFormatterExponent,
        "LogFormatterMathtext": LogFormatterMathtext,
        "LogFormatterSciNotation": LogFormatterSciNotation,
    }
    if formatter_type in log_types:
        thresholds = _number_list(item.get("minor_thresholds"), "minor_thresholds", 2)
        return log_types[formatter_type](
            base=_number(item, "base", minimum=1e-300),
            labelOnlyBase=_boolean(item, "label_only_base"),
            minor_thresholds=(thresholds[0], thresholds[1]),
        )
    raise PackageError(f"Formatter is not allowlisted: {formatter_type}")


def _restore_axis(
    axis: matplotlib.axis.Axis, spec: object, files: Mapping[str, bytes]
) -> None:
    item = _mapping(spec, "axis")
    major_locator = _restore_locator(item.get("major_locator"), files)
    minor_locator = _restore_locator(item.get("minor_locator"), files)
    major_formatter = _restore_formatter(item.get("major_formatter"))
    minor_formatter = _restore_formatter(item.get("minor_formatter"))
    if major_locator is not None:
        axis.set_major_locator(major_locator)
    if minor_locator is not None:
        axis.set_minor_locator(minor_locator)
    if major_formatter is not None:
        axis.set_major_formatter(major_formatter)
    if minor_formatter is not None:
        axis.set_minor_formatter(minor_formatter)
    axis.set_visible(_boolean(item, "visible"))


def _restore_line(
    ax: matplotlib.axes.Axes, spec: object, files: Mapping[str, bytes]
) -> Line2D:
    item = _mapping(spec, "line")
    marker = item.get("marker")
    if (
        not isinstance(marker, str | int)
        or isinstance(marker, bool)
        or marker not in MarkerStyle.markers
    ):
        raise PackageError("Invalid line marker")
    line = Line2D(
        _load_array(files, item.get("xdata")),
        _load_array(files, item.get("ydata")),
        alpha=_optional_number(item, "alpha"),
        antialiased=_boolean(item, "antialiased"),
        color=_safe_color(item, "color"),
        dash_capstyle=_enum(item, "dash_capstyle", {"butt", "projecting", "round"}),
        dash_joinstyle=_enum(item, "dash_joinstyle", {"miter", "round", "bevel"}),
        drawstyle=_enum(
            item,
            "drawstyle",
            {"default", "steps", "steps-pre", "steps-mid", "steps-post"},
        ),
        label=_string(item, "label", max_length=MAX_TEXT_LENGTH),
        linestyle=_string(item, "linestyle", max_length=100),  # type: ignore[arg-type]
        linewidth=_number(item, "linewidth", minimum=0, maximum=1_000_000),
        marker=marker,  # type: ignore[arg-type]
        markeredgecolor=_safe_color(item, "markeredgecolor"),
        markeredgewidth=_number(item, "markeredgewidth", minimum=0, maximum=1_000_000),
        markerfacecolor=_safe_color(item, "markerfacecolor"),
        markersize=_number(item, "markersize", minimum=0, maximum=1_000_000),
        visible=_boolean(item, "visible"),
        zorder=_number(item, "zorder", minimum=-1_000_000, maximum=1_000_000),
    )
    ax.add_line(line)
    return line


def _restore_scale(name: str, axis: matplotlib.axis.Axis) -> ScaleBase:
    scale_type = _SCALE_TYPES.get(name)
    if scale_type is None:
        raise PackageError(f"Scale is not allowlisted: {name}")
    return cast(ScaleBase, scale_type(axis))


def _restore_axes(figure: Figure, spec: object, files: Mapping[str, bytes]) -> None:
    item = _mapping(spec, "axes")
    position = _number_list(item.get("position"), "position", 4)
    if any(value < -1000 or value > 1000 for value in position):
        raise PackageError("Axes position is outside the allowed range")
    rect = (position[0], position[1], position[2], position[3])
    scale_mapping = getattr(mscale, "_scale_mapping", {})
    if scale_mapping.get("linear") is not LinearScale:
        raise PackageError(
            "Matplotlib's built-in linear scale registry has been replaced"
        )
    ax = Axes(
        figure,
        rect,
        facecolor=_safe_color(item, "facecolor"),
    )
    figure.add_axes(ax)
    xscale = _enum(item, "xscale", {"linear", "log", "symlog", "logit", "asinh"})
    yscale = _enum(item, "yscale", {"linear", "log", "symlog", "logit", "asinh"})
    ax.set_xscale(_restore_scale(xscale, ax.xaxis))
    ax.set_yscale(_restore_scale(yscale, ax.yaxis))
    lines = _sequence(item.get("lines"), "lines", max_items=MAX_ARTISTS_PER_AXES)
    for line_spec in lines:
        _restore_line(ax, line_spec, files)
    texts = _sequence(item.get("texts"), "texts", max_items=MAX_ARTISTS_PER_AXES)
    for text_value in texts:
        text_spec = _mapping(text_value, "text")
        transform_name = _enum(text_spec, "transform", {"data", "axes", "figure"})
        transform = {
            "data": ax.transData,
            "axes": ax.transAxes,
            "figure": figure.transFigure,
        }[transform_name]
        position_value = _number_list(text_spec.get("position"), "text position", 2)
        text = ax.text(
            position_value[0], position_value[1], "", transform=transform, usetex=False
        )
        _apply_text_spec(text, text_spec)
    _apply_text_spec(ax.title, _mapping(item.get("title"), "title"))
    _apply_text_spec(ax.xaxis.label, _mapping(item.get("xlabel"), "xlabel"))
    _apply_text_spec(ax.yaxis.label, _mapping(item.get("ylabel"), "ylabel"))
    aspect = item.get("aspect")
    if isinstance(aspect, str):
        if aspect not in {"auto", "equal"}:
            raise PackageError("Unsupported axes aspect")
    elif isinstance(aspect, int | float) and not isinstance(aspect, bool):
        aspect = _finite_number(aspect, "aspect")
    else:
        raise PackageError("Invalid axes aspect")
    ax.set_aspect(cast(Any, aspect))
    xlim = _number_list(item.get("xlim"), "xlim", 2)
    ylim = _number_list(item.get("ylim"), "ylim", 2)
    ax.set_xlim((xlim[0], xlim[1]))
    ax.set_ylim((ylim[0], ylim[1]))
    _restore_axis(ax.xaxis, item.get("xaxis"), files)
    _restore_axis(ax.yaxis, item.get("yaxis"), files)
    if _boolean(item, "axis_on"):
        ax.set_axis_on()
    else:
        ax.set_axis_off()
    legend_value = item.get("legend")
    if legend_value is not None:
        legend_spec = _mapping(legend_value, "legend")
        labels = _string_list(legend_spec, "labels", max_items=MAX_ARTISTS_PER_AXES)
        handles = ax.lines[: len(labels)]
        loc = legend_spec.get("loc")
        if (
            not isinstance(loc, str | int)
            or isinstance(loc, bool)
            or (isinstance(loc, str) and loc not in _LEGEND_LOCATIONS)
            or (isinstance(loc, int) and not 0 <= loc <= 10)
        ):
            raise PackageError("Invalid legend location")
        legend = ax.legend(
            handles,
            labels,
            frameon=_boolean(legend_spec, "frameon"),
            loc=cast(Any, loc),
            title=_string(legend_spec, "title", max_length=MAX_TEXT_LENGTH),
        )
        legend.set_visible(_boolean(legend_spec, "visible"))


def load_package(payload: bytes) -> Figure:
    """Restore a Figure from a validated data-only package."""
    _manifest, files = _validated_files(payload)
    spec = _read_json(files["figure.json"], "figure.json")
    if spec.get("schema_version") != FIGURE_SCHEMA_VERSION:
        raise PackageError("Unsupported figure schema version")
    figure_spec = _mapping(spec.get("figure"), "figure")
    size = _number_list(figure_spec.get("size_inches"), "size_inches", 2)
    if any(value <= 0 or value > 100_000 for value in size):
        raise PackageError("Invalid figure size")
    figure = Figure(
        figsize=(size[0], size[1]),
        dpi=_number(figure_spec, "dpi", minimum=1e-6, maximum=1_000_000),
        facecolor=_safe_color(figure_spec, "facecolor"),
        edgecolor=_safe_color(figure_spec, "edgecolor"),
        frameon=_boolean(figure_spec, "frameon"),
    )
    axes_specs = _sequence(spec.get("axes"), "axes", max_items=MAX_AXES)
    for axes_spec in axes_specs:
        _restore_axes(figure, axes_spec, files)
    suptitle_spec = figure_spec.get("suptitle")
    if suptitle_spec is not None:
        suptitle = figure.suptitle("", usetex=False)
        _apply_text_spec(suptitle, _mapping(suptitle_spec, "suptitle"))
    return figure
