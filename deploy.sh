#!/usr/bin/env bash
# 능놀스테이 사이트 배포: 빌드 → 푸시 → GitHub Pages(/docs) 활성화 → 빌드 완료 대기
# (루트의 기존 1페이지 SPA는 보존되고, docs/ 의 다국어 SEO 사이트가 배포됩니다)
set -euo pipefail
OWNER="neungnolstay-spec"
REPO="neungnolstay"
BRANCH="main"

cd "$(dirname "$0")"

python3 i18n_build/build.py

git add -A
git diff --cached --quiet || git commit -m "사이트 갱신: $(date +%Y-%m-%d\ %H:%M)"
git branch -M "$BRANCH"
git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$OWNER/$REPO.git"
git push -u origin "$BRANCH"

# Pages 활성화 (이미 켜져 있으면 409 → 무시)
gh api -X POST "repos/$OWNER/$REPO/pages" \
  -f "source[branch]=$BRANCH" -f "source[path]=/docs" >/dev/null 2>&1 \
  && echo "pages: enabled" \
  || gh api -X PUT "repos/$OWNER/$REPO/pages" \
       -f "source[branch]=$BRANCH" -f "source[path]=/docs" >/dev/null 2>&1 \
       && echo "pages: updated" || echo "pages: unchanged"

for i in $(seq 1 24); do
  STATUS=$(gh api "repos/$OWNER/$REPO/pages/builds/latest" --jq '.status' 2>/dev/null || echo "pending")
  echo "build: $STATUS"
  [ "$STATUS" = "built" ] && break
  sleep 5
done
echo "https://$OWNER.github.io/$REPO/"
echo "  한국어: https://$OWNER.github.io/$REPO/ko/"
