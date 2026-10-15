// Tuned Team: a team of Claude Code agents in one editor window.
// manager, deputy and N colleagues (numbered from 1), each in its
// own editor group, with the shared team.md plus a role from a .md file (--append-system-prompt).
// Roles: ~/.tuned-team/roles/<role>.md (your own) or defaults/roles/<role>.md from this extension.
const vscode = require("vscode");
const path = require("path");
const fs = require("fs");
const os = require("os");

const EXT_ID = "tuned.tuned-team";
const ROWS = 2;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const quote = (s) => `'${String(s).replace(/'/g, "'\\''")}'`;

let extensionPath = "";
let state; // workspaceState: remembered per project

// Control mode, per project. It only steers the team's roles, not Claude Code's own permissions.
const CONTROL = {
  decide: {
    label: "I DECIDE ALL",
    description: "work projects: release, push, deploy and settings wait for your yes",
    text: "Control mode for this project: I DECIDE ALL. Release, push, deploy and changes to settings or permissions wait for a yes from the owner, given after you show the exact repo, branch and commits. The owner pushes by hand: give them the exact command.",
  },
  claude: {
    label: "ALL CLAUDE",
    description: "hobby projects: the deputy releases on its own, colleagues do not ask about each step",
    text: "Control mode for this project: ALL CLAUDE. The deputy releases on its own when there are new merged commits on the base branch; colleagues do not ask the owner about each step. Permission prompts and sandbox blocks still go to the owner.",
  },
};
const controlOf = () => (CONTROL[state?.get("control")] ? state.get("control") : "decide");

// A role from ~/.tuned-team/roles takes precedence over the built-in one.
function roleFile(role) {
  const own = path.join(os.homedir(), ".tuned-team", "roles", `${role}.md`);
  return fs.existsSync(own) ? own : path.join(extensionPath, "defaults", "roles", `${role}.md`);
}

// Every window starts black; from then on the status line (bin/tuned-statusline.sh)
// turns it red as context fills up. OSC 11 sets the terminal background.
const BLACK = "#000000";
const tintSeq = `\\033]11;${BLACK}\\007`;

// Grey banner in the manager's window, printed right before claude starts.
const BANNER = "TUNED TEAM · READY";
const bannerSeq = `\\033[48;5;240m\\033[38;5;255m\\033[1m  ${BANNER}  \\033[0m\\n`;

const cwdOf = () => vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

// One member: a terminal named like the session, claude with its role.
// perl replaces {{ROLES}} and {{ADD_URL}} in the role file (via environment
// variables, so paths with spaces and apostrophes are safe).
function launchCmd(nr, role, cwd, opts = session) {
  const name = nr === 0 ? "manager" : nr === 1 ? "deputy" : `${nr - 1}-colleague`;
  // Manager and deputy always run on Opus; the wizard's model applies to colleagues.
  const chosen = nr <= 1 ? "opus" : opts.model;
  const model = chosen ? ` --model ${quote(chosen)}` : "";
  // Every window starts in auto mode.
  const mode = " --permission-mode auto";
  // Every window starts like a plain claude: slash commands, skills, the project's MCP servers
  // and the claude.ai connectors (e.g. Claude Docs). No --strict-mcp-config: it hides the connectors.
  const start = nr === 0 ? ` ${quote(startMessage(opts))}` : "";
  const roles = path.dirname(roleFile("colleague"));
  const addUrl = `${vscode.env.uriScheme}://${EXT_ID}/add`;
  const prompt =
    `"$(TT_ROLES=${quote(roles)} TT_ADD=${quote(addUrl)} ` +
    `perl -pe 's/\\{\\{ROLES\\}\\}/$ENV{TT_ROLES}/g; s/\\{\\{ADD_URL\\}\\}/$ENV{TT_ADD}/g' ${quote(roleFile("team"))} ${quote(roleFile(role))}; ` +
    `printf '\\n\\nLanguage: ${opts.lang === "pl" ? "reply to the owner and write to teammates in Polish" : "reply to the owner and write to teammates in English"}.\\n'; ` +
    `printf '%s\\n' ${quote(CONTROL[controlOf()].text)})"`;
  const banner = nr === 0 ? `printf '${bannerSeq}'; ` : "";
  return `printf '${tintSeq}'; ${banner}claude -n ${name}${model}${mode} --append-system-prompt ${prompt}${start}`;
}

