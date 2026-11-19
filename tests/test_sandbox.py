"""A window in Claude Code's sandbox reaches the team's tmux server: each window's settings allow its socket, and a
   blocked socket says so instead of "No window". Runs on its own tmux socket, macOS sandbox-exec as the sandbox.
   python3 -m unittest discover tests"""
import json, os, shutil, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, 'bin', 'tunedteam')
CONF = os.path.join(ROOT, 'tmux.conf')
NO_SOCKETS = '(version 1)(allow default)(deny network-outbound)'


class SandboxTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home)
        self.socket = f'tuned-test-sb-{os.getpid()}'
        self.env = dict(os.environ, HOME=self.home, TUNED_TEAM='t', TUNED_TMUX_SOCKET=self.socket)
        for k in ('TMUX', 'TUNED_NAME'):
            self.env.pop(k, None)
        self.team = os.path.join(self.home, '.tunedteam', 'teams', 't')
        os.makedirs(os.path.join(self.team, 'settings'))
        with open(os.path.join(self.team, 'config.json'), 'w') as f:
            json.dump({'cwd': self.home, 'speak': 'off', 'specialists': 1, 'control': 'owner'}, f)
        with open(os.path.join(self.team, 'settings', 'specialist-1.json'), 'w') as f:
            f.write('{}')
        self.addCleanup(self.tmux, 'kill-server')
        self.tmux('new-session', '-d', '-s', 't', '-n', 'director', 'exec sleep 100')
        self.tmux('new-window', '-d', '-t', '=t:', '-n', 'specialist-1', 'exec sleep 100')

    def tmux(self, *args):
        return subprocess.run(['tmux', '-L', self.socket, '-f', CONF, *args], env=self.env, capture_output=True,
                              text=True)

    def test_settings_allow_the_team_socket(self):
        subprocess.run([BIN, 'allow', '--env', 'x'], env=self.env, capture_output=True, text=True, check=True)
        with open(os.path.join(self.team, 'settings', 'specialist-1.json')) as f:
            allowed = json.load(f)['sandbox']['network']['allowUnixSockets']
        self.assertIn(self.tmux('display', '-p', '#{socket_path}').stdout.strip(), allowed)

    @unittest.skipUnless(shutil.which('sandbox-exec'), 'macOS only')
    def test_blocked_socket_names_the_cause(self):
        out = subprocess.run(['sandbox-exec', '-p', NO_SOCKETS, BIN, 'restart', 'specialist-1'], env=self.env,
                             capture_output=True, text=True)
        self.assertNotEqual(out.returncode, 0)
        self.assertNotIn('No window', out.stderr)
        self.assertIn('Operation not permitted', out.stderr)
        self.assertIn('sandbox', out.stderr)

    def test_missing_window_still_says_no_window(self):
        out = subprocess.run([BIN, 'restart', 'specialist-9'], env=self.env, capture_output=True, text=True)
        self.assertIn('No window "specialist-9"', out.stderr)


if __name__ == '__main__':
    unittest.main()
