"""The plan brake: the status line saves the plan's use, the ctx-check hook tells each window once per level
(80, 90, back under 80); `tunedteam idle` switches test and fix.   python3 -m unittest discover tests"""
import json, os, shutil, subprocess, tempfile, time, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, 'bin', 'tunedteam')


class BrakeTest(unittest.TestCase):
    def setUp(self):
        self.home = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home)
        self.dir = os.path.join(self.home, '.tunedteam', 'teams', 't')

    def run_(self, cmd, stdin='', name='director'):
        env = dict(os.environ, HOME=self.home, TUNED_TEAM='t', TUNED_NAME=name)
        env.pop('CLAUDE_CONFIG_DIR', None)
        out = subprocess.run([BIN, *cmd], input=stdin, env=env, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout

    def status_line(self, five, week, resets=None):
        resets = resets or time.time() + 3600
        self.run_(['statusline'], json.dumps({'cwd': self.home, 'rate_limits': {
            'five_hour': {'used_percentage': five, 'resets_at': resets},
            'seven_day': {'used_percentage': week, 'resets_at': resets}}}))

    def hook(self, name='director', sid='s1'):
        out = self.run_(['ctx-check'], json.dumps({'session_id': sid, 'tool_name': 'Bash'}), name=name)
        return json.loads(out)['hookSpecificOutput']['additionalContext'] if out.strip() else ''

    def test_saves_the_plan(self):
        self.status_line(41.6, 12)
        with open(os.path.join(self.dir, 'plan.json')) as f:
            plan = json.load(f)
        self.assertEqual((plan['5h']['pct'], plan['week']['pct']), (42, 12))

    def test_once_per_level(self):
        self.status_line(10, 50)
        self.assertEqual(self.hook(), '')
        self.status_line(10, 82)
        said = self.hook()
        self.assertIn('week limit is at 82%', said)
        self.assertIn('give no sweeps', said)
        self.assertEqual(self.hook(), '')
        self.assertIn('Haiku or Sonnet', self.hook(name='specialist-1', sid='s2'))
        self.status_line(93, 85)
        self.assertIn('give no new tasks', self.hook())
        self.status_line(5, 20)
        self.assertIn('brake is off', self.hook())
        self.assertEqual(self.hook(), '')

    def test_past_reset_counts_as_zero(self):
        self.status_line(95, 95, resets=time.time() - 60)
        self.assertEqual(self.hook(), '')

    def test_director_line_shows_the_brake(self):
        self.status_line(10, 91)
        self.assertIn('plan week 91%: no new tasks', self.run_(['statusline'], json.dumps({'cwd': self.home})))

    def test_idle_switch(self):
        os.makedirs(self.dir, exist_ok=True)
        with open(os.path.join(self.dir, 'config.json'), 'w') as f:
            json.dump({'idle': 'wait', 'cwd': self.home}, f)
        self.assertIn('TEST AND FIX', self.run_(['idle', 'test']))
        with open(os.path.join(self.dir, 'config.json')) as f:
            self.assertEqual(json.load(f), {'idle': 'test', 'cwd': self.home})
        self.assertIn('Idle mode: test', self.run_(['idle']))


if __name__ == '__main__':
    unittest.main()
