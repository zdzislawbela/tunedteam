"""Scripted Tuned Team demo in an iTerm2 look: tabs listed on the left, one agent per tab, the demo clicks through
director → specialist-2 → specialist-5 → lazygit → director. Writes frames.json for render.swift.

Rebuild docs/demo.gif (macOS, needs gifski):
    python3 frames.py frames.json
    swiftc -O render.swift -o render && mkdir -p out && ./render frames.json out 1
    gifski --fps 10 --quality 85 -o ../demo.gif out/f0*.png"""
import json, sys

W, H, SIDE, TOP, HEAD = 1280, 800, 224, 22, 26
CW, CH = 7.224609375, 15  # Menlo 12 cell
COLS, ROWS = int((W - SIDE - 12) / CW), int((H - TOP - HEAD - 6) / CH)
FPS, END, HOLD = 10, 29.0, 3.0
BG, FG, DIM = '#1b1c20', '#d9d9de', '#80838d'
GREEN, YELLOW, RED, MAGENTA = '#7fc77a', '#e8c46b', '#ec6d6d', '#c792ea'
CYAN, BLUE, ORANGE, LINK = '#6cc6d6', '#6aa6ff', '#e0875f', '#7fb4ff'
USERBG, BORDER, SEL = '#2b2d34', '#4a4d58', '#253a5e'
SIDEBG, SIDESEL, SIDEFG, DOT, HEADBG = '#1f1f22', '#2e2f34', '#c8c8cc', '#5b7cf0', '#26272b'


class Screen:
    def __init__(self):
        self.g = [[[' ', FG, BG, False] for _ in range(COLS)] for _ in range(ROWS)]
        self.ui = []

    def put(self, r, c, text, fg=FG, bg=None, bold=False, maxw=None):
        if maxw is not None and len(text) > maxw:
            text = text[:max(0, maxw - 1)] + '…' if maxw > 0 else ''
        for i, ch in enumerate(text):
            if 0 <= r < ROWS and 0 <= c + i < COLS:
                cell = self.g[r][c + i]
                cell[0], cell[1], cell[3] = ch, fg, bold
                if bg:
                    cell[2] = bg

    def fill(self, r, c, w, bg):
        for i in range(w):
            if 0 <= r < ROWS and 0 <= c + i < COLS:
                self.g[r][c + i][2] = bg

    def box(self, x, y, w, h, color):
        self.put(y, x, '╭' + '─' * (w - 2) + '╮', color)
        self.put(y + h - 1, x, '╰' + '─' * (w - 2) + '╯', color)
        for r in range(y + 1, y + h - 1):
            self.put(r, x, '│', color)
            self.put(r, x + w - 1, '│', color)

    def runs(self):
        out = []
        for row in self.g:
            runs, cur = [], None
            for c, (ch, fg, bg, bold) in enumerate(row):
                key = (fg, bg, bold)
                if cur and cur[0] == key:
                    cur[2] += ch
                else:
                    cur = [key, c, ch]
                    runs.append(cur)
            out.append([[c, t, k[0], k[1], k[2]] for k, c, t in runs if t.strip() or k[1] != BG])
        return out


def tool(t, name, arg, *outs, gap=0.5):
    lines = [(t, 'tool', f'{name}({arg})')]
    for i, o in enumerate(outs):
        lines.append((t + gap + i * 0.15, 'fail' if o.startswith('✗') else 'out', o))
    return lines


def spin_glyph(t):
    return '·✢✳✶✻✽✻✶✳✢'[int(t * 6) % 10]


def log_rows(log, t, working):
    """Claude Code's transcript: a blank line before every new block."""
    rows = []
    for _, kind, text in [l for l in log if l[0] <= t]:
        if kind in ('user', 'msg', 'tool', 'say', 'ask') and rows:
            rows.append(('blank', ''))
        rows.append((kind, text))
    if working:
        rows += [('blank', ''), ('spin', working)]
    return rows


