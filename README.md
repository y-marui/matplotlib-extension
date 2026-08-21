# Matplotlib Extension

> **This is the reference (English) version.**
> The canonical (Japanese) version is [README-jp.md](README-jp.md).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/ci.yml/badge.svg)](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/ci.yml)
[![Charter Check](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/dev-charter-check.yml/badge.svg)](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/dev-charter-check.yml)
[![GitHub Sponsors](https://img.shields.io/github/sponsors/y-marui?style=social)](https://github.com/sponsors/y-marui)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-donate-yellow.svg)](https://www.buymeacoffee.com/y.marui)

A matplotlib extension library that embeds a data-only Figure package in plot images or OLE objects so another Python process or console can safely restore and continue editing the Figure. It also provides axis formatting utilities.

## Requirements

- Python 3.11+

## Setup

~~~sh
uv sync
~~~

## Usage

### Save and Load Figures Safely

Importing `matplotlib_extension` adds one opt-in keyword to Matplotlib's existing API. The visible PDF, PNG, or SVG remains a normal graphic, while a versioned data-only package is embedded for editing.

In this package, "editable" does not mean that the file or OLE object contains an editing UI. It means that another Python process or console can restore the saved plot as a `Figure` and continue editing it with the normal Matplotlib API.

~~~python
import matplotlib.pyplot as plt
import matplotlib_extension

fig, ax = plt.subplots()
ax.plot([1, 2, 3], [1, 4, 9])

fig.savefig("figure.pdf", editable=True)
fig.savefig("figure.png", editable=True)
fig.savefig("figure.svg", editable=True)
fig.savefig("figure.ole", editable=True)  # generic OLE Package container

restored = matplotlib_extension.loadfig("figure.pdf")
restored.axes[0].set_title("Edited in another Python console")
restored.savefig("restored.png")
~~~

PDF, PNG, and SVG outputs remain ordinary graphics that can be placed in applications including PowerPoint. OLE is a passive container for the same canonical package. This project does not provide an in-PowerPoint editor or execute embedded code. Editing always happens in Python after passing the file or extracted OLE object to `loadfig()`.

An OLE object extracted by presentation software as a file such as `oleObject1.bin` can be restored directly because loading detects its file signature rather than trusting its extension. Use `extract_package()` when an independent canonical package file is desired.

~~~python
from matplotlib_extension import extract_package, loadfig

fig = loadfig("oleObject1.bin")
extract_package("oleObject1.bin", "figure.mplpkg")
~~~

The native file embedded in a Windows OLE Package is an `.mplpkg`. The user selects the intended OLE object in PowerPoint, saves or exports its native `.mplpkg` or OLE `.bin`, and passes that file to Python. Python does not scan the entire PPTX and guess which object should be restored.

If the generic OLE Package operations cannot save the native file reliably, a Windows extraction/export-only verb or adapter may be added. Such an adapter only copies the embedded data to a file; it never restores or edits a Figure. All editing remains in Python.

On macOS, the workflow does not depend on Windows OLE activation or verbs. An extraction-only PowerPoint bridge obtains the user-selected OLE shape and a copy of the current PPTX through PowerPoint APIs, resolves only the OLE `.bin` referenced by that shape, and saves it locally. Python never receives the whole PPTX to guess the target, and the bridge never restores or edits a Figure. The exported `.bin` is passed to the same `loadfig()` API.

The standalone API also supports atomic overwrite and exclusive creation:

~~~python
from matplotlib_extension import savefig

savefig(fig, "figure.pdf")
savefig(fig, "new-figure.pdf", mode="x")
savefig(fig, "figure.mplpkg")  # raw canonical package
~~~

The format never restores a serialized Python object. It uses canonical JSON and numeric NumPy arrays, restores only allowlisted Matplotlib types, rejects object dtypes, and verifies package paths, sizes, versions, and SHA-256 digests before constructing a new `Figure`. Legacy object-bearing files are rejected rather than restored.

Current round-trip support covers basic `Figure`, `Axes`, `Line2D`, `Text`, `Legend`, scales, locators, and formatters. Unsupported objects are skipped with `UnsupportedFigureWarning`. Numeric scatter and image data can still be retrieved with `matplotlib_extension.recover_data()`; broader artist coverage is tracked in the [roadmap](ROADMAP.md).

See the [format specification](docs/EDITABLE_FORMAT.md) and [security policy](SECURITY.md) for the exact trust boundary.

### LabelString

Converts shorthand keywords to LaTeX representations for matplotlib labels.

~~~python
from matplotlib_extension.label_string import LabelString

ax.set_xlabel(repr(LabelString("alpha vs para")))
# → "$\alpha$ vs $\parallel$"
~~~

Supported keywords: `alpha`, `beta`, `gamma`, `para`, `perp`

### Adjust Locator

Automatically adjusts major and minor tick locators to fit the data range.

~~~python
from matplotlib_extension.pyplot import adjust_locator

adjust_locator(ax, units=(0.5, 10), subunits=(0.1, 2))
~~~

## Commands

| Command | Description |
|---|---|
| `uv run pytest` | Run tests |
| `uv run ruff check .` | Lint |
| `uv run ruff format .` | Format |
| `uv run mypy matplotlib_extension` | Type check |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).

---
*This document has a Japanese canonical version [README-jp.md](README-jp.md). Update both in the same commit when editing.*
