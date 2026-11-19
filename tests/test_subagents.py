"""Subagents of a window: a row in `tunedteam status` while they run, marked lines in `tunedteam log`, no ctx
warning inside them, no window-only team commands from them, and a restart that waits for them.
   python3 -m unittest discover tests"""
import json, os, shutil, stat, subprocess, tempfile, time, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, 'bin', 'tunedteam')
CONF = os.path.join(ROOT, 'tmux.conf')


class SubagentTest(unittest.TestCase):
    def setUp(self):
        self.home = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home)
        self.dir = os.path.join(self.home, '.tunedteam', 'teams', 't')
        os.makedirs(os.path.join(self.dir, 'settings'))
        with open(os.path.join(self.dir, 'config.json'), 'w') as f:
            json.dump({'cwd': self.home, 'speak': 'off', 'specialists': 1, 'model': 'haiku', 'control': 'owner'}, f)
        self.env = dict(os.environ, HOME=self.home, TUNED_TEAM='t', TUNED_NAME='director')
        self.env.pop('CLAUDE_CONFIG_DIR', None)
        self.env.pop('TMUX', None)

    def run_(self, cmd, stdin='', name='director'):
        out = subprocess.run([BIN, *cmd], input=stdin, env=dict(self.env, TUNED_NAME=name),
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout

    def hook(self, cmd, name='director', **d):
        out = self.run_([cmd], json.dumps(dict({'session_id': 's1'}, **d)), name=name)
        return json.loads(out)['hookSpecificOutput'] if out.strip() else {}

    def start_sub(self, aid='a1', what='file overlap', name='director'):
        self.hook('pre-tool', name, tool_name='Agent', tool_input={'description': what, 'prompt': 'x'})
        return self.hook('subagent', name, hook_event_name='SubagentStart', agent_id=aid, agent_type='Explore')

    def running(self, name='director'):
        with open(os.path.join(self.dir, 'subagents.json')) as f:
            return json.load(f).get(name, {}).get('running', [])

    def test_settings_have_the_hooks_and_sonnet(self):
        with open(os.path.join(self.dir, 'settings', 'director.json'), 'w') as f:
            f.write('{}')
        self.run_(['allow', '--env', 'x'])  # rewrites every window's settings
        with open(os.path.join(self.dir, 'settings', 'director.json')) as f:
            s = json.load(f)
        self.assertEqual(s['env']['CLAUDE_CODE_SUBAGENT_MODEL'], 'sonnet')
        for event in ('SubagentStart', 'SubagentStop'):
            self.assertTrue(s['hooks'][event][0]['hooks'][0]['command'].endswith(' subagent'))
        self.assertEqual(s['hooks']['PreToolUse'][0]['matcher'], 'Bash|Agent')

    def test_start_and_stop_keep_the_running_list(self):
        out = self.start_sub()
        self.assertEqual(out['hookEventName'], 'SubagentStart')
        self.assertIn('`tunedteam check --timeout 540', out['additionalContext'])
        self.assertIn('window director', out['additionalContext'])
        self.start_sub('a2', 'review diff')
        self.assertEqual([(a['id'], a['type'], a['what']) for a in self.running()],
                         [('a1', 'Explore', 'file overlap'), ('a2', 'Explore', 'review diff')])
        self.hook('subagent', hook_event_name='SubagentStop', agent_id='a1', agent_type='Explore')
        self.assertEqual([a['id'] for a in self.running()], ['a2'])

    def test_rows_of_an_earlier_session_go(self):
        self.start_sub('old')
        self.run_(['subagent'], json.dumps({'session_id': 's2', 'hook_event_name': 'SubagentStart',
                                            'agent_id': 'new', 'agent_type': 'Explore'}))
        self.assertEqual([a['id'] for a in self.running()], ['new'])

    def test_window_only_commands_are_denied_in_a_subagent(self):
        for cmd in ('tunedteam restart self', 'cd /x && tunedteam done', 'tunedteam report eta "~16:00"',
                    'tunedteam park "waits"'):
            out = self.hook('pre-tool', 'specialist-1', tool_name='Bash', tool_input={'command': cmd},
                            agent_id='a1', agent_type='Explore')
            self.assertEqual(out.get('permissionDecision'), 'deny', cmd)
            self.assertIn('specialist-1', out['permissionDecisionReason'])
        # Allowed: the same in the window itself, and other team commands in a subagent.
        self.assertEqual(self.hook('pre-tool', 'specialist-1', tool_name='Bash',
                                   tool_input={'command': 'tunedteam restart self'}), {})
        self.assertEqual(self.hook('pre-tool', 'specialist-1', tool_name='Bash', agent_id='a1',
                                   tool_input={'command': 'tunedteam check --timeout 540 npm test'}), {})

    def test_log_marks_subagent_calls_and_skips_the_warning(self):
        with open(os.path.join(self.dir, 'plan.json'), 'w') as f:
            json.dump({'week': {'pct': 85, 'resets': time.time() + 3600}}, f)
        sub = self.hook('ctx-check', tool_name='Bash', tool_input={'command': 'git log'},
                        agent_id='a1', agent_type='Explore')
        self.assertEqual(sub, {})  # the brake warning waits for the window's own next call
        said = self.hook('ctx-check', tool_name='Bash', tool_input={'command': 'ls'})['additionalContext']
        self.assertIn('85%', said)
        lines = self.run_(['log']).splitlines()
        self.assertIn('director ↳ Explore', lines[0])
        self.assertIn('git log', lines[0])
        self.assertNotIn('↳', lines[1])

    def test_wait_ends_when_the_subagents_stop_or_at_the_timeout(self):
        self.start_sub()
        self.env['TUNED_SUBAGENT_WAIT'] = '30'
        p = subprocess.Popen([BIN, 'subagent-wait', 'director'], env=self.env)
        time.sleep(2.5)
        self.assertIsNone(p.poll())
        self.hook('subagent', hook_event_name='SubagentStop', agent_id='a1')
        self.assertEqual(p.wait(timeout=10), 0)
        self.start_sub('a2')
        self.env['TUNED_SUBAGENT_WAIT'] = '1'
        started = time.time()
        self.run_(['subagent-wait', 'director'])
        self.assertLess(time.time() - started, 5)
        self.assertEqual(self.running(), [])  # forgotten: the restart ends them


class SubagentTmuxTest(unittest.TestCase):
    """status and restart on a team in its own tmux server, with `claude` stubbed."""

    def setUp(self):
        self.home = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home)
        self.socket = f'tuned-test-sub-{os.getpid()}'
        self.addCleanup(self.tmux, 'kill-server')
        stub = os.path.join(self.home, 'bin')
        os.makedirs(stub)
        path = os.path.join(stub, 'claude')
        with open(path, 'w') as f:
            f.write('#!/bin/sh\nexec sleep 100\n')
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
        self.env = dict(os.environ, HOME=self.home, TUNED_TEAM='t', TUNED_TMUX_SOCKET=self.socket,
                        TUNED_NAME='director', TUNED_SUBAGENT_WAIT='20', PATH=f'{stub}:{os.environ["PATH"]}')
        self.env.pop('TMUX', None)
        self.env.pop('CLAUDE_CONFIG_DIR', None)
        self.dir = os.path.join(self.home, '.tunedteam', 'teams', 't')
        os.makedirs(self.dir)
        with open(os.path.join(self.dir, 'config.json'), 'w') as f:
            json.dump({'cwd': self.home, 'speak': 'off', 'specialists': 1, 'model': 'haiku', 'control': 'owner'}, f)
        self.tmux('new-session', '-d', '-s', 't', '-n', 'director', 'exec sleep 100')
        self.tmux('new-window', '-d', '-t', '=t:', '-n', 'specialist-1', 'exec sleep 100')

    def tmux(self, *args):
        return subprocess.run(['tmux', '-L', self.socket, '-f', CONF, *args], env=getattr(self, 'env', None),
                              capture_output=True, text=True)

    def run_(self, cmd, stdin=''):
        out = subprocess.run([BIN, *cmd], input=stdin, env=dict(self.env, TUNED_NAME='specialist-1'),
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout

    def pid(self):
        out = self.tmux('list-panes', '-s', '-t', '=t', '-F', '#{window_name}\t#{pane_pid}').stdout
        return dict(l.split('\t') for l in out.splitlines())['specialist-1']

    def test_status_shows_the_row_and_restart_waits(self):
        self.run_(['pre-tool'], json.dumps({'session_id': 's1', 'tool_name': 'Agent',
                                            'tool_input': {'description': 'lookup tickets'}}))
        self.run_(['subagent'], json.dumps({'session_id': 's1', 'hook_event_name': 'SubagentStart',
                                            'agent_id': 'a1', 'agent_type': 'Explore'}))
        status = subprocess.run([BIN, 'status'], env=self.env, capture_output=True, text=True).stdout
        self.assertRegex(status, r'\| ↳ Explore \|.*subagent, 0 min.*lookup tickets')
        before = self.pid()
        out = subprocess.run([BIN, 'restart', 'specialist-1'], env=self.env, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('waits for 1 running subagent(s) (Explore: lookup tickets)', out.stdout)
        time.sleep(3)
        self.assertEqual(self.pid(), before)  # still waiting
        self.run_(['subagent'], json.dumps({'session_id': 's1', 'hook_event_name': 'SubagentStop', 'agent_id': 'a1'}))
        for _ in range(50):
            if self.pid() != before:
                break
            time.sleep(0.2)
        self.assertNotEqual(self.pid(), before)


if __name__ == '__main__':
    unittest.main()
