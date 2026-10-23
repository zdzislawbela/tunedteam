"""`tunedteam allow` adds permission rules and auto-mode context to every window's settings.
   python3 -m unittest discover tests"""
import json, os, shutil, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, 'bin', 'tunedteam')


class AllowTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home)
        self.team = os.path.join(self.home, '.tunedteam', 'teams', 't')
        os.makedirs(os.path.join(self.team, 'settings'))
        with open(os.path.join(self.team, 'config.json'), 'w') as f:
            json.dump({'cwd': '/x/app', 'repos': ['/x/api'], 'speak': 'off', 'db': 'ask', 'specialists': 1}, f)
        with open(os.path.join(self.team, 'settings', 'specialist-1.json'), 'w') as f:
            f.write('{}')

    def allow(self, *args):
        env = dict(os.environ, HOME=self.home, TUNED_TEAM='t')
        return subprocess.run([BIN, 'allow', *args], env=env, capture_output=True, text=True, check=True).stdout

    def settings(self):
        with open(os.path.join(self.team, 'settings', 'specialist-1.json')) as f:
            return json.load(f)

    def test_rules_and_context_reach_open_windows(self):
        self.allow('Bash(npm run dev*)')
        self.allow('Bash(npm run dev*)')
        self.allow('--env', 'QA', 'is', 'staging')
        s = self.settings()
        self.assertEqual(s['permissions']['allow'], ['Bash(npm run dev*)'])
        self.assertIn('mcp__*__deploy_*', s['permissions']['ask'])  # the owner's ask list stays
        env = s['autoMode']['environment']
        self.assertEqual(env[0], '$defaults')
        self.assertTrue(any('/x/app, /x/api' in e for e in env))
        self.assertEqual(env[-1], 'QA is staging')
        self.assertIn('Bash(npm run dev*)', self.allow())

    def test_without_rules_no_allow_list(self):
        self.allow('--env', 'x')
        self.assertNotIn('allow', self.settings()['permissions'])


if __name__ == '__main__':
    unittest.main()
