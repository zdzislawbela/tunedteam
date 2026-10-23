"""`tunedteam park` puts a blocked task aside so the window is free; `unpark` gives it back.
   python3 -m unittest discover tests"""
import json, os, shutil, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, 'bin', 'tunedteam')


class ParkTest(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home)
        self.team = os.path.join(self.home, '.tunedteam', 'teams', 't')
        os.makedirs(self.team)
        self.reports({'specialist-1': {'what': 'login page', 'branch': 'login', 'worktree': '/x/wt/login',
                                       'repo': '/x/app', 'eta': '~15:00', 'done': False}})

    def reports(self, data=None):
        path = os.path.join(self.team, 'reports.json')
        if data is not None:
            with open(path, 'w') as f:
                json.dump(data, f)
        with open(path) as f:
            return json.load(f)

    def run_(self, name, *args, ok=True):
        env = dict(os.environ, HOME=self.home, TUNED_TEAM='t', TUNED_NAME=name)
        out = subprocess.run([BIN, *args], env=env, capture_output=True, text=True)
        self.assertEqual(out.returncode == 0, ok, out.stderr)
        return out.stdout

    def test_park_frees_the_window_and_unpark_hands_it_back(self):
        self.run_('specialist-1', 'park', 'owner: which discount stays')
        r = self.reports()['specialist-1']
        self.assertNotIn('worktree', r)  # tunedteam done no longer waits for it
        self.assertTrue(r['done'])
        self.run_('specialist-3', 'unpark', '1')
        r = self.reports()['specialist-3']
        self.assertEqual((r['branch'], r['worktree'], r['what']), ('login', '/x/wt/login', 'login page'))
        with open(os.path.join(self.team, 'parked.json')) as f:
            self.assertEqual(json.load(f), [])

    def test_bad_input(self):
        self.run_('specialist-1', 'park', ok=False)
        self.run_('specialist-1', 'unpark', '4', ok=False)


if __name__ == '__main__':
    unittest.main()
