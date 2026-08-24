import os
import tempfile
from collections.abc import Callable
from functools import wraps
from io import BytesIO
from pathlib import Path
from typing import Any

import matplotlib
import matplotlib.figure
import numpy as np
from matplotlib.ticker import MultipleLocator

from matplotlib_extension.container import (
    CFB_SIGNATURE,
    MAX_OLE_BYTES,
    PNG_SIGNATURE,
    embed_ole,
    embed_pdf,
    embed_png,
    embed_svg,
    extract_ole_native_png,
    extract_payload,
    extract_png,
)
from matplotlib_extension.package import (
    PackageError,
    dump_package,
    load_package,
    recover_numeric_data,
)

_ORIGINAL_FIGURE_SAVEFIG = getattr(
    matplotlib.figure.Figure,
    "__matplotlib_extension_original_savefig__",
    matplotlib.figure.Figure.savefig,
)
_MAX_CONTAINER_BYTES = MAX_OLE_BYTES


def _output_format(filename: Path, requested: object) -> str:
    if requested is not None:
        if not isinstance(requested, str):
            raise ValueError("format must be a string")
        output_format = requested.lower()
    elif filename.name.lower().endswith(".mplpkg"):
        output_format = "mplpkg"
    else:
        output_format = filename.suffix.lower().removeprefix(".")
    if output_format not in {"pdf", "png", "svg", "ole", "mplpkg"}:
        raise ValueError("Editable figures support PDF, PNG, SVG, OLE, and MPLPKG")
    return output_format


def _write_file(filename: Path, data: bytes, mode: str) -> None:
    if mode not in {"x", "w"}:
        raise ValueError("mode must be 'x' or 'w'; editable append is not supported")
    if mode == "x":
        with filename.open("xb") as stream:
            stream.write(data)
        return
    descriptor, temporary_name = tempfile.mkstemp(
        dir=filename.parent,
        prefix=f".{filename.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, filename)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def savefig(
    fig: matplotlib.figure.Figure,
    filename: Path | str,
    *,
    editable: bool = True,
    mode: str = "w",
    title: str = "Figure",
    **kwargs: Any,
) -> None:
    """Save a normal graphic with a safe editable figure package embedded.

    Args:
        fig: The exact allowlisted Matplotlib ``Figure`` to serialize.
        filename: Destination ending in ``.pdf``, ``.png``, ``.svg``,
            ``.ole``, or ``.mplpkg``.
        editable: When false, delegate to Matplotlib's original ``savefig``.
        mode: ``"w"`` for atomic overwrite or ``"x"`` for exclusive create.
        title: PDF outline title.
        **kwargs: Normal Matplotlib ``savefig`` keyword arguments.
    """
    destination = Path(filename)
    if mode not in {"x", "w"}:
        raise ValueError("mode must be 'x' or 'w'; editable append is not supported")
    requested_format = kwargs.pop("format", None)
    output_format = _output_format(destination, requested_format)
    if not editable:
        if output_format in {"ole", "mplpkg"}:
            raise ValueError("OLE and MPLPKG are editable-only formats")
        _ORIGINAL_FIGURE_SAVEFIG(fig, destination, format=output_format, **kwargs)
        return

    payload = dump_package(fig)
    if output_format == "mplpkg":
        output = payload
    elif output_format == "ole":
        rendered = BytesIO()
        _ORIGINAL_FIGURE_SAVEFIG(fig, rendered, format="png", **kwargs)
        output = embed_ole(embed_png(rendered.getvalue(), payload))
    else:
        rendered = BytesIO()
        _ORIGINAL_FIGURE_SAVEFIG(fig, rendered, format=output_format, **kwargs)
        if output_format == "pdf":
            output = embed_pdf(rendered.getvalue(), payload, title=title)
        elif output_format == "png":
            output = embed_png(rendered.getvalue(), payload)
        else:
            output = embed_svg(rendered.getvalue(), payload)
    _write_file(destination, output, mode)


def _read_file(filename: Path | str) -> bytes:
    source = Path(filename)
    with source.open("rb") as stream:
        data = stream.read(_MAX_CONTAINER_BYTES + 1)
    if len(data) > _MAX_CONTAINER_BYTES:
        raise PackageError("Editable figure container exceeds the size limit")
    return data


