"""`tunedteam findings` keeps the team's queue of problems found; "test and fix" puts the split rule in the
director's prompt.   python3 -m unittest discover tests"""
import importlib.machinery, importlib.util, json, os, shutil, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, 'bin', 'tunedteam')


class FindingsTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home)

    def run_(self, *args, name='specialist-2', ok=True):
        env = dict(os.environ, HOME=self.home, TUNED_TEAM='t', TUNED_NAME=name)
        out = subprocess.run([BIN, 'findings', *args], env=env, capture_output=True, text=True)
        self.assertEqual(out.returncode == 0, ok, out.stderr)
        return out.stdout

    def test_add_take_close(self):
        self.assertIn('finding 1 added; open: 1', self.run_('add', 'login', 'button', 'dead', 'on', 'iPhone'))
        self.assertIn('finding 2 added; open: 2', self.run_('add', 'slow list'))
        self.run_('take', '1', name='specialist-5')
        listing = self.run_()
        self.assertIn('open: 1 · taken: 1 · closed: 0', listing)
        self.assertIn('specialist-5', listing)
        self.run_('close', '1', 'abc123')
        self.assertNotIn('login button', self.run_())
        with open(os.path.join(self.home, '.tunedteam', 'teams', 't', 'findings.json')) as f:
            done = json.load(f)[0]
        self.assertEqual((done['state'], done['note'], done['by']), ('closed', 'abc123', 'specialist-2'))

    def test_bad_input(self):
        self.run_('take', '9', ok=False)
        self.run_('add', ok=False)


class IdlePromptTest(unittest.TestCase):
    def test_director_gets_the_idle_mode(self):
        loader = importlib.machinery.SourceFileLoader('tunedteam', BIN)
        tt = importlib.util.module_from_spec(importlib.util.spec_from_loader('tunedteam', loader))
        loader.exec_module(tt)
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home)
        tt.HOME = home
        cfg = {'cwd': '/x/app', 'specialists': 2, 'control': 'owner', 'speak': 'off', 'idle': 'test'}
        with open(tt.prompt_file('t', 'director', cfg)) as f:
            self.assertIn('TEST AND FIX', f.read())
        with open(tt.prompt_file('t', 'director', dict(cfg, idle='wait'))) as f:
            self.assertNotIn('TEST AND FIX', f.read())
        with open(tt.prompt_file('t', 'specialist-1', cfg)) as f:
            self.assertIn('tunedteam findings add', f.read())


if __name__ == '__main__':
    unittest.main()