// Tab icons (codicons) and colours, the same colours as the layout preview in tuned-team.
const ICONS = {
  manager: ["star-full", "terminal.ansiBlue"],
  deputy: ["shield", "terminal.ansiMagenta"],
  colleague: ["account", "terminal.ansiWhite"],
  standby: ["zap", "terminal.ansiYellow"],
};
const iconOf = (role) => ({ iconPath: new vscode.ThemeIcon(ICONS[role][0]), color: new vscode.ThemeColor(ICONS[role][1]) });

// location: an editor group ({ viewColumn }), the panel, or a split ({ parentTerminal }).
function member(nr, role, location, cwd, opts = session) {
  const label = nr >= 2 ? `#${nr - 1} ${role}` : role[0].toUpperCase() + role.slice(1);
  const t = vscode.window.createTerminal({ name: label, cwd, location, ...iconOf(role) });
  t.sendText(launchCmd(nr, role, cwd, opts));
  return t;
}

// Cull: exit a colleague's claude and start it fresh in the same terminal.
// Only for colleagues; the manager calls it for colleagues the deputy lists as READY TO CLEAR.
async function restart(k) {
  if (!(k >= 1)) return vscode.window.showErrorMessage("Tuned Team: only colleagues (#1 and up) can be restarted.");
  const nr = k + 1;
  const t = vscode.window.terminals.find((x) => new RegExp(`#${k} colleague`).test(x.name));
  if (!t) return vscode.window.showErrorMessage(`Tuned Team: no colleague #${k}.`);
  t.sendText("/exit");
  await sleep(3000);
  t.sendText(launchCmd(nr, "colleague", cwdOf()));
}

// Does the terminal's shell still have a child (claude)? Same pgrep as label().
async function busy(t) {
  const shell = await t.processId;
  if (!shell) return false;
  try {
    return require("child_process").execFileSync("pgrep", ["-P", String(shell)], { encoding: "utf8" }).trim() !== "";
  } catch {
    return false;
  }
}

