# Matplotlib Extension

> **This is the reference (English) version.**
> The canonical (Japanese) version is [README-jp.md](README-jp.md).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/ci.yml/badge.svg)](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/ci.yml)
[![Charter Check](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/dev-charter-check.yml/badge.svg)](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/dev-charter-check.yml)
[![GitHub Sponsors](https://img.shields.io/github/sponsors/y-marui?style=social)](https://github.com/sponsors/y-marui)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-donate-yellow.svg)](https://www.buymeacoffee.com/y.marui)

A matplotlib extension library that saves and restores figures as editable PDF files, and provides axis formatting utilities.

## Requirements

- Python 3.11+

## Setup

```sh
uv sync
```

## Usage

### Save and Load Figures

Saves a matplotlib figure as a `.plt.pdf` file — a PDF with an embedded dill object that allows the figure to be fully restored.

```python
import matplotlib.pyplot as plt
import matplotlib_extension.pyplot as mplex

fig, ax = plt.subplots()
ax.plot([1, 2, 3], [1, 4, 9])

mplex.savefig(fig, "output.plt.pdf")             # exclusive (fails if exists)
mplex.savefig(fig, "output.plt.pdf", mode="w")   # overwrite
mplex.savefig(fig, "output.plt.pdf", mode="a")   # append

figs = mplex.loadfig("output.plt.pdf")
figs[0].show()
```

### LabelString

Converts shorthand keywords to LaTeX representations for matplotlib labels.

```python
from matplotlib_extension.label_string import LabelString

ax.set_xlabel(repr(LabelString("alpha vs para")))
# → "$\alpha$ vs $\parallel$"
```

Supported keywords: `alpha`, `beta`, `gamma`, `para`, `perp`

### Adjust Locator

Automatically adjusts major and minor tick locators to fit the data range.

```python
from matplotlib_extension.pyplot import adjust_locator

adjust_locator(ax, units=(0.5, 10), subunits=(0.1, 2))
```

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
