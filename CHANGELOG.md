# Changelog

What each version of Tuned Team brings. Update with `brew upgrade tunedteam`.

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
