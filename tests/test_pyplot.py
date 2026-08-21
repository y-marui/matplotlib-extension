from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator, PercentFormatter

from matplotlib_extension import pyplot
from matplotlib_extension.package import PackageError


def _figure() -> Figure:
    fig, ax = plt.subplots(figsize=(5, 3), dpi=120)
    x = np.linspace(0, 10, 100)
    ax.plot(x, np.sin(x), "o--", label="sin", color="#123456")
    ax.set(title="A title", xlabel="x", ylabel="y")
    ax.text(0.25, 0.75, "axes text", transform=ax.transAxes)
    ax.xaxis.set_major_locator(MultipleLocator(2.0, offset=0.5))
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=2.0, decimals=1))
    ax.legend(title="Legend")
    fig.suptitle("Figure title")
    return fig


@pytest.mark.parametrize("suffix", ["pdf", "png", "svg", "ole", "mplpkg"])
def test_save_and_loadfig_all_formats(tmp_path: Path, suffix: str) -> None:
    fig = _figure()
    filename = tmp_path / f"figure.{suffix}"

    pyplot.savefig(fig, filename)
    restored = pyplot.loadfig(filename)

    assert isinstance(restored, Figure)
    assert len(restored.axes) == 1
    ax = restored.axes[0]
    assert ax.get_title() == "A title"
    assert ax.get_xlabel() == "x"
    assert ax.get_ylabel() == "y"
    assert len(ax.lines) == 1
    np.testing.assert_allclose(ax.lines[0].get_xdata(), np.linspace(0, 10, 100))
    np.testing.assert_allclose(ax.lines[0].get_ydata(), np.sin(np.linspace(0, 10, 100)))
    assert ax.lines[0].get_color() == "#123456ff"
    assert [text.get_text() for text in ax.texts] == ["axes text"]
    assert ax.get_legend() is not None
    assert ax.get_legend().get_title().get_text() == "Legend"
    assert restored._suptitle is not None
    assert restored._suptitle.get_text() == "Figure title"
    plt.close(fig)
    plt.close(restored)


def test_figure_savefig_editable_keyword(tmp_path: Path) -> None:
    fig = _figure()
    filename = tmp_path / "figure.png"

    fig.savefig(filename, editable=True)

    restored = pyplot.loadfig(filename)
    assert restored.axes[0].get_title() == "A title"
    plt.close(fig)
    plt.close(restored)


def test_normal_savefig_is_unchanged(tmp_path: Path) -> None:
    fig = _figure()
    filename = tmp_path / "normal.png"

    fig.savefig(filename)

    with pytest.raises(PackageError, match="exactly one editable payload"):
        pyplot.loadfig(filename)
    plt.close(fig)


def test_savefig_exclusive_mode(tmp_path: Path) -> None:
    fig = _figure()
    filename = tmp_path / "exclusive.pdf"
    pyplot.savefig(fig, filename, mode="x")

    with pytest.raises(FileExistsError):
        pyplot.savefig(fig, filename, mode="x")
    plt.close(fig)


def test_savefig_overwrites_atomically(tmp_path: Path) -> None:
    fig = _figure()
    filename = tmp_path / "overwrite.pdf"
    filename.write_bytes(b"old")

    pyplot.savefig(fig, filename)

    assert filename.read_bytes().startswith(b"%PDF-")
    assert pyplot.loadfig(filename).axes[0].get_title() == "A title"
    plt.close(fig)


def test_savefig_append_is_explicitly_unsupported(tmp_path: Path) -> None:
    fig = _figure()
    filename = tmp_path / "append.pdf"

    with pytest.raises(ValueError, match="append is not supported"):
        pyplot.savefig(fig, filename, mode="a")
    plt.close(fig)


def test_adjust_locator() -> None:
    fig, ax = plt.subplots()
    x = np.linspace(0, 10, 100)
    y = np.cos(x)
    ax.plot(x, y)
    pyplot.adjust_locator(ax)
    assert hasattr(ax.xaxis, "get_major_locator")
    assert hasattr(ax.xaxis, "get_minor_locator")
    plt.close(fig)