def draw_log(s, x, y, w, h, rows, t):
    for i, (kind, text) in enumerate(rows[-h:]):
        r = y + i
        if kind in ('user', 'user2'):
            s.fill(r, x - 1, w + 1, USERBG)
            s.put(r, x, ('› ' if kind == 'user' else '  ') + text, FG, USERBG, maxw=w)
        elif kind == 'msg':
            s.put(r, x, '› ', DIM)
            s.put(r, x + 2, text, DIM, maxw=w - 2)
        elif kind == 'tool':
            name, rest = text.split('(', 1)
            s.put(r, x, '● ', GREEN)
            s.put(r, x + 2, name, FG, bold=True)
            s.put(r, x + 2 + len(name), '(' + rest, FG, maxw=w - 2 - len(name))
        elif kind in ('out', 'fail'):
            col = RED if kind == 'fail' else GREEN if text.startswith('✓') else DIM
            s.put(r, x, '  ⎿  ', DIM)
            s.put(r, x + 5, text, col, maxw=w - 5)
        elif kind == 'say':
            s.put(r, x, '● ', FG)
            s.put(r, x + 2, text, FG, maxw=w - 2)
        elif kind == 'ask':
            s.put(r, x, '● ', YELLOW)
            s.put(r, x + 2, text, YELLOW, maxw=w - 2)
        elif kind == 'plain':
            s.put(r, x, text, FG, maxw=w)
        elif kind == 'spin':
            verb, since = text
            s.put(r, x, spin_glyph(t) + ' ', ORANGE)
            s.put(r, x + 2, f'{verb}… ', ORANGE)
            secs = int(t - since)
            s.put(r, x + 4 + len(verb), f'({secs}s · ↓ {0.4 + secs * 0.37:.1f}k tokens · esc to interrupt)', DIM,
                  maxw=w - 4 - len(verb))


