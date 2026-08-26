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

fig.savefig("figure.mpl.pdf", editable=True)
fig.savefig("figure.mpl.png", editable=True)
fig.savefig("figure.mpl.svg", editable=True)
fig.savefig("figure.ole", editable=True)  # native fileは通常に開けるeditable PNG

restored = matplotlib_extension.loadfig("figure.mpl.pdf")
restored.axes[0].set_title("Edited in another Python console")
restored.savefig("restored.png")
~~~

PDF・PNG・SVGは通常の画像としてPowerPointを含む他のアプリケーションへ配置できる。OLEは同じcanonical packageを保持する受動的なデータ容器である。PowerPoint内の編集UIや埋め込みコードの実行は提供しない。編集は常に、対象ファイルまたは取り出したOLE objectをPythonへ渡し、`loadfig()`で復元して行う。

編集可能な画像は、通常形式と目視で区別できるよう`.mpl.png`・`.mpl.pdf`・`.mpl.svg`のcompound suffixを使う。PowerPointからユーザーが保存するファイル形式は、Windows・Macとも`figure.mpl.png`に統一する。これは通常のPNGとして開け、同時に安全なcanonical payloadを保持する。`.bin`はPPTX内部、`.mplpkg`はcanonical serialization内部の形式であり、通常の受け渡しには使わない。

~~~python
from matplotlib_extension import extract_editable_png, loadfig

# PowerPointの抽出ブリッジが保存した共通形式
fig = loadfig("figure.mpl.png")

# raw OLE/CFBを手動で取得した場合の低レベル救済API
extract_editable_png("oleObject1.bin", "figure.mpl.png")
~~~

OLE Packageへ埋め込むnative file自体を`figure.mpl.png`とする。Windowsでは標準OLE操作または抽出専用adapterがこのnative PNGを保存する。Python側でPPTX全体を走査して対象objectを推測する機能は提供しない。

汎用OLE Packageの標準操作だけで安定して保存できない場合は、Windows向けに抽出・export専用のverbまたはadapterを追加できる。ただし、それは埋め込みeditable PNGをファイルへコピーするだけであり、Figureのrestoreや編集は行わない。編集処理は引き続きPythonだけで行う。

MacではWindows OLEのactivationやverbに依存しない。PowerPoint用の抽出専用ブリッジが、ユーザーの選択したOLE Shapeと現在のPPTXコピーをPowerPoint APIから取得し、そのShapeが参照する内部OLE objectからnative PNGを取り出して`figure.mpl.png`として保存する。PPTX全体をPythonへ渡して対象を推測させず、ブリッジ内でもFigureのrestoreや編集は行わない。

独立 API では atomic overwrite と排他作成も指定できる。

~~~python
from matplotlib_extension import savefig

savefig(fig, "figure.mpl.pdf")
savefig(fig, "new-figure.mpl.pdf", mode="x")
savefig(fig, "figure.mplpkg")  # 内部検証・高度な用途向けraw canonical package
~~~

### Legacy dill Files

旧`.plt.pdf`はdill等でシリアライズされたlive Python objectを含む場合があり、読込時に任意コードを実行し得る。`loadfig()`はこの形式を常に拒否し、自動fallbackや確認付きfallbackも行わない。

信頼できる旧ファイルの一方向変換が必要な場合は、将来、本体とは別配布のdeprecated migration toolとして提供する。本体はdill・pickle・cloudpickleへ依存しない。migration toolはprocess内で最初にdeserializeする直前に任意コード実行の危険を表示し、完全一致する確認文を1回だけ要求する。非対話環境はdefaultで拒否し、自動化には`--allow-arbitrary-code-execution`のような明示的な長いflagを要求する。

確認やsubprocessによってdillが安全になるわけではない。信頼できないファイルは変換せず、必要な場合もnetwork無効・input read-only・専用output directoryだけを書込可能にした使い捨て環境を使う。出力は`.mpl.png`とし、通常の安全な`loadfig()`で再検証する。実装は[Issue #35](https://github.com/y-marui/python-matplotlib-extension/issues/35)で管理する。

この形式は、シリアライズされた Python object を一切 restore しない。canonical JSON と numeric NumPy array だけを使い、allowlist 済みの Matplotlib type だけを復元する。object dtype は拒否し、新しい `Figure` を構築する前に package path・size・version・SHA-256 digest を検証する。旧 object-bearing file は復元せず拒否する。

現在の round-trip 対象は、基本的な `Figure`、`Axes`、`Line2D`、`Text`、`Legend`、scale、locator、formatter。未対応 object は `UnsupportedFigureWarning` とともに skip する。scatter と image の numeric data は `matplotlib_extension.recover_data()` で回収でき、artist coverage の拡張は [Issue #31](https://github.com/y-marui/python-matplotlib-extension/issues/31) で管理する。

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
