# AI_CONTEXT.md

## Project Overview

matplotlib の拡張ライブラリ。図を dill オブジェクト付きの PDF（`.plt.pdf`）として保存・読み込みする機能と、軸フォーマッティング・LaTeX ラベルユーティリティを提供する。

- **言語:** Python 3.11+
- **パッケージマネージャ:** uv（`uv sync` / `uv add`）
- **主要依存:** matplotlib, dill, pymupdf, pypdf, send2trash
- **ツール:** ruff（lint/format）, mypy（型チェック）, pytest
- **主要ディレクトリ:**
  - `matplotlib_extension/` — ライブラリ本体（pyplot.py, label_string.py, *.mplstyle）
  - `tests/` — pytest テスト
  - `docs/dev-charter/` — 開発憲章（git subtree）

## Applied Charter Principles

憲章参照: docs/dev-charter/CHARTER_INDEX.md でトピックを特定してから該当ファイルのみ読む

- **コミット形式:** Conventional Commits（feat/fix/chore/docs/refactor）
- **セキュリティ:** pre-commit（gitleaks, detect-private-key, detect-dotenv）CI で強制
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

## AI Tool Assignments

- **Claude Code:** 機能実装・リファクタリング・CI 設計
- **GitHub Copilot:** 補完・細かな修正

## Prohibited Actions

- シークレット・認証情報のコミット
- ハードコードされたローカルパスの使用
- `main` への直接 push（PR 経由のみ）
