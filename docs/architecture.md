# Tuned Team architecture

A technical map of what runs on your machine. [INSIDE-OUT.md](../INSIDE-OUT.md) explains why each piece
exists; the [README](../README.md) explains how to use it.

Tuned Team is one Python script that starts many separate Claude Code processes in one tmux session. Each
agent has its own window. Roles and `tunedteam` commands organize how they talk and how they use git.

The script is not a background service. It runs for a moment when you type a command, or when an agent or a
Claude Code hook calls it, and then exits. tmux and the `claude` processes are what keep running.

## Terms

| Term | Meaning |
|---|---|
| process | A running program with its own PID and a parent process. Signals such as 15 (terminate) and 9 (kill) are sent to processes. |
| terminal | The app that shows text and passes your keys on, such as iTerm2. It does not run your commands itself. |
| shell | The program that reads commands and runs them, such as `zsh`. |
| tmux | A program that keeps terminal programs running independently of the terminal app. It has a server and clients. |
| tmux server | A background process and the parent of the programs in its windows. |
| tmux client | The process that connects a terminal to the server. When it detaches, the server and windows keep running. |
| socket | The file a client uses to reach a server. `-L tuned` selects Tuned Team's own server, separate from your own tmux. |
| session | A named group of windows. Tuned Team creates one session per team. |
| window | One screen in a session, like a browser tab. With `tmux -CC`, iTerm2 shows each window as a native tab. |
| pane | A rectangle in a window where a program runs. A window normally has one. |
| agent | One `claude` process in a pane, with its own conversation context, role and permissions. |
| worktree | An extra working folder of the same git repo, on its own branch, so agents do not overwrite each other's files. |

## What runs

```text
macOS
├── iTerm2 or another terminal
│   └── tmux client (tmux -CC in iTerm2) ──┐
├── launchd: commands from `tunedteam schedule`
└── tmux server (socket "tuned")  <────────┘
    ├── session "myapp"
    │   ├── window director       claude on Opus, talks to you
    │   ├── window specialist-1   claude
    │   ├── ...
    │   ├── window specialist-N   claude
    │   ├── window lazygit        if installed
    │   ├── your tabs             from ~/.tunedteam/tabs
    │   └── window shell          a plain shell
    └── session "other-project"   another team on the same server
```

The parent of each `claude` process is the tmux server, not the terminal app.

## Starting a team

1. `tunedteam` asks for the team's settings: specialists, their model, who controls releases, database
   rights, reading aloud, and what to do when idle.
2. It writes them to `~/.tunedteam/teams/<team>/config.json`.
3. It builds a prompt from the role files and a Claude Code settings file for each agent.
4. It calls `tmux new-session` for the director and `tmux new-window` for every other window.
5. It attaches your terminal. In iTerm2 this uses `tmux -CC`, once iTerm2 opens tmux windows as tabs.

One agent starts roughly like this, with paths shortened:

```sh
TUNED_TEAM=myapp TUNED_NAME=specialist-3 \
claude -n myapp.specialist-3 \
  --model <model> \
  --permission-mode auto \
  --settings .../settings/specialist-3.json \
  --append-system-prompt-file .../prompts/specialist-3.md \
  --add-dir <connected repo>
```

`TUNED_TEAM` and `TUNED_NAME` tell `tunedteam` commands which window called them. On a subscription the start
also removes `ANTHROPIC_API_KEY`, so windows use the plan.

## Parts

| Part | What it does |
|---|---|
| `bin/tunedteam` | All the logic: start, status, restart, worktrees, checks, hooks and the status line. |
| `tmux.conf` | Settings of the `tuned` server: tab labels, mouse, history, dead windows and their log. |
| `roles/team.md` | Rules for every agent. |
| `roles/director.md` | The director's instructions: hand out tasks and talk to you. |
| `roles/specialist.md` | A specialist's instructions: own branch and worktree, tests, merge. |
| `~/.tunedteam/teams/<team>/` | Team state in files: `config.json`, `reports.json`, `worktrees.json`, `findings.json`, `handover.md`, `prompts/`, `settings/`. |
| Claude Code | The agent itself. Tuned Team starts it with flags, hooks and a status line, and does not change it. |
| launchd | Runs `tunedteam schedule` commands at a set time, without using tokens. |

## How agents work together

| Need | Mechanism |
|---|---|
| Messages | Claude Code's `SendMessage`, addressed `team.window`, such as `myapp.specialist-3`. |
| Task state | `tunedteam report` writes to `reports.json`; `tunedteam status` shows the table. |
| Separate work | `tunedteam worktree` creates a branch and a folder in `<repo>-worktrees.noindex/`, which Spotlight skips. |
| Worktree cleanup | `tunedteam worktrees` lists state and owner. `prune` removes only merged, clean and unused ones. `done` tracks every worktree the window made. |
| Dependencies | `node_modules` is an APFS clone (`cp -cR`); `.env.local` is a symlink to the main checkout's. |
| Heavy checks | `tunedteam check` runs at most 2 full checks at a time. |
| Dev servers | A limit of 4: a rule for agents and an alarm on the director's status line. It does not block a fifth. |
| Director's memory | Before a restart the director writes `handover.md`, and reads it first afterwards. |

A `PostToolUse` hook runs `tunedteam ctx-check` after every tool call. It logs the call and warns the window
when its context or the plan's limit passes a threshold. An agent cannot see its own status line, so this is
how it finds out.

## What fails together

| Event | Result |
|---|---|
| A `claude` process is killed or exits with an error | The rest keeps running. The window stays open with its exit code, and a line goes to `~/.tunedteam/pane-deaths.log`. |
| A program exits with code 0 | Its window closes, with no log line. |
| The last window of a session closes | The session ends. The server keeps running if it has other sessions. |
| The client detaches | Agents keep working. `tunedteam` attaches the terminal again. |
| The tmux server dies | Every window of every team is gone. |
| The Mac restarts | All processes are gone. State files, branches and worktrees stay. |
| `tunedteam restart <window>` | `respawn-pane -k` kills the window's program and starts a new `claude` with an empty context. |

Closing an iTerm2 tab in `tmux -CC` mode can differ from detaching and may close the tmux window. This has not
been tested.
