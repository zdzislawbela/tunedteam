# Tuned Team, inside out

What tunedteam does under the hood, and why. The README says how to use it; this says
what each piece is for. Most of it is about one thing: a team of Claude Code sessions
burns context and plan limits fast, so every trick here either keeps context small,
keeps sessions from waking each other, or keeps them from fighting over the machine.

## Isn't this just 8 terminals?

Open 8 terminals with `claude` in each and you get 8 sessions. Then you are the director:

- you split the work, type each task 8 times, and keep in your head who does what;
- you check each tab to see who is done, who is stuck, who waits for a permission click;
- two sessions edit the same file, or work in the same checkout and break each other's build;
- 8 test runs start at once and the machine stops;
- every long conversation gets slower and more expensive until you remember to `/clear`, and
  then it forgets what it was doing;
- sessions that message each other wake each other up for "ok, thanks";
- an agent picks up the paid API key from `.env` and you pay twice for the plan;
- the second project's `director` gets messages meant for the first one.

tunedteam is the rules and plumbing around those sessions so none of that is your job: one
session you talk to, specialists each in their own worktree, a status table that costs no
tokens, a queue for heavy checks, fresh context per task, and addresses that can't mix up
teams. The rest of this page is how each of those works.

## Shape of the team

- **Two levels, no middle managers.** The owner talks to the director, the director hands
  tasks to specialists. An earlier version had a manager layer in between: it cost 2-3x the
  tokens per commit for about 14% more commits. Following Anthropic's "Building effective
  agents": start simple, add a layer only when it measurably helps.
- **One task per specialist, one branch per task, every open task on its own files.**
  Specialists working in the same file was the most common source of wasted rounds.
- **The director never writes code.** Its context stays on the conversation with the owner
  and the state of the team, so it lasts longer.

## Context

- **Fresh context per task.** `tunedteam done` refuses until the task is merged and its
  worktree and branch are gone, then restarts the window. The next task starts from zero
  instead of on top of the last one.
- **Start over before context gets expensive.** Every tool call resends the whole
  conversation (mostly from cache, but still). A specialist hands its state to the director
  and restarts at about 30%; the director writes a handover file and restarts at about 20%.
  Percentages are counted against the model's real window (Opus 1M), not a guess.
- **Progress goes to a table, not to messages.** Every message wakes the receiver and costs
  it a full turn over its whole context. `tunedteam report start|eta|done` writes a line to
  `~/.tunedteam/teams/<team>/reports.json` instead, and nobody pays for reading it until they
  run `tunedteam status`.
- **`tunedteam status` costs no tokens.** It reads Claude Code's own session files and
  transcripts on disk: who is busy, who waits on a permission prompt (the last tool call
  without a result), context, RAM. No agent is asked anything.
- **Short messages, in English.** Telegraphic and imperative, no greetings, no
  acknowledgements, no progress notes. The director answers the owner in the owner's
  language; agents write to each other in English, which is cheaper and less ambiguous.
- **Small, per-window prompts.** Each window gets `roles/team.md` + its own role + only the
  lines that apply to it (team, addresses, control mode, database rule; reading-aloud rules
  only for the director), through `--append-system-prompt-file`. Changes to `roles/*.md`
  reach a window on its next restart.

## Addresses and teams

- **Every agent has a unique name on the Mac: `<team>.<window>`**, e.g.
  `myapp.specialist-3`, passed as `claude -n`. Claude Code's SendMessage addresses
  sessions by name across the whole machine, so two teams with a `director` each would
  otherwise mix. (`@` can't be used: SendMessage reserves it.)
- **The team is named after the project folder**; another folder with the same name gets
  `-2`. `tunedteam teams` lists the running teams; only directors talk across teams, and only
  when the owner asks.
- **Tabs keep short names** (`director`, `specialist-1`). Commands take these names; the team
  name is in the window title.

## tmux

- **Its own tmux server and config** (`tmux -L tuned -f tunedteam/tmux.conf`), so your own
  tmux sessions and `~/.tmux.conf` are never touched. Tests run on yet another socket.
- **Windows keep their names** (`allow-rename off`, `automatic-rename off`): the names are the
  addresses commands use.
- **iTerm2:** attaches with `tmux -CC`, so every agent is a native iTerm2 tab (a list on the
  left if you like). Only when iTerm2 opens tmux windows as tabs: with its default it opens one
  window per agent. The first start asks once and writes the setting; that start still uses
  the plain attach, because a running iTerm2 may not have read it yet.
- **Windows start 0.3 s apart.** A dozen Claude Code sessions starting in the same second
  choke the machine.
- **Extra tabs:** `lazygit` if installed, your own tabs from `~/.tunedteam/tabs` (typed into a
  shell, so aliases work), and `shell` last: a plain terminal for long or interactive commands.
  Short commands from the director can also go into its own window with `!`.

## Accounts and money

- **Accounts are config folders.** `~/.claude`, every `~/.claude-*`, and your own
  `CLAUDE_CONFIG_DIR`. tunedteam asks which one, logs it in before any window opens, and
  passes it to every window.
- **The tmux server remembers the environment of the shell that started it**, possibly the
  other account. So when no account folder is set, windows start with `CLAUDE_CONFIG_DIR`
  explicitly removed.
- **On a subscription, windows start without `ANTHROPIC_API_KEY`**, so Claude Code uses the
  plan and the agents' own scripts can't pick the paid key up. Without a subscription,
  tunedteam says at start where the key would come from (environment, `.env*`) and that it
  costs money. Agents run their own AI work (tests, scoring) through `claude -p` or subagents.

## Sharing one machine

- **Full checks through `tunedteam check`:** at most 2 at a time (`TUNED_CHECK_MAX`). The
  rest wait; with `--timeout` they give up with exit code 3 and the branch stays unmerged.
- **At most 4 dev servers, browsers headless and closed after use.** These are rules in
  the role, not enforced in code.
- **Worktrees next to the repo in `<repo>-worktrees.noindex/`.** Spotlight skips `.noindex`
  folders, so a dozen copies of the repo don't get indexed. `node_modules` is copied with
  `cp -c` (an APFS clone: seconds, no extra disk), `.env.local` is copied.

## Safety

- **Push, release and deploy follow the control mode** chosen at start: the owner decides
  (default), or the team decides. When the team decides, the director releases at most once an
  hour, all merged commits together: every release is a deploy, and a release per merge filled
  the hosting's deployment storage. Permission prompts always go to the owner, in the window
  that asks.
- **Database writes through MCP:** in "ask" mode every tool that writes, migrates, deploys
  or deletes is on Claude Code's ask list, which holds in auto mode too. Schema changes are
  saved as migration files in the repo either way.
- **`close-all` lists unmerged branches, worktrees and uncommitted files** and closes
  nothing without `--force`, which agents use only after the owner's yes.
- **Recurring tasks** (cron, `/loop`) only on the owner's request, always with an end date.

## Small things

- **Status line:** `repo (branch) | model | ctx %` from one git call, with the repo of the main
  checkout even inside a worktree.
- **Reading aloud:** the director ends replies with `<speak>…</speak>`; a Stop hook reads only
  that part with macOS `say`, in a Polish voice when the text has Polish letters.
- **Update check:** once a day against the GitHub tags, silent when offline.