SPEC = [  # task, branch, spinner verb, steps (seconds after the task arrives)
    ('wishlist table + migration', 'feat/wishlist-db', 'Considering', [
        *tool(0.6, 'Read', 'db/schema.sql', 'Read 212 lines'),
        *tool(1.6, 'Write', 'db/migrations/0042_wishlist.sql', 'Wrote 18 lines'),
        *tool(2.8, 'Bash', 'npm run db:migrate', 'applied 0042_wishlist'),
        *tool(4.0, 'Bash', 'npm test -- db', '✓ 31 passed'),
        *tool(5.2, 'Bash', 'git commit -am "wishlist table"', '[feat/wishlist-db 2d71f0a]'),
        (6.0, 'say', 'Done. Ready for review.'),
    ]),
    ('wishlist API', 'feat/wishlist-api', 'Brewing', [
        *tool(0.6, 'Read', 'src/api/routes.ts', 'Read 140 lines'),
        *tool(1.4, 'Read', 'db/migrations/0042_wishlist.sql', 'Read 18 lines'),
        *tool(2.2, 'Write', 'src/api/wishlist.ts', 'Wrote 64 lines'),
        *tool(3.0, 'Bash', 'npm test -- wishlist.api', '✗ 1 failed: a guest gets 500, the test wants 401'),
        (3.9, 'say', 'Guests hit the handler without a user. Adding the auth guard.'),
        *tool(4.4, 'Update', 'src/api/wishlist.ts', 'Updated src/api/wishlist.ts with 3 additions and 1 removal'),
        *tool(5.0, 'Bash', 'npm test -- wishlist.api', '✓ 12 passed'),
        *tool(5.6, 'Bash', 'git commit -am "wishlist API"', '[feat/wishlist-api 8e04c1d]'),
        (6.2, 'say', 'Done. Ready for review.'),
    ]),
    ('heart button on ProductCard', 'feat/heart-button', 'Crafting', [
        *tool(0.6, 'Read', 'src/components/ProductCard.tsx', 'Read 84 lines'),
        *tool(1.8, 'Write', 'src/components/HeartButton.tsx', 'Wrote 41 lines'),
        *tool(3.0, 'Update', 'src/components/ProductCard.tsx', '+6 −1'),
        *tool(4.2, 'Bash', 'npm run typecheck', 'no errors'),
        *tool(5.4, 'Bash', 'npm test -- HeartButton', '✓ 6 passed'),
        *tool(6.8, 'Bash', 'tunedteam worktree run dev', 'ready on :3103'),
    ]),
    ('/wishlist page', 'feat/wishlist-page', 'Sketching', [
        *tool(0.6, 'Read', 'src/pages/cart.tsx', 'Read 120 lines'),
        *tool(1.8, 'Write', 'src/pages/wishlist.tsx', 'Wrote 97 lines'),
        *tool(3.2, 'Bash', 'npm run dev -- --port 3104', 'ready on :3104'),
        *tool(4.4, 'Screenshot', 'localhost:3104/wishlist', '3 items, grid matches /cart'),
        *tool(6.0, 'Bash', 'npm test -- wishlist.page', '✓ 9 passed'),
    ]),
    ('search: find the slow query', 'fix/search-index', 'Measuring', [
        *tool(0.6, 'Bash', 'npm run bench:search', 'p50 1.8 s   p95 3.1 s'),
        *tool(1.6, 'Grep', '"ILIKE" in src/search', 'Found 3 matches'),
        *tool(2.4, 'Read', 'src/search/query.ts', 'Read 58 lines'),
        (3.0, 'say', 'name ILIKE \'%…%\' scans all 240k products. A trigram index fixes it.'),
        *tool(3.6, 'Write', 'db/migrations/0043_search_index.sql', 'Wrote 4 lines'),
        *tool(4.4, 'Bash', 'npm run db:migrate && npm run bench:search', '✓ p50 0.14 s   p95 0.31 s'),
        *tool(5.4, 'Bash', 'npm test', '✓ 203 passed'),
        *tool(6.2, 'Bash', 'git merge fix/search-index', 'merged to main'),
        (6.8, 'say', 'Done: search 1.8 s → 0.14 s. Reported to the director.'),
    ]),
    ('e2e tests for wishlist', 'test/wishlist-e2e', 'Testing', [
        *tool(0.6, 'Read', 'e2e/cart.spec.ts', 'Read 77 lines'),
        *tool(1.8, 'Write', 'e2e/wishlist.spec.ts', 'Wrote 54 lines'),
        *tool(3.0, 'Bash', 'tunedteam check npx playwright test', 'waiting for a free machine slot…', '✓ 5 passed (38s)', gap=0.7),
        *tool(6.8, 'Bash', 'git commit -am "wishlist e2e"', '[test/wishlist-e2e 91c3b7e]'),
    ]),
    ('copy: empty state, toasts', 'copy/wishlist', 'Wording', [
        *tool(0.6, 'Read', 'src/i18n/en.json', 'Read 310 lines'),
        (1.8, 'say', 'Two options for the empty state.'),
        *tool(2.4, 'Bash', 'tunedteam ask director "A or B?"', 'asked, waiting'),
        (14.0, 'msg', 'Message from @demo-shop.director: B, "Tap ♡ to save items"'),
        *tool(14.6, 'Update', 'src/i18n/en.json', '+6'),
        *tool(15.4, 'Update', 'src/i18n/pl.json', '+6'),
    ]),
    ('review + merge order', 'main', 'Reviewing', [
        (0.6, 'say', 'Merge order: db → api → heart, page → e2e.'),
        *tool(5.0, 'Bash', 'git diff main...feat/wishlist-db', '2 files, +31'),
        *tool(8.0, 'Bash', 'git merge feat/wishlist-db', 'merged to main'),
        *tool(9.6, 'Bash', 'git diff main...feat/wishlist-api', '3 files, +88 −2'),
        *tool(10.6, 'Bash', 'git merge feat/wishlist-api', 'merged to main'),
        *tool(11.2, 'Bash', 'npm test', '✓ 214 passed'),
    ]),
]
START = 7.6
def st_of(i): return START + i * 0.35
WAIT_FROM, ANSWER_T, ANSWER = st_of(6) + 2.9, 22.4, 23.0  # specialist-7 waits on the owner

REQUEST = ('Add a wishlist: a heart on product cards, a /wishlist page, saved per user. '
           'And search is slow, fix it.')
TYPE_A, TYPE_B = 0.4, 3.2
ASK_T = 20.6
DIRECTOR = [
    (3.6, 'user', REQUEST),
    (5.0, 'say', 'Eight tasks, one per specialist:'),
] + [(5.2 + i * 0.2, 'plain', f'    specialist-{i + 1}  {s[0]:30} {s[1]}') for i, s in enumerate(SPEC)] + [
    *tool(7.2, 'Bash', 'tunedteam send specialist-1 … specialist-8', '8 tasks sent'),
    (8.4, 'say', 'Everyone has a task. I tell you when something needs you.'),
    (st_of(4) + 6.9, 'msg', 'Message from @demo-shop.specialist-5: search 1.8 s → 0.14 s (trigram index), merged'),
    (st_of(4) + 7.4, 'say', 'Search is fixed: 1.8 s → 0.14 s, index on products.name, tests pass, on main.'),
    (ASK_T - 0.3, 'msg', 'Message from @demo-shop.specialist-7: empty wishlist text, A or B?'),
    (ASK_T, 'ask', 'specialist-7 asks you: what does an empty wishlist say?'),
    (ASK_T, 'plain', '  A) "Nothing here yet"     B) "Tap ♡ to save items"'),
    (ANSWER, 'user', 'B'),
    (ANSWER + 0.6, 'say', 'Sent. specialist-7 goes on.'),
    (25.4, 'say', 'Wishlist DB and API are merged, 3 of 8 done. The rest are on it.'),
]

