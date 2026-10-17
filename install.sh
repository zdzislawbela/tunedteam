#!/bin/sh
# Installs Tuned Team: links bin/tunedteam into ~/bin, so `git pull` updates it.
set -e
cd "$(dirname "$0")"
for cmd in tmux claude python3 git; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Missing '$cmd'. Install it first (tmux: brew install tmux)."; exit 1; }
done
mkdir -p "$HOME/bin"
# Links left by older versions (tuned-team, tuned-agents, tuned-report, ...) now point at files that are gone.
for old in "$HOME"/bin/tuned-*; do
  [ -L "$old" ] && [ ! -e "$old" ] && rm "$old"
done
ln -sf "$PWD/bin/tunedteam" "$HOME/bin/tunedteam"
case ":$PATH:" in *":$HOME/bin:"*) ;; *) echo "Add ~/bin to PATH (in ~/.zshrc: export PATH=\"\$HOME/bin:\$PATH\")." ;; esac
echo "Done. In a project folder run: tunedteam"
