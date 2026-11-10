# Changelog

What each version of Tuned Team brings. Update with `brew upgrade tunedteam`.

## 0.2.39 (2026-11-10)

- Fable for one task. `tunedteam model specialist-N fable` restarts a specialist on Fable; the window returns
  to the team's model at its `tunedteam done`. The start asks when the director uses it: only when you ask,
  or also on its own for the tasks that need the largest model. The director stays on Opus.
- A specialist's status line has four lines: name, task and ETA with the model and context; its worktree
  (`⎇ repo · branch · folder`); the team; the Mac. `tunedteam status` has Model and Worktree columns.
- Context percent counts Fable against its 1M window.
- The start's questions are numbered steps with one line of explanation each; an answered step folds into
  `✓ title: answer`.
- New start step "Lazygit tab": this repo, this repo and the connected repos, or off.
- New start step "Keep the Mac awake": `caffeinate -i -d` for as long as the team runs.

## 0.2.38 (2026-11-02)

- With connected repos, the start asks whether each gets a lazygit tab. The default is no, because lazygit opens
  the repo's main checkout, not an agent's worktree. The team remembers the answer for its next start.

## 0.2.37 (2026-11-01)

- `tunedteam worktrees` shows every worktree of the team with its owner, branch, state and age.
  `tunedteam worktrees prune` removes only the merged, clean and unused ones with their branches. It keeps
  anything with uncommitted files, a running task or process, a parked task, or less than an hour old.
- `tunedteam done` now sees every worktree the window made, also after a second worktree or a restart.
  `tunedteam done --force` lets go of work handed to another window.

## 0.2.36 (2026-11-01)

- A killed window no longer disappears. It stays open with its exit code or signal (`signal=term`), and the
  death goes to `~/.tunedteam/pane-deaths.log` with the time, team and window. A clean exit closes the window
  as before. `tunedteam restart <window>` brings a dead window back.
- Agents stop a dev server by its listening port only, so they no longer kill browsers and tests connected to
  that port, or a teammate's server.

## 0.2.35 (2026-10-25)

- A brake on your plan. Past 80% of the 5-hour or weekly limit the team gives no sweeps, adds no
  specialists and uses only Haiku or Sonnet subagents; past 90% it starts no new tasks, running ones
  finish or park, and the director tells you once with the reset time. Back under 80%, work goes on.
  The director's Mac line shows it (`▲ plan week 83%: no sweeps`), `tunedteam status` shows the use.
- Say "test and fix" or "wait" to the director to switch what the team does with nothing to do
  (`tunedteam idle test|wait`). "test and fix" is on the director's line of things to say.

## 0.2.34 (2026-10-24)

- Nobody holds a blocked task. When a task waits for you (about a minute without your answer, or after
  "goodnight"), the specialist commits what it has, parks the task with `tunedteam park` and takes other
  work. Parked tasks are listed in `tunedteam tasks`; `tunedteam unpark N` gives one back once you answer.
- While you are away the director asks nothing more and keeps your questions for one short list.

## 0.2.33 (2026-10-24)

- New start question: what the team does when it has nothing to do. "Test and fix": free specialists
  sweep one area each (UI, behavior, API, performance, architecture) and only record problems; open
  findings go out as fix tasks. The split follows the queue: under 3 open, the free ones sweep; 3 to 10,
  at most one sweeps; over 10, everybody fixes. An architecture change comes to you as one decision.
- New `tunedteam findings`: the team's queue of problems found (add, take, close, list). It outlives
  restarts; `tunedteam status` shows how many are open. Specialists record problems outside their task
  there instead of fixing them on the side.

## 0.2.32 (2026-10-23)

- No specialist waits for you. Specialists send questions to the director, who decides on its own,
  product and technical choices included. What only you can give (a secret, a yes for production)
  comes in one message, each item with a fix that stops it coming back.
- The director makes sure each specialist can do its task before it starts: dependencies, .env,
  test accounts, tokens, a dev server slot, permissions.
- Fewer auto-mode refusals: every window tells auto mode it is part of a team and which repos are
  yours. After 3 refusals in a row auto mode stops for a human; this keeps windows from getting there.
- New `tunedteam allow`: a permission rule (`tunedteam allow 'Bash(npm run dev*)'`) or a note for
  auto mode (`tunedteam allow --env "QA is the team's staging"`) for every window of the team,
  approved once.
- Every task says how to check it is done (a test or a behavior); specialists merge only once it holds.
- This changelog. `release.sh` refuses a version without an entry here.

Earlier versions: see `git log`.
