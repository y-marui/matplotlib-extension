# AI_CONTEXT.md

## Project Overview

matplotlib の拡張ライブラリ。data-only canonical package を埋め込んだ editable PDF・PNG・SVG・OLE の安全な保存・復元機能と、軸フォーマッティング・LaTeX ラベルユーティリティを提供する。

「editable」は、保存した画像ファイルまたはOLE objectを別のPython process / consoleで`Figure`へrestoreし、Matplotlib APIで追加編集できることを意味する。PowerPoint内の編集UIは提供しない。OLEはcanonical packageの受動的なデータ容器として扱う。

OLE/presentation連携では、ユーザーがPowerPoint上で目的のobjectを選択し、Windowsでnative `.mplpkg`またはOLE CFB `.bin`として保存・exportしてPythonの`loadfig()` / `extract_package()`へ渡す。Python側でPPTXを走査して対象objectを推測しない。汎用Packageの操作が不十分な場合は抽出専用verb/adapterを追加できるが、restore・編集・埋め込みコード実行は行わない。

- **言語:** Python 3.11+
- **パッケージマネージャ:** uv（`uv sync` / `uv add`）
- **主要依存:** matplotlib, numpy, pypdf, olefile
- **ツール:** ruff（lint/format）, mypy（型チェック）, pytest
- **主要ディレクトリ:**
  - `matplotlib_extension/` — ライブラリ本体（pyplot.py, label_string.py, *.mplstyle）
  - `tests/` — pytest テスト
  - `docs/dev-charter/` — 開発憲章（git subtree）

## Applied Charter Principles

憲章参照: docs/dev-charter/CHARTER_INDEX.md でトピックを特定してから該当ファイルのみ読む

- **コミット形式:** Conventional Commits（feat/fix/chore/docs/refactor）
- **セキュリティ:** pre-commit（gitleaks, detect-private-key, detect-dotenv, check-local-charter-version, check-markdown-heading-language）CI で強制
- **コードの原則:** YAGNI・DRY（3回目で検討）・変更範囲最小限
- **コメント:** 「なぜそうするか」のみ。コードから自明な処理には書かない。
- **OSS 言語ポリシー:** 公開面（README・docstring・コミット）は英語、内部コメントは日本語 OK
- **dev-charter の変更:** `docs/dev-charter/` 配下のファイルを直接編集しない。変更が必要な場合は dev-charter リポジトリに Issue を立て、`git subtree pull` でアップデートを取り込む

## Document Sync Rule

仕様・ルール・構成に変更が生じたとき、変更と同じ作業内で関連ドキュメントを更新する。
対象は docs/ 内のファイルに限らず、AI_CONTEXT.md・README.md 等のルートファイルも含む。

## Project-Specific Rules

- 依存管理は uv のみ（poetry は使わない）
- 型注釈は公開 API に必須
- live Python object serializer、`eval` / `exec`、file-selected import/class construction は editable file の保存・読込に使用しない
- NumPy array は `allow_pickle=False`、object/structured dtype 禁止
- 旧 object-bearing `.plt.pdf` の自動 restore は禁止
- format/security の正本は `docs/EDITABLE_FORMAT.md` と `SECURITY.md`

## AI Tool Assignments

- **使用ツール**：Claude Code、GitHub Copilot、Gemini CLI
- **標準担当の正本**：`docs/dev-charter/AI_COLLABORATION_RULES.md` の「AI Tool Responsibilities」と「Rules for Multi-AI Usage」
- **プロジェクト固有の上書き**：なし

## Prohibited Actions

- シークレット・認証情報のコミット
- ハードコードされたローカルパスの使用
- `main` への直接 push（PR 経由のみ）
