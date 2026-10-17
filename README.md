# Tuned Team

A multi-agent dev environment for Claude Code. One command opens a team of
Claude Code sessions in tmux, one tab each:

- **director**: the only one you talk to. Turns what you want into tasks, hands them to
  the specialists and watches them.
- **specialists**: do the work (code, design, copy, research), each on its own branch.

Two levels on purpose: following Anthropic's "Building effective agents" (start simple,
add a layer only when it measurably helps), and an earlier measurement where a middle
layer of managers cost 2-3x the tokens per commit for about 14% more commits.

## Install

```sh
brew install zdzislawbela/tap/tunedteam
```

Homebrew brings tmux along. Claude Code is installed separately
(`brew install --cask claude-code`). Update with `brew upgrade tunedteam`. Works in any
terminal (Ghostty, iTerm2, Terminal).

New to tmux? Use **iTerm2** (`brew install --cask iterm2`): every agent is a normal tab you
click, listed on the left, and no tmux keys to learn. The first start in iTerm2 offers this
layout.

To work on Tuned Team itself instead: clone this repo and run `./install.sh`, which links
`bin/tunedteam` into `~/bin` (needs `tmux`, `claude`, `python3`, `git`).

## Two Claude accounts (e.g. work and private)

Claude Code keeps an account in a config folder: `~/.claude` by default, any other
folder through `CLAUDE_CONFIG_DIR`. One-time setup of a second account:

```sh
CLAUDE_CONFIG_DIR=~/.claude-priv claude
```

Log in inside it (`/login`, pick the private account), then exit. From then on
`tunedteam` lists both accounts at start with their email and plan, and remembers
your choice per project. Name extra folders `~/.claude-<something>` and they are found
on their own.

Optional, so plain `claude` in a terminal also picks the right account by folder
(in `~/.zshrc`):

```sh
autoload -U add-zsh-hook
_claude_profile() {
  if [[ $PWD == $HOME/repos/priv* ]]; then export CLAUDE_CONFIG_DIR=$HOME/.claude-priv
  else unset CLAUDE_CONFIG_DIR; fi
}
add-zsh-hook chpwd _claude_profile; _claude_profile
```

## Database and deploy tools (MCP)

At start you choose how agents may use database and deploy tools from your MCP servers
(Supabase, Neon, Vercel and others):

- **ask** (default, the safe choice): agents read freely; every tool that writes, migrates,
  deploys or deletes (`execute_*`, `apply_*`, `run_sql*`, `deploy_*`, `delete_*`, `drop_*`,
  `insert_*`, branch merge/reset/rebase, on any server) is on Claude Code's ask list, so you
  approve each call in that window. This holds in auto mode too. Agents also save the change
  as a file in the repo and show you the exact SQL first.
- **full**: agents really do everything on their own, without asking: writes, migrations,
  deploys, deletes. Your job is to point the team at **staging**, never production: the
  database and deploy target the team works on is treated as staging, whatever its name.
  Before SQL that changes data, agents take a backup (or write down the SQL that restores
  it); after it, they run the tests. At start, picking full shows this and asks you to confirm.

If your MCP server has a read-only mode (Supabase does), connect it read-only for the team.

## Paid API key vs subscription

With `ANTHROPIC_API_KEY` in the environment, Claude Code may bill the API instead of
your Max or Pro plan. On an account with a subscription, every Tuned Team window starts
without that variable, so the windows run on the plan and the agents' commands cannot
pick the key up. `tunedteam` also warns at start when it finds the key in your shell or
in the project's `.env*` files, and the team rules tell agents to run their own AI work
(tests, scoring, simulations) through `claude -p` or subagents, and the paid API only with
your yes. Project scripts that read the key from `.env.local` themselves are outside
Tuned Team's reach: block them in the project (see your AGENTS.md).

## Use

Anywhere:

```sh
tunedteam
```

The first question is the project folder: the current one (if it is a git repo), then
projects you ran a team in, then repos in `~/repos`, or any folder you type.

