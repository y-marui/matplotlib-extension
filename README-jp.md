# Matplotlib Extension

> **このファイルは正本（日本語版）です。**
> 英語版（参照）は [README.md](README.md) を参照してください。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/ci.yml/badge.svg)](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/ci.yml)
[![Charter Check](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/dev-charter-check.yml/badge.svg)](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/dev-charter-check.yml)
[![GitHub Sponsors](https://img.shields.io/github/sponsors/y-marui?style=social)](https://github.com/sponsors/y-marui)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-donate-yellow.svg)](https://www.buymeacoffee.com/y.marui)

matplotlib の拡張ライブラリ。図を安全な編集可能 PDF・PNG・SVG・OLE として保存・復元する機能と、軸フォーマッティングユーティリティを提供する。

## Requirements

- Python 3.11+

## Setup

~~~sh
uv sync
~~~

## Usage

### Save and Load Figures Safely

`matplotlib_extension` を import すると、既存の Matplotlib API に opt-in のキーワードが 1 つ追加される。表示部分は通常の PDF・PNG・SVG のままで、編集用の versioned data-only package が埋め込まれる。

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
restored.savefig("restored.png")
~~~

独立 API では atomic overwrite と排他作成も指定できる。

~~~python
from matplotlib_extension import savefig

savefig(fig, "figure.pdf")
savefig(fig, "new-figure.pdf", mode="x")
savefig(fig, "figure.mplpkg")  # raw canonical package
~~~

この形式は、シリアライズされた Python object を一切 restore しない。canonical JSON と numeric NumPy array だけを使い、allowlist 済みの Matplotlib type だけを復元する。object dtype は拒否し、新しい `Figure` を構築する前に package path・size・version・SHA-256 digest を検証する。旧 object-bearing file は復元せず拒否する。

現在の round-trip 対象は、基本的な `Figure`、`Axes`、`Line2D`、`Text`、`Legend`、scale、locator、formatter。未対応 object は `UnsupportedFigureWarning` とともに skip する。scatter と image の numeric data は `matplotlib_extension.recover_data()` で回収でき、artist coverage の拡張は [roadmap](ROADMAP.md) で管理する。

trust boundary の詳細は [format specification](docs/EDITABLE_FORMAT.md) と [security policy](SECURITY.md) を参照。

### LabelString

略称キーワードを matplotlib ラベル用の LaTeX 表記に変換する。

~~~python
from matplotlib_extension.label_string import LabelString

ax.set_xlabel(repr(LabelString("alpha vs para")))
# → "$\alpha$ vs $\parallel$"
~~~

対応キーワード: `alpha`, `beta`, `gamma`, `para`, `perp`

### Adjust Locator

データ範囲に合わせて主・補助目盛りを自動調整する。

~~~python
from matplotlib_extension.pyplot import adjust_locator

adjust_locator(ax, units=(0.5, 10), subunits=(0.1, 2))
~~~

## Commands

| コマンド | 説明 |
|---|---|
| `uv run pytest` | テスト実行 |
| `uv run ruff check .` | リント |
| `uv run ruff format .` | フォーマット |
| `uv run mypy matplotlib_extension` | 型チェック |

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) を参照。

## License

MIT — [LICENSE](LICENSE) を参照。

---
*この文書には英語版 [README.md](README.md) があります。編集時は同一コミットで更新してください。*
