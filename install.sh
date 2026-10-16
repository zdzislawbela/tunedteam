#!/bin/sh
# Installs Tuned Team: links bin/tuned-team into ~/bin, so `git pull` updates it.
set -e
cd "$(dirname "$0")"
for cmd in tmux claude python3 git; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Missing '$cmd'. Install it first (tmux: brew install tmux)."; exit 1; }
done
mkdir -p "$HOME/bin"
# Links from older versions (tuned-agents, tuned-report, ...) point into this repo at files that are gone.
for old in "$HOME"/bin/tuned-*; do
  if [ -L "$old" ] && [ ! -e "$old" ]; then
    case "$(readlink "$old")" in "$PWD"/*) rm "$old";; esac
  fi
done
ln -sf "$PWD/bin/tuned-team" "$HOME/bin/tuned-team"
case ":$PATH:" in *":$HOME/bin:"*) ;; *) echo "Add ~/bin to PATH (in ~/.zshrc: export PATH=\"\$HOME/bin:\$PATH\")." ;; esac
echo "Done. In a project folder run: tuned-team"