COMMITS = [(0, '19bd3f4', 'Release 1.4.0'), (0, 'e41aa90', 'product grid: lazy images'),
           (0, '7c1e0b2', 'checkout: retry payment once'),
           (st_of(4) + 6.2, 'b8d2e61', 'fix/search-index: trigram index on products.name'),
           (st_of(7) + 8.0, '4fa07c3', "Merge branch 'feat/wishlist-db'"),
           (st_of(7) + 10.6, 'c51e9a8', "Merge branch 'feat/wishlist-api'")]
DIFFS = {
    '7c1e0b2': ('checkout: retry payment once', 'src/checkout/pay.ts', ['@@ -41,6 +41,9 @@ export async function pay(order) {',
                '   const res = await charge(order)', '+  if (res.status === 502) {', '+    return charge(order)', '+  }',
                '   return res']),
    'b8d2e61': ('fix/search-index: trigram index on products.name', 'db/migrations/0043_search_index.sql',
                ['@@ -0,0 +1,4 @@', '+CREATE EXTENSION IF NOT EXISTS pg_trgm;', '+CREATE INDEX products_name_trgm',
                 '+  ON products USING gin (name gin_trgm_ops);']),
    '4fa07c3': ("Merge branch 'feat/wishlist-db'", 'db/migrations/0042_wishlist.sql',
                ['@@ -0,0 +1,18 @@', '+CREATE TABLE wishlist (', '+  user_id    uuid NOT NULL REFERENCES users,',
                 '+  product_id uuid NOT NULL REFERENCES products,', '+  added_at   timestamptz DEFAULT now(),',
                 '+  PRIMARY KEY (user_id, product_id)', '+);']),
    'c51e9a8': ("Merge branch 'feat/wishlist-api'", 'src/api/wishlist.ts',
                ['@@ -0,0 +1,64 @@', "+router.post('/wishlist/:id', auth, async (req, res) => {",
                 '+  await addToWishlist(req.user.id, req.params.id)', '+  res.status(204).end()', '+})']),
}

# Which tab is in front, and when.
TABS = [(0, 'director'), (9.2, 'specialist-2'), (13.2, 'specialist-5'), (16.8, 'lazygit'), (20.2, 'director')]


def active(t):
    return [n for at, n in TABS if t >= at][-1]


def spec_state(i, t):
    task, branch, verb, steps = SPEC[i]
    st = st_of(i)
    if t < st:
        return None, [], False
    log = [(st, 'msg', f'Message from @demo-shop.director: {task}, on branch {branch}')] + [(st + d, k, x) for d, k, x in steps]
    if i == 6 and WAIT_FROM <= t < st + 14.0:
        working = ('Waiting for the director', WAIT_FROM)
    else:
        done = steps[-1][2].startswith('Done') and t >= st + steps[-1][0]
        working = False if done else (verb, st)
    return st, log, working


def working_now(i, t):
    st, _, w = spec_state(i, t)
    return st is not None and bool(w)


def screen(s, t, who, typed, status_lines, rows):
    """Transcript, Claude Code's effort hint, the input between two rules, then the status lines. The input
    follows the transcript until the screen is full, then stays at the bottom."""
    room = ROWS - 4 - len(status_lines) - 2 - 1
    shown = min(len(rows), room)
    draw_log(s, 2, 1, COLS - 4, shown, rows, t)
    r = 1 + shown + 2
    s.put(r - 1, COLS - 20, '◐ medium · /effort', DIM)
    tag = f' demo-shop.{who} ─'
    s.put(r, 0, '─' * (COLS - len(tag)), BORDER)
    s.put(r, COLS - len(tag), tag, DIM)
    s.put(r + 1, 0, '› ', FG)
    s.put(r + 1, 2, typed[-(COLS - 4):], FG)
    if int(t * 2) % 2 == 0:
        s.put(r + 1, 2 + len(typed[-(COLS - 4):]), '█', FG)
    s.put(r + 2, 0, '─' * COLS, BORDER)
    for k, line in enumerate(status_lines):
        c = 2
        for text, col, bold in line:
            s.put(r + 3 + k, c, text, col, bold=bold)
            c += len(text)
    r += 3 + len(status_lines)
    s.put(r, 2, '▸▸ auto mode on', YELLOW)
    s.put(r, 17, ' (shift+tab to cycle)', DIM)


