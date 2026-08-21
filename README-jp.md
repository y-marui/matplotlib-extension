# Matplotlib Extension

> **このファイルは正本（日本語版）です。**
> 英語版（参照）は [README.md](README.md) を参照してください。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/ci.yml/badge.svg)](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/ci.yml)
[![Charter Check](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/dev-charter-check.yml/badge.svg)](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/dev-charter-check.yml)
[![GitHub Sponsors](https://img.shields.io/github/sponsors/y-marui?style=social)](https://github.com/sponsors/y-marui)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-donate-yellow.svg)](https://www.buymeacoffee.com/y.marui)

matplotlib の拡張ライブラリ。Figure の data-only package をプロット画像または OLE object に埋め込み、別の Python process / console で安全に復元して追加編集できるようにする。軸フォーマッティングユーティリティも提供する。

## Requirements

- Python 3.11+

## Setup

~~~sh
uv sync
~~~

## Usage

### Save and Load Figures Safely

`matplotlib_extension` を import すると、既存の Matplotlib API に opt-in のキーワードが 1 つ追加される。表示部分は通常の PDF・PNG・SVG のままで、編集用の versioned data-only package が埋め込まれる。

このパッケージにおける「editable」とは、ファイルや OLE object 自体に編集UIを持たせることではない。保存したプロットを別の Python process / console で `Figure` に復元し、通常の Matplotlib API で追加編集できることを意味する。

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

PDF・PNG・SVGは通常の画像としてPowerPointを含む他のアプリケーションへ配置できる。OLEは同じcanonical packageを保持する受動的なデータ容器である。PowerPoint内の編集UI、Office add-in、COM/OLEの編集verb、埋め込みコードの実行は提供しない。編集は常に、対象ファイルまたは取り出したOLE objectをPythonへ渡し、`loadfig()`で復元して行う。

PowerPointなどからOLE objectを`oleObject1.bin`として取り出した場合も、拡張子ではなくファイル署名を判定するため直接復元できる。canonical packageを独立したファイルとして保存する場合は`extract_package()`を使う。

~~~python
from matplotlib_extension import extract_package, loadfig

fig = loadfig("oleObject1.bin")
extract_package("oleObject1.bin", "figure.mplpkg")
~~~

WindowsのOLE Packageへ埋め込むnative fileは`.mplpkg`とする。PowerPointのUIがnative fileの保存を提供する場合は、取り出した`.mplpkg`をそのままPythonへ渡せる。UIから保存できない場合は、PPTXをZIPとして開いて`ppt/embeddings/oleObject*.bin`を取り出し、上記APIへ渡す。どちらの場合もOffice側でコードは実行しない。

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
