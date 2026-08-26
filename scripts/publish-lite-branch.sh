#!/usr/bin/env bash
# scripts/lite-manifest.txt の [include] で選定したファイルから
# lite ブランチ（軽量版 dev-charter）を構築し、必要な場合のみ push する。
#
# 実際の checkout を経由せず git plumbing（hash-object/update-index/
# write-tree/commit-tree）だけでコミットを組み立てる。include ファイルが
# root 直下と topics/ に分散しているため、`git subtree split` のような
# 単一ディレクトリ前提のツールは使えない。
#
# lite の VERSION は full の VERSION と独立させ、include ファイルの内容が
# 実際に変わったときだけ更新する（無関係な full 側の変更で lite 採用先に
# 更新PRが飛ぶノイズを防ぐため）。
#
# Usage:
#   scripts/publish-lite-branch.sh            # 差分があれば origin/lite へ push
#   scripts/publish-lite-branch.sh --dry-run  # 構築結果を表示するだけ。push しない
set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

MANIFEST="scripts/lite-manifest.txt"
REMOTE="${LITE_REMOTE:-origin}"
BRANCH="lite"
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

include_files=$(awk '/^\[include\]/{f=1;next} /^\[exclude\]/{f=0} f' "$MANIFEST" \
  | sed -e 's/#.*//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' | grep -v '^$' | sort)

INDEX_FILE=$(mktemp -u)
LITE_INDEX_MD=$(mktemp)
trap 'rm -f "$INDEX_FILE" "$LITE_INDEX_MD"' EXIT
export GIT_INDEX_FILE="$INDEX_FILE"

while IFS= read -r f; do
  [ -n "$f" ] || continue
  blob=$(git hash-object -w "$f")
  git update-index --add --cacheinfo 100644,"$blob","$f"
done <<< "$include_files"

{
  echo "# Charter Index (lite)"
  echo
  echo "dev-charter lite 版のドキュメント索引。プロジェクト種別を問わず"
  echo "普遍的に価値がある部分だけを収録している。full 版の全体像は"
  echo "https://github.com/y-marui/dev-charter を参照。"
  echo
  echo "## Index"
  echo
  echo "| トピック / キーワード | ファイル |"
  echo "|---|---|"
  while IFS= read -r f; do
    grep -F "\`${f}\`" CHARTER_INDEX.md || true
  done <<< "$include_files"
} > "$LITE_INDEX_MD"
blob=$(git hash-object -w "$LITE_INDEX_MD")
git update-index --add --cacheinfo 100644,"$blob",CHARTER_INDEX.md

content_tree=$(git write-tree)

parent_sha=$(git ls-remote "$REMOTE" "refs/heads/${BRANCH}" 2>/dev/null | cut -f1 || true)
if [ -n "$parent_sha" ]; then
  parent_tree=$(git rev-parse "${parent_sha}^{tree}")
  # VERSION は毎回値が変わるため、比較対象から除外して純粋な内容差分だけを見る
  parent_content_tree=$(git ls-tree "$parent_tree" | grep -v $'\tVERSION$' | git mktree)
  if [ "$parent_content_tree" = "$content_tree" ]; then
    echo "lite: include ファイルに変更なし。publish をスキップします。"
    exit 0
  fi
fi

version=$(date -u +%Y-%m-%dT%HZ)
version_blob=$(printf '%s\n' "$version" | git hash-object -w --stdin)
git update-index --add --cacheinfo 100644,"$version_blob",VERSION
final_tree=$(git write-tree)

if [ -n "$parent_sha" ]; then
  commit=$(git commit-tree "$final_tree" -p "$parent_sha" -m "chore: publish lite ${version}")
else
  commit=$(git commit-tree "$final_tree" -m "chore: publish lite ${version}")
fi

if [ "$DRY_RUN" = "1" ]; then
  echo "dry-run: ${commit}（push しません）"
  git show --stat "$commit"
  exit 0
fi

git push "$REMOTE" "${commit}:refs/heads/${BRANCH}"
echo "lite branch updated: ${commit} (VERSION ${version})"
