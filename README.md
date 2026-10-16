# Tuned Team

A multi-agent dev environment for Claude Code. One command opens a team of
Claude Code sessions in tmux, one tab each:

- **director**: the only one you talk to. Turns what you want into tasks.
- **managers**: each looks after a group of specialists and hands them tasks.
  Managers solve problems among themselves; the director gets only what you must see.
- **specialists**: do the work (code, design, copy, research), each on its own branch.

## Install

```sh
brew install tmux
git clone git@github.com:zdzislawbela/tuned-team.git ~/tools/tuned-team
~/tools/tuned-team/install.sh
```

Works in any terminal (Ghostty, iTerm2, Terminal). Needs `tmux`, `claude`, `python3`, `git`.

## Use

In a project folder:

```sh
tuned-team
```

It asks for the language, the number of specialists and managers, the model, who
decides on push and release, and whether to read notifications or only questions
aloud. Then the tabs open and you talk to the director (tab 0).

tmux keys: `Ctrl-b w` all windows, `Ctrl-b 0` the director, `Ctrl-b n` / `p` next / previous,
`Ctrl-b d` detach (the team keeps running; `tuned-team` again attaches).

Every window shows one plain status line: `repo (branch) | model | ctx %`.

## Commands the agents use

| Command | What it does |
|---|---|
| `tuned-team status` | team table: who works, who waits for the owner, context, ETA |
| `tuned-team report start\|eta\|done` | a specialist writes its state into the table |
| `tuned-team check [--timeout S] CMD` | runs the full check once one of the 2 machine slots is free (exit 3: no slot, nothing ran) |
| `tuned-team done` | task merged, nothing open: the window restarts with a fresh context |
| `tuned-team add manager\|specialist` | opens one more window |
| `tuned-team restart NAME\|self` | restarts a window with a fresh context |
| `tuned-team close-all [--force]` | lists unmerged work; with none (or `--force`) closes every window |

`statusline` and `speak` are Claude Code hooks; they are passed to each window with
`claude --settings`, so your own `settings.json` stays untouched.

## How it works

- Roles: `roles/team.md` (rules for everyone) plus `roles/director.md`, `manager.md` or
  `specialist.md`, passed with `--append-system-prompt-file`.
- Specialist N belongs to manager `((N - 1) % managers) + 1`.
- State per team: `~/.tuned-team/teams/<repo>/` (answers, reports, generated prompts and settings).
- tmux runs its own server (`tmux -L tuned`) with `tmux.conf` from this repo, so your own tmux is untouched.
- Every window starts in auto mode. Speaking aloud uses macOS `say`.

## Limits

One laptop runs at most 2 full checks and 4 dev servers at a time, whatever the team size.
Each window is a full Claude Code session: many windows use memory and your plan's usage limits.