SEPS = (' │ ', DIM, False)


def director_view(s, t):
    started = sum(1 for i in range(8) if t >= st_of(i))
    busy = sum(1 for i in range(8) if working_now(i, t))
    waiting = 1 if ASK_T <= t < ANSWER else 0
    team = [(f'● {busy - waiting} working', GREEN, False), ('  ', FG, False), (f'○ {8 - busy} free', DIM, False)]
    if waiting:
        team += [('  ', FG, False), ('▲ 1 WAITING FOR YOU', YELLOW, True)]
    hints = [('say ', DIM, False)]
    for k, w in enumerate(('tasks', 'status', 'add a specialist', 'release', 'close the team')):
        hints += ([(' · ', DIM, False)] if k else []) + [(w, CYAN, False)]
    hints += [SEPS, ('Ctrl+V', FG, True), (' image', DIM, False), SEPS, ('!cmd', FG, True), (' run here', DIM, False)]
    status = [[('demo-shop', FG, True), (' main', MAGENTA, False), SEPS, ('Opus 5.5', DIM, False), SEPS,
               (f'ctx {5 + int(t / 3)}%', GREEN, False), SEPS, ('tunedteam 0.2.29', DIM, False)],
              team, [('● Mac ok', DIM, False)], hints]
    typed = ''
    if TYPE_A <= t < TYPE_B + 0.3:
        typed = REQUEST[:int(len(REQUEST) * min(1, (t - TYPE_A) / (TYPE_B - TYPE_A)))]
    elif ANSWER_T <= t < ANSWER:
        typed = 'B'
    working = ('Planning', 3.6) if 3.6 <= t < 7.2 else ('Sending', 7.2) if 7.2 <= t < 8.4 else (
        ('Answering', ANSWER) if ANSWER <= t < ANSWER + 0.6 else False)
    screen(s, t, 'director', typed, status, log_rows(DIRECTOR, t, working))


def specialist_view(s, i, t):
    st, log, working = spec_state(i, t)
    task, branch = SPEC[i][0], SPEC[i][1]
    ctx = 0 if st is None else min(29, 6 + int((t - st) * 1.6))
    left = [(f'specialist-{i + 1}', FG, True), (' · ' + task, DIM, False)]
    right = [('demo-shop', FG, True), (' ' + branch, MAGENTA, False), SEPS, ('Sonnet 5.5', DIM, False), SEPS,
             (f'ctx {ctx}%', GREEN if ctx < 25 else YELLOW, False), SEPS, ('tunedteam 0.2.29', DIM, False)]
    gap = COLS - 4 - sum(len(x[0]) for x in left + right)
    screen(s, t, f'specialist-{i + 1}', '', [left + [(' ' * gap, FG, False)] + right], log_rows(log, t, working))


