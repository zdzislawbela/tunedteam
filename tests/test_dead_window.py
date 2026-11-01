"""A window whose program dies stays open with its exit code, the death goes to a log, and the team commands
   still work with a dead window in the team. Runs on its own tmux socket, with `claude` stubbed.
   python3 -m unittest discover tests"""
import json, os, shutil, signal, stat, subprocess, tempfile, time, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, 'bin', 'tunedteam')
CONF = os.path.join(ROOT, 'tmux.conf')


class DeadWindowTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home)
        self.socket = f'tuned-test-{os.getpid()}'
        self.addCleanup(self.tmux, 'kill-server')
        stub = os.path.join(self.home, 'bin')
        os.makedirs(stub)
        path = os.path.join(stub, 'claude')
        with open(path, 'w') as f:
            f.write('#!/bin/sh\nexec sleep 100\n')
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
        self.env = dict(os.environ, HOME=self.home, TUNED_TEAM='t', TUNED_TMUX_SOCKET=self.socket,
                        PATH=f'{stub}:{os.environ["PATH"]}')
        self.env.pop('TMUX', None)
        team = os.path.join(self.home, '.tunedteam', 'teams', 't')
        os.makedirs(team)
        with open(os.path.join(team, 'config.json'), 'w') as f:
            json.dump({'cwd': self.home, 'speak': 'off', 'specialists': 1, 'model': 'haiku', 'control': 'owner'}, f)
        self.tmux('new-session', '-d', '-s', 't', '-n', 'director', 'exec sleep 100')
        self.tmux('new-window', '-d', '-t', '=t:', '-n', 'specialist-1', 'exec sleep 100')

    def tmux(self, *args):
        return subprocess.run(['tmux', '-L', self.socket, '-f', CONF, *args], env=getattr(self, 'env', None),
                              capture_output=True, text=True)

    def panes(self):
        """{window name: (dead, status, signal)}"""
        out = self.tmux('list-panes', '-s', '-t', '=t', '-F',
                        '#{window_name}\t#{pane_dead}\t#{pane_dead_status}\t#{pane_dead_signal}\t#{pane_pid}').stdout
        return {l.split('\t')[0]: l.split('\t')[1:] for l in out.splitlines()}

    def kill_specialist(self, sig):
        os.kill(int(self.panes()['specialist-1'][3]), sig)
        self.wait(lambda: self.panes().get('specialist-1', ['0'])[0] == '1')

    def wait(self, ok):
        for _ in range(50):
            if ok():
                return
            time.sleep(0.1)
        self.fail('condition not met in 5 s')

    def log(self):
        try:
            with open(os.path.join(self.home, '.tunedteam', 'pane-deaths.log')) as f:
                return f.read()
        except FileNotFoundError:
            return ''

    def test_killed_window_stays_with_its_signal(self):
        self.kill_specialist(signal.SIGTERM)
        self.assertEqual(self.panes()['specialist-1'][:3], ['1', '', 'term'])

    def test_death_is_logged_with_team_window_and_signal(self):
        self.kill_specialist(signal.SIGTERM)
        self.wait(self.log)
        line = self.log()
        for word in ('t', 'specialist-1', 'signal=term'):
            self.assertIn(word, line.split())
        self.assertRegex(line, r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d ')

    def test_clean_exit_closes_the_window(self):
        self.tmux('new-window', '-d', '-t', '=t:', '-n', 'lazygit', 'exit 0')
        self.wait(lambda: 'lazygit' not in self.panes())
        self.assertEqual(self.log(), '')

    def test_status_works_with_a_dead_window(self):
        self.kill_specialist(signal.SIGTERM)
        out = subprocess.run([BIN, 'status'], env=self.env, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('specialist-1', out.stdout)

    def test_restart_brings_a_dead_window_back(self):
        self.kill_specialist(signal.SIGTERM)
        out = subprocess.run([BIN, 'restart', 'specialist-1'], env=self.env, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.wait(lambda: self.panes()['specialist-1'][0] == '0')


if __name__ == '__main__':
    unittest.main()
