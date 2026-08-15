# Matplotlib Extension

> **このファイルは正本（日本語版）です。**
> 英語版（参照）は [README.md](README.md) を参照してください。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/ci.yml/badge.svg)](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/ci.yml)
[![Charter Check](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/dev-charter-check.yml/badge.svg)](https://github.com/y-marui/python-matplotlib-extension/actions/workflows/dev-charter-check.yml)
[![GitHub Sponsors](https://img.shields.io/github/sponsors/y-marui?style=social)](https://github.com/sponsors/y-marui)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-donate-yellow.svg)](https://www.buymeacoffee.com/y.marui)

matplotlib の拡張ライブラリ。図を編集可能な PDF として保存・復元する機能と、軸フォーマッティングユーティリティを提供する。

## Requirements

- Python 3.11+

## Setup

```sh
uv sync
```

## Usage

### Save and Load Figures

matplotlib の図を `.plt.pdf` ファイルとして保存する。PDF に dill オブジェクトを埋め込むことで、図を完全な状態で復元できる。

```python
import matplotlib.pyplot as plt
import matplotlib_extension.pyplot as mplex

fig, ax = plt.subplots()
ax.plot([1, 2, 3], [1, 4, 9])

mplex.savefig(fig, "output.plt.pdf")             # 排他（存在する場合はエラー）
mplex.savefig(fig, "output.plt.pdf", mode="w")   # 上書き（既存ファイルはゴミ箱へ）
mplex.savefig(fig, "output.plt.pdf", mode="a")   # 追記

figs = mplex.loadfig("output.plt.pdf")
figs[0].show()
```

### LabelString

略称キーワードを matplotlib ラベル用の LaTeX 表記に変換する。

```python
from matplotlib_extension.label_string import LabelString

ax.set_xlabel(repr(LabelString("alpha vs para")))
# → "$\alpha$ vs $\parallel$"
```

対応キーワード: `alpha`, `beta`, `gamma`, `para`, `perp`

### Adjust Locator

データ範囲に合わせて主・補助目盛りを自動調整する。

```python
from matplotlib_extension.pyplot import adjust_locator

adjust_locator(ax, units=(0.5, 10), subunits=(0.1, 2))
```

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