def lazygit_view(s, t):
    lw = 50
    commits = [c for c in COMMITS if c[0] <= t][::-1]
    branches = [('main', '')] + [(SPEC[i][1], '↑1') for i in range(7) if t >= st_of(i) + 1.0]
    h = ROWS - 1
    panels = [('Status', 3), ('Files', 5), ('Local branches', 11), ('Commits', h - 3 - 5 - 11 - 3), ('Stash', 3)]
    r = 0
    for n, (title, ph) in enumerate(panels):
        on = title == 'Commits'
        s.box(0, r, lw, ph, GREEN if on else FG)
        s.put(r, 1, f'[{n + 1}]─{title}', GREEN if on else FG, bold=on)
        if title == 'Status':
            s.put(r + 1, 1, '✓ ', GREEN)
            s.put(r + 1, 3, 'demo-shop → main', FG)
        elif title == 'Files':
            s.put(r + 1, 1, 'No changed files', DIM)
        elif title == 'Local branches':
            for k, (b, ahead) in enumerate(branches[:ph - 2]):
                s.put(r + 1 + k, 1, '*' if b == 'main' else ' ', GREEN)
                s.put(r + 1 + k, 3, 'now' if b == 'main' else f'{max(1, int((t - st_of(k - 1)) / 4))}m', DIM)
                s.put(r + 1 + k, 7, b, GREEN if b == 'main' else FG)
                s.put(r + 1 + k, 8 + len(b), ahead, YELLOW)
            s.put(r + ph - 1, lw - 10, f' {len(branches)} of {len(branches)} ', FG)
        elif title == 'Commits':
            for k, (_, sha, msg) in enumerate(commits[:ph - 2]):
                if k == 0:
                    s.fill(r + 1, 1, lw - 2, SEL)
                bg = SEL if k == 0 else None
                s.put(r + 1 + k, 1, sha, YELLOW, bg)
                s.put(r + 1 + k, 9, 'DS', CYAN, bg)
                s.put(r + 1 + k, 12, msg, FG, bg, maxw=lw - 13)
            s.put(r + ph - 1, lw - 10, f' 1 of {len(commits)} ', FG)
        r += ph
    mx, mw = lw, COLS - lw
    s.box(mx, 0, mw, h, FG)
    s.put(0, mx + 1, 'Patch', FG)
    sha = commits[0][1]
    subject, path, diff = DIFFS[sha]
    lines = [(f'commit {sha}', YELLOW), ('Author: Demo Shop <dev@demo-shop.test>', FG), ('Date:   Mon Oct 19 18:02:11 2026', FG),
             ('', FG), ('    ' + subject, FG), ('', FG), (f'diff --git a/{path} b/{path}', FG, True),
             (f'--- a/{path}', FG, True), (f'+++ b/{path}', FG, True)]
    for k, l in enumerate(lines + [(d, CYAN if d.startswith('@@') else GREEN if d.startswith('+') else FG) for d in diff]):
        s.put(1 + k, mx + 2, l[0], l[1], bold=len(l) > 2, maxw=mw - 4)
    s.put(ROWS - 1, 0, 'Checkout: <space> | Merge: M | Rebase: r | Push: P | Pull: p | Keymap: ?', BLUE)


SIDEBAR = ['director'] + [f'specialist-{i + 1}' for i in range(8)] + ['lazygit', 'shell']


def sidebar(ui, t):
    ui.append(['r', 0, 0, W, TOP, '#000000'])
    ui.append(['r', 0, TOP, SIDE, H - TOP, SIDEBG])
    now = active(t)
    for k, name in enumerate(SIDEBAR):
        y = TOP + 6 + k * 34
        if name == now:
            ui.append(['r', 0, y - 6, SIDE, 34, SIDESEL])
        ui.append(['r', 0, y + 28, SIDE, 1, '#2a2b30'])
        ui.append(['t', 10, y + 6, f'» demo-shop · {name}', '#ffffff' if name == now else SIDEFG, 12.5, name == now])
        if k < 9:
            ui.append(['t', SIDE - 30, y + 6, f'⌘{k + 1}', SIDEFG, 12, False])
        busy = (name.startswith('specialist-') and working_now(int(name[11:]) - 1, t)) or (
            name == 'director' and now != 'director' and t >= st_of(4) + 6.9)
        if busy and name != now:
            ui.append(['o', SIDE - 52, y + 9, 10, DOT])
        if name == 'lazygit' and name != now:
            ui.append(['t', SIDE - 56, y + 4, spin_glyph(t), DIM, 15, False])
    ui.append(['r', SIDE, TOP, W - SIDE, HEAD, HEADBG])
    ui.append(['t', SIDE + 12, TOP + 6, '✕', DIM, 11, False])
    title = f'»  ✱ demo-shop.{now}' if now != 'lazygit' else '»  lazygit'
    ui.append(['t', SIDE + 34, TOP + 6, title, SIDEFG, 12.5, False])


def frame(t):
    s = Screen()
    now = active(t)
    if now == 'director':
        director_view(s, t)
    elif now == 'lazygit':
        lazygit_view(s, t)
    else:
        specialist_view(s, int(now[11:]) - 1, t)
    sidebar(s.ui, t)
    return {'g': s.runs(), 'ui': s.ui}


frames, last, refs = [], None, []
for k in range(int(END * FPS)):
    f = frame(k / FPS)
    key = json.dumps(f)
    if key != last:
        frames.append(f)
        last = key
    refs.append(len(frames) - 1)
refs += [refs[-1]] * int(HOLD * FPS)
json.dump({'W': W, 'H': H, 'ox': SIDE + 8, 'oy': TOP + HEAD + 4, 'cols': COLS, 'rows': ROWS, 'bg': BG,
           'frames': frames, 'refs': refs}, open(sys.argv[1], 'w'))
print(f'{COLS}x{ROWS} grid, {len(refs)} frames, {len(frames)} unique')
