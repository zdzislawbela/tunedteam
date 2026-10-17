#!/bin/sh
# Publishes a Tuned Team version for Homebrew: pushes main, tags vX.Y.Z, then points the
# formula in zdzislawbela/homebrew-tap (~/repos/priv/homebrew-tap) at the new tag and pushes it
# (creating the tap repo on GitHub the first time).
#   sh release.sh 0.2.0
set -e
v=${1:?usage: sh release.sh 0.2.0}
here=$(cd "$(dirname "$0")" && pwd)
tap=${TUNED_TAP_DIR:-$HOME/repos/priv/homebrew-tap}

# The version the program reports (tunedteam --version, start screen).
if [ "$(cat "$here/VERSION" 2>/dev/null)" != "$v" ]; then
  echo "$v" > "$here/VERSION"
  git -C "$here" commit -q -m "Release $v" -- VERSION
fi
git -C "$here" push origin main
if git -C "$here" rev-parse -q --verify "refs/tags/v$v" >/dev/null; then
  echo "Tag v$v already exists, using it."
else
  git -C "$here" tag "v$v"
fi
git -C "$here" push origin "v$v"

url="https://github.com/zdzislawbela/tunedteam/archive/refs/tags/v$v.tar.gz"
sha=$(curl -fsSL "$url" | shasum -a 256 | cut -d' ' -f1)
sed -i '' -e "s|^  url \".*\"|  url \"$url\"|" -e "s|^  sha256 \".*\"|  sha256 \"$sha\"|" "$tap/Formula/tunedteam.rb"
git -C "$tap" add -A
git -C "$tap" commit -q -m "tunedteam $v"
if git -C "$tap" remote get-url origin >/dev/null 2>&1; then
  git -C "$tap" push origin main
else
  gh repo create zdzislawbela/homebrew-tap --public --source "$tap" --push --description "Homebrew formulas"
fi
echo "Released tunedteam $v: brew install zdzislawbela/tap/tunedteam"