Every question is a list you pick from with the arrow keys and Enter. It lists your Claude accounts (`~/.claude`, every `~/.claude-*` folder and your own
`CLAUDE_CONFIG_DIR`, e.g. work and private), asks which one to use (with one account it
skips the question) and logs it in first if needed, so no window opens on a
logged-out account. Then it asks for the number of specialists, the model, who decides on push
and release, and whether to read notifications or only questions aloud. The director
answers in the language you write in; agents write to each other in English. Then the tabs open and you talk to the director (tab 0). The last tab, `shell · last resort`,
is a plain terminal for you in the project folder, for when you have to type something yourself.
With [lazygit](https://github.com/jesseduffield/lazygit) installed, the tab before it shows the repo in lazygit.
Tabs of your own go in `~/.tunedteam/tabs`, one per line as `name: command` (e.g. `awake: caffeinate -d`):
each opens as a shell with the command typed in, so your aliases work.
All names are in English (`director`, `specialist-N`, `shell`): they are the tab names and
the names commands take. Agents write to each other at `<team>.<name>` (e.g. `myapp.director`),
so teams in different projects never mix; `tunedteam teams` lists the running teams. The team
is named after the project folder; a second project with the same folder name gets `-2`.

Tabs can be clicked. tmux keys: `Ctrl-b w` all windows, `Ctrl-b c` one more terminal of your own, `Ctrl-b 0` the director, `Ctrl-b n` / `p` next / previous,
`Ctrl-b d` detach (the team keeps running; `tunedteam` again attaches).

In **iTerm2** the first start asks for the layout: the tunedteam setup (every agent a native
iTerm2 tab, listed on the left), tabs on top, or leave iTerm2 as it is. The first two change
iTerm2's settings (tmux windows open as tabs, tab bar location, the tmux gateway tab hidden) and
work from the next start; "leave it" is remembered and not asked again. Other terminals show
the tmux tab bar at the bottom.

Every window shows the same right half: `repo version branch │ model │ ctx % │ tunedteam version`,
the context turning yellow and red as the window nears its restart point (director ~20%,
specialists ~30%). On the left a specialist shows its name and task. The director has it as the
top line, then how the team is doing (`● 6 working  ○ 3 free`, plus `▲ 2 WAITING FOR YOU` when
anyone waits on you), redrawn every 15 s; below it a line about the Mac: a grey `● Mac ok`, or only what needs you,
with what to do (`▲ 5 dev servers (limit 4): stop 1`, `▲ RAM 44/48 GB, swap 3.2 GB: close a
window`, `▲ CPU 160%`), measured at most every 10 s; and at the bottom what you can say to it
("tasks", "status", "add a specialist", "release", "close the team"). Put a command in `~/.tunedteam/statusline` to show its first
line there too, e.g. deploys on Vercel: it runs in the project folder, in the background, every
5 minutes.

## Rules

The full rules are in [roles/](roles/): `team.md` for everyone, `director.md`, `specialist.md`.
Some are enforced by tunedteam, the rest are instructions the agents follow:

| Rule | Enforced by |
|---|---|
| a task ends merged, with its worktree and branch gone, before the window starts fresh | `tunedteam done` refuses until then |
| at most 2 full checks at a time | `tunedteam check` waits or exits 3 |
| database writes, migrations and deploys through MCP need your yes ("ask" mode) | Claude Code's ask list |
| nothing closes while work is unmerged | `close-all` needs `--force` |
| a window starts fresh past its restart point (director ~20%, specialists ~30%) | a hook tells the window when it passes it (the model can't see its own status line); the restart itself is done by the agent |
| one task per specialist, one branch per task, every task on its own files | the role |
| at most 4 dev servers, headless browsers | the role |
| when the team decides, at most one release an hour | the role (a hard limit belongs in the project's own release script) |
| messages only when the receiver must act, no "ok" or "thanks" | the role |

## Releases

Who pushes and releases is the third question at start: you (the default) or the team. When the
team decides, the director releases at most once an hour, all merged commits together: every
release is a deploy, and a release per merge fills the hosting's deployment storage.

## Scheduled commands

Commands to run every day go to launchd, not to a Claude session: no tokens, and they keep
running with the team closed or the Mac restarted. The first start offers to update Claude Code
every morning when it came from Homebrew.

```sh
tunedteam schedule                                        # list: when, on/off, last run, exit code
tunedteam schedule add claude-update 07:00 brew upgrade --cask claude-code
tunedteam schedule run|log|off|on|rm claude-update
```

Each runs in a login shell (your PATH), its output in `~/.tunedteam/schedule/NAME.log`. The
director uses the same command when you ask for something recurring.

## Commands the agents use

| Command | What it does |
|---|---|
| `tunedteam --version` | the installed version (in a git checkout also commits past the release) |
| `tunedteam tasks` | the tasks in progress, with the specialists, branch, ETA and state of each |
| `tunedteam schedule …` | commands run every day by launchd: list, add, run, log, off, on, rm |
| `tunedteam --inside-out` | how it works under the hood and why, also in [INSIDE-OUT.md](INSIDE-OUT.md) |
| `tunedteam status` | team table: who works, who waits for the owner, context, RAM, ETA |
| `tunedteam report start\|eta\|done` | a specialist writes its state into the table |
| `tunedteam worktree BRANCH [BASE]` | new branch + worktree in `<repo>-worktrees.noindex/` next to the repo (Spotlight skips `.noindex` folders), node_modules cloned, .env.local copied |
| `tunedteam check [--timeout S] CMD` | runs the full check once one of the 2 machine slots is free (exit 3: no slot, nothing ran) |
| `tunedteam done` | task merged: the window restarts with a fresh context; refuses while the task's worktree or branch is still there |
| `tunedteam add` | opens one more specialist |
| `tunedteam restart NAME\|self` | restarts a window with a fresh context |
| `tunedteam close-all [--force]` | lists unmerged work; with none (or `--force`) closes every window |

`statusline` and `speak` are Claude Code hooks; they are passed to each window with
`claude --settings`, so your own `settings.json` stays untouched.

## Compared with other tools

How Tuned Team differs from tools people use to run many coding agents. Mostly an
opinion from reading the tools' pages and reviews (October 2026), not a benchmark.
Only the Tuned Team and VS Code memory figures were measured, on a 48 GB M4 Pro.

| Tool | What it is | Who splits the work | Each task isolated | 16 agents on one laptop | Notes |
|---|---|---|---|---|---|
| **Tuned Team** | terminal (tmux), one command | the agents: the director hands out and checks the work; you talk only to the director | git worktree per task | yes: a fresh session uses ~370 MB (measured), so 16 are roughly 6-10 GB; should fit a 16 GB MacBook Air, not tested there | roles, quality gate before merge, machine limits (2 checks, 4 dev servers), read-aloud |
| Claude Squad | terminal (tmux) with a session switcher | you: you prompt each agent and review each diff | git worktree per session | likely yes, same tmux model | session manager, no coordination between agents; AGPL-3.0 |
| Claude Code agent teams | built into Claude Code, experimental | a lead agent | worktree support | likely yes, panes need tmux or iTerm2 | off by default; more tokens than subagents |
| VS Code + Claude Code panels | Electron editor | you | your own scripts | **no** in our use: at 8-10 long sessions the window froze (one renderer process at 1.4 GB and 100% of one core, measured) | every panel is drawn by one window process |
| Cursor 3 (Agents Window) | Electron editor (VS Code fork) | you | worktree per agent | up to 8 agents per window (vendor) | same Electron model as VS Code; paid plans |
| OpenAI Codex app | desktop app | you | built-in worktrees | not known | another model and plan |
| Conductor | Mac app | you | worktree per workspace | 5-10 sessions (reviews) | GUI around worktrees: chat, diff, checks, PR |
| workmux, dmux | small terminal tools | you | worktree per task | likely yes | windows and worktrees only |

In short: the window-and-worktree layer is the same everywhere (tmux or an app around
git worktrees). What Tuned Team adds is the coordination: agents hand out and check the
work, so one person can run 16 of them without switching between windows.

## How it works

- Roles: `roles/team.md` (rules for everyone) plus `roles/director.md` or
  `roles/specialist.md`, passed with `--append-system-prompt-file`.
- The director's handover before a fresh start goes to `~/.tunedteam/teams/<repo>/handover.md`.
- State per team: `~/.tunedteam/teams/<repo>/` (answers, reports, generated prompts and settings).
- tmux runs its own server (`tmux -L tuned`) with `tmux.conf` from this repo, so your own tmux is untouched.
- Every window starts in auto mode. Speaking aloud uses macOS `say`, with a Polish voice
for text with Polish letters.

## Limits

One laptop runs at most 2 full checks and 4 dev servers at a time, whatever the team size.
Each window is a full Claude Code session: many windows use memory and your plan's usage limits.

## License

MIT, see [LICENSE](LICENSE).