// The end: close the whole team. The manager runs `tuned-the-end`, which checks for
// unmerged work and then opens this URI. The manager's claude exits and its window shows
// THE END while colleagues close one by one, then the deputy; GOOD BYE, and it closes too.
async function end() {
  const STEP = 1500;
  const all = vscode.window.terminals;
  const manager = all.find((x) => x.name === "Manager");
  const others = [...all.filter((x) => /^#\d+ colleague/.test(x.name)), ...all.filter((x) => x.name === "Deputy")];
  let show = false;
  if (manager) {
    // Let the manager finish its last reply, then exit its claude. The animation command goes
    // in only once claude is gone, so it never lands in claude's prompt.
    await sleep(4000);
    manager.sendText("/exit");
    for (let i = 0; i < 20 && (await busy(manager)); i++) await sleep(500);
    show = !(await busy(manager));
    if (show) manager.sendText(`"$HOME/bin/tuned-the-end" --show ${Math.ceil((others.length * STEP) / 1000) + 1}; exit`);
  }
  for (const t of others) {
    t.sendText("/exit");
    await sleep(STEP);
    t.dispose();
  }
  if (manager) {
    await sleep(show ? 4000 : 0);
    manager.dispose();
  }
}

// Settings from the wizard; "add colleague" in the same editor window uses them too.
let session = {};

// The manager's first message: "start" plus what you said in the wizard.
function startMessage(opts) {
  let msg = "start";
  if (opts.sizeLabel) msg += `. Size of the work: ${opts.sizeLabel}. Colleagues: ${opts.n}.`;
  if (opts.cron) msg += ` Set up a recurring task right away: ${opts.cron}`;
  return msg;
}

// Numbers already open in this window (terminals are named "#N role").
function taken() {
  // Slots: manager 0, deputy 1, colleague k = k + 1 (terminals are named "#k colleague").
  return vscode.window.terminals.map((t) => /#(\d+) colleague/.exec(t.name)).filter(Boolean).map((m) => Number(m[1]) + 1);
}

function supported() {
  if (process.platform === "win32") {
    vscode.window.showErrorMessage("Tuned Team works on macOS and Linux. On Windows, run VS Code through WSL.");
    return false;
  }
  return true;
}

// Layout: colleagues in a grid of editor groups (2 rows), the bottom panel split into
// manager | deputy | a fresh shell. The shell that ran tuned-team (shellPid) is closed:
// the API only splits to the right, so a new shell takes its place at the end.
async function team(n, opts = {}, shellPid) {
  if (!supported()) return;
  session = { ...opts, n };
  const cwd = cwdOf();
  const rows = Math.min(ROWS, n);
  const cols = Math.ceil(n / rows);
  await vscode.commands.executeCommand("vscode.setEditorLayout", {
    orientation: 1,
    groups: Array.from({ length: rows }, () => ({ groups: Array.from({ length: cols }, () => ({})) })),
  });
  for (let k = 1; k <= n; k++) {
    member(k + 1, "colleague", { viewColumn: k, preserveFocus: true }, cwd);
    await sleep(200);
  }
  const old = [];
  for (const t of vscode.window.terminals) if (shellPid && (await t.processId) === shellPid) old.push(t);
  const manager = member(0, "manager", vscode.TerminalLocation.Panel, cwd);
  await sleep(200);
  const deputy = member(1, "deputy", { parentTerminal: manager }, cwd);
  await sleep(200);
  // Standby: a plain shell at hand for the owner, for a quick reaction.
  vscode.window.createTerminal({ name: "Standby", cwd, location: { parentTerminal: deputy }, ...iconOf("standby") });
  old.forEach((t) => t.dispose());
  manager.show(false);
}

const pick = async (title, placeHolder, items) => {
  const chosen = await vscode.window.showQuickPick(items, { title, placeHolder, ignoreFocusOut: true });
  return chosen; // undefined = Esc, the whole wizard ends
};

async function askCount() {
  const answer = await vscode.window.showInputBox({
    title: "Tuned Team: how many colleagues?",
    prompt: "How many colleagues besides the manager and the deputy? (1–20)",
    value: "2",
    ignoreFocusOut: true,
    validateInput: (v) => (/^\d+$/.test(v) && v >= 1 && v <= 20 ? null : "Enter a number from 1 to 20"),
  });
  return answer ? Number(answer) : undefined;
}

// Control mode picker; the current one is listed first. Returns false on Esc.
async function pickControl(title) {
  const cur = controlOf();
  const keys = [cur, ...Object.keys(CONTROL).filter((k) => k !== cur)];
  const chosen = await pick(title, "Remembered for this project; change it later with 'Tuned Team: control mode'", keys.map((k) => ({
    label: CONTROL[k].label,
    description: (k === cur ? "current · " : "") + CONTROL[k].description,
    value: k,
  })));
  if (!chosen) return false;
  await state.update("control", chosen.value);
  return true;
}

// Wizard: control mode, model, size of the work (with a suggested number of colleagues), recurring task.
async function start() {
  if (!(await pickControl("Tuned Team (1/4): who decides on release, push and deploy?"))) return;
  const model = await pick("Tuned Team (2/4): which model?", "Model for all team windows", [
    { label: "Opus", description: "recommended: best quality", value: "opus" },
    { label: "Sonnet", description: "faster, uses less of your limit", value: "sonnet" },
    { label: "Default", description: "do not set, stays as in Claude Code", value: "" },
  ]);
  if (!model) return;

  const size = await pick("Tuned Team (3/4): how big is the work?", "This decides how many colleagues we suggest", [
    { label: "One feature or fix", description: "we suggest 2 colleagues", value: 2 },
    { label: "A few tasks, half a day", description: "we suggest 4 colleagues", value: 4 },
    { label: "A full day of coding", description: "we suggest 6 colleagues (8 windows, the limit drains faster)", value: 6 },
    { label: "Other number…", description: "you type it", value: 0 },
  ]);
  if (!size) return;
  const n = size.value || (await askCount());
  if (!n) return;

  const cron = await pick("Tuned Team (4/4): recurring task?", "The manager sets it up right after start", [
    { label: "No", description: "no background tasks", value: "" },
    {
      label: "Yes, release every hour",
      description: "the manager asks the deputy to check new commits and release",
      value: "every hour write to the deputy: check for new commits on the base branch and release if there are any.",
    },
    { label: "Custom…", description: "you type what and how often", value: "custom" },
  ]);
  if (!cron) return;
  let cronText = cron.value;
  if (cron.value === "custom") {
    cronText = await vscode.window.showInputBox({
      title: "Tuned Team: custom recurring task",
      prompt: "What should repeat, and how often? E.g. every 30 minutes: check that the tests pass.",
      ignoreFocusOut: true,
    });
    if (!cronText) return;
  }
  return team(n, { model: model.value, sizeLabel: size.label.toLowerCase(), cron: cronText });
}

// Change the control mode; windows started or restarted from now on get it.
async function control() {
  if (await pickControl("Tuned Team: control mode for this project")) {
    vscode.window.showInformationMessage(`Tuned Team: ${CONTROL[controlOf()].label}. Running windows get it after a restart; tell the manager now if the team is running.`);
  }
}

// One more colleague in a new editor group to the right (the manager calls it).
async function add() {
  if (!supported()) return;
  const nr = Math.max(1, ...taken()) + 1;
  member(nr, "colleague", { viewColumn: vscode.ViewColumn.Beside, preserveFocus: true }, cwdOf());
}

// Label the open Claude tabs "#N label": the terminal's
// shell pid -> its claude child -> ~/.claude/sessions/<pid>.json -> name "N-role".
async function label() {
  const { execFileSync } = require("child_process");
  const home = os.homedir();
  const back = vscode.window.activeTerminal;
  for (const t of vscode.window.terminals) {
    const shell = await t.processId;
    if (!shell) continue;
    let kids = [];
    try {
      kids = execFileSync("pgrep", ["-P", String(shell)], { encoding: "utf8" }).split("\n").filter(Boolean);
    } catch {}
    for (const pid of kids) {
      let session;
      try {
        session = JSON.parse(fs.readFileSync(path.join(home, ".claude", "sessions", `${pid}.json`), "utf8"));
      } catch {
        continue;
      }
      const sn = session.name || "";
      const m = /^(\d+)-(.+)$/.exec(sn);
      const nr = String(sn === "manager" ? 0 : sn === "deputy" ? 1 : m ? Number(m[1]) + 1 : -1);
      if (nr === "-1") continue;
      const title = m ? `#${m[1]} ${m[2].replace(/-/g, " ")}` : sn[0].toUpperCase() + sn.slice(1);
      // renameWithArg renames the active terminal: focus this one first.
      t.show(false);
      await sleep(150);
      await vscode.commands.executeCommand("workbench.action.terminal.renameWithArg", { name: title });
      await sleep(100);
    }
  }
  back?.show(false);
}

exports.activate = (context) => {
  extensionPath = context.extensionPath;
  state = context.workspaceState;
  context.subscriptions.push(
    vscode.commands.registerCommand("tunedTeam.start", start),
    vscode.commands.registerCommand("tunedTeam.add", add),
    vscode.commands.registerCommand("tunedTeam.label", label),
    vscode.commands.registerCommand("tunedTeam.control", control),
    // shell shortcut (the scheme depends on the editor: vscode://, cursor://, windsurf://):
    //   open "vscode://tuned.tuned-team/team?n=4"
    //   open "vscode://tuned.tuned-team/add"
    //   open "vscode://tuned.tuned-team/end"   (via tuned-the-end, which checks for unmerged work first)
    vscode.window.registerUriHandler({
      handleUri: (uri) => {
        if (uri.path === "/add") return add();
        if (uri.path === "/restart") return restart(Number(new URLSearchParams(uri.query).get("nr")));
        if (uri.path === "/label") return label();
        if (uri.path === "/end") return end();
        const q = new URLSearchParams(uri.query);
        const model = ["opus", "sonnet"].includes(q.get("model")) ? q.get("model") : "";
        const lang = q.get("lang") === "pl" ? "pl" : "en";
        return team(Math.max(1, Math.min(20, Number(q.get("n")) || 2)), { model, lang }, Number(q.get("pid")) || 0);
      },
    }),
  );
};
exports.deactivate = () => {};