def loadfig(filename: Path | str) -> matplotlib.figure.Figure:
    """Restore one Figure from any supported editable container.

    Args:
        filename: Editable PDF, PNG, SVG, OLE, or raw MPLPKG path.

    Returns:
        A newly constructed allowlisted Matplotlib Figure.

    Raises:
        PackageError: If the container or package is invalid, unsafe, legacy,
            or unsupported. Legacy dill files are never deserialized.
    """
    return load_package(extract_payload(_read_file(filename)))


def extract_editable_png(
    filename: Path | str,
    destination: Path | str,
    *,
    mode: str = "x",
) -> None:
    """Extract one validated, user-facing editable PNG.

    This is primarily useful for OLE objects exported from presentation files.
    An editable PNG source is validated and copied unchanged. An OLE/CFB source
    is unwrapped to its native editable PNG. Other containers are rejected so
    every presentation extraction produces the same normal image format.

    Args:
        filename: Editable PNG or OLE/CFB path.
        destination: Destination ending in ``.png``.
        mode: ``"x"`` for exclusive creation or ``"w"`` for atomic overwrite.
    """
    output = Path(destination)
    if output.suffix.lower() != ".png":
        raise ValueError("editable extraction destination must end in .png")
    source = _read_file(filename)
    if source.startswith(PNG_SIGNATURE):
        extract_png(source)
        editable_png = source
    elif source.startswith(CFB_SIGNATURE):
        editable_png = extract_ole_native_png(source)
    else:
        raise PackageError("Editable PNG extraction requires a PNG or OLE container")
    _write_file(output, editable_png, mode)


def recover_data(filename: Path | str) -> list[dict[str, Any]]:
    """Recover numeric records for supported-but-not-restored artist types."""
    return recover_numeric_data(extract_payload(_read_file(filename)))


def install_matplotlib_savefig() -> None:
    """Install support for ``fig.savefig(..., editable=True)`` once."""
    current = matplotlib.figure.Figure.savefig
    if getattr(current, "__matplotlib_extension_editable__", False):
        return

    @wraps(current)
    def savefig_with_editable(
        figure: matplotlib.figure.Figure,
        filename: Path | str,
        *args: Any,
        editable: bool = False,
        **kwargs: Any,
    ) -> Any:
        if not editable:
            return current(figure, filename, *args, **kwargs)
        if args:
            raise TypeError("editable savefig accepts keyword arguments after filename")
        mode = kwargs.pop("mode", "w")
        title = kwargs.pop("title", "Figure")
        return savefig(figure, filename, editable=True, mode=mode, title=title, **kwargs)

    setattr(savefig_with_editable, "__matplotlib_extension_editable__", True)
    setattr(
        matplotlib.figure.Figure,
        "__matplotlib_extension_original_savefig__",
        _ORIGINAL_FIGURE_SAVEFIG,
    )
    setattr(matplotlib.figure.Figure, "savefig", savefig_with_editable)


def _adjust_locator_axis(
    get_lim: Callable[[], tuple[float, float]],
    set_lim: Callable[..., Any],
    axis: matplotlib.axis.Axis,
    unit: float | None,
    subunit: float | None,
) -> None:
    """Automatically adjust the locator of the axis.

    Parameters
    ----------
    get_lim : callable
        function of getting the limit of the axis
    set_lim : callable
        function of setting the limit of the axis
    axis : matplotlib.axis.Axis
        axis object to adjust the locator
    """
    min_val, max_val = get_lim()
    if unit is None:
        unit = 10 ** np.floor(np.log10(max_val - min_val))
    min_val = unit * np.floor(min_val / unit)
    max_val = unit * np.ceil(max_val / unit)
    set_lim(min_val, max_val)

    ticklocs = axis.get_ticklocs()
    unit_major = ticklocs[1] - ticklocs[0]
    if subunit is None:
        unit_minor = min(ticklocs[1] - min_val, max_val - ticklocs[-2])
    else:
        unit_minor = subunit
    if unit_minor != unit_major:
        axis.set_minor_locator(MultipleLocator(unit_minor))


def adjust_locator(
    ax: matplotlib.axes.Axes,
    units: tuple[float | None, float | None] = (None, None),
    subunits: tuple[float | None, float | None] = (None, None),
) -> None:
    """Automatically adjust the locator of the axes.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        axes object
    """
    unit_x, unit_y = units
    subunit_x, subunit_y = subunits
    _adjust_locator_axis(ax.get_xlim, ax.set_xlim, ax.xaxis, unit_x, subunit_x)
    _adjust_locator_axis(ax.get_ylim, ax.set_ylim, ax.yaxis, unit_y, subunit_y)
