import matplotlib.pyplot as plt
from io import BytesIO, StringIO
import dill
import fitz
from send2trash import send2trash
from pypdf import PdfWriter
from pathlib import Path
import matplotlib
import numpy as np
from matplotlib.ticker import MultipleLocator
from typing import List


def savefig(fig: plt.figure, filename: Path, mode: str = "x", title: str = "Figure"):
    """Save the current figure to a file of ".plt.pdf" which is PDF file including dill object.

    Args:
        filename (str): The name of the file to save the figure to.
    """
    assert mode in ["x", "w", "a"]

    if isinstance(filename, str):
        filename = Path(filename)

    with PdfWriter() as merger:
        if isinstance(filename, Path) and filename.exists():
            if mode == "x":
                raise FileExistsError(f"{filename}")
            elif mode == "w":
                send2trash(filename)
            elif mode == "a":
                merger.append(filename)

        with BytesIO() as fp_pdf:
            fig.savefig(fp_pdf, format="pdf")
            fp_pdf.seek(0)

            with BytesIO() as fp_dill:
                dill.dump(fig, fp_dill)
                fp_dill.seek(0)

                doc = fitz.open("pdf", fp_pdf)
                page: fitz.Page = doc[0]
                page.add_file_annot(None, fp_dill, "fig.dill")
                doc.save(fp_pdf)
                fp_pdf.seek(0)

            merger.append(fp_pdf)
            merger.add_outline_item(title, merger.get_num_pages() - 1)

        merger.write(filename)


def loadfig(filename: str) -> plt.figure:
    """Load the figure from a file of ".plt.pdf" which is PDF file including dill object.

    Args:
        filename (str): The name of the file to load the figure from.

    Returns:
        List[plt.figure]: The figure object.
    """
    if isinstance(filename, str):
        filename = Path(filename)

    with filename.open("rb") as fp:
        doc = fitz.open(fp)
        figs = []
        for page in doc:
            for annot in page.annots():
                if annot.info["content"] == "fig.dill":
                    fig = dill.loads(annot.get_file())
                    figs.append(fig)

        return figs


def _adjust_locator_axis(
    get_lim: callable, set_lim: callable, axis: matplotlib.axis.Axis, unit: float
):
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
    unit_minor = min(ticklocs[1] - min_val, max_val - ticklocs[-2])
    if unit_minor != unit_major:
        axis.set_minor_locator(MultipleLocator(unit_minor))


def adjust_locator(ax: matplotlib.axes.Axes, units: List[float] = (None, None)):
    """Automatically adjust the locator of the axes.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        axes object
    """
    unit_x, unit_y = units
    _adjust_locator_axis(ax.get_xlim, ax.set_xlim, ax.xaxis, unit_x)
    _adjust_locator_axis(ax.get_ylim, ax.set_ylim, ax.yaxis, unit_y)
