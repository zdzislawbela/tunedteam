"""`tunedteam statusline` shows every repo of the team: the window's repo first, then the main checkout and the
connected repos.   python3 -m unittest discover tests"""
import json, os, re, shutil, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, 'bin', 'tunedteam')
ANSI = re.compile(r'\x1b\[[0-9;]*m')


class StatuslineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.env = dict(os.environ, HOME=self.tmp, TUNED_TEAM='t', TUNED_NAME='specialist-1',
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
                        GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t', GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@t')
        self.env.pop('COLUMNS', None)
        self.env.pop('CLAUDE_CONFIG_DIR', None)

    def repo(self, name, branch, version=None):
        path = os.path.join(self.tmp, name)
        os.makedirs(path)
        subprocess.run(['git', 'init', '-q', '-b', branch, path], check=True, env=self.env, capture_output=True)
        subprocess.run(['git', '-C', path, 'commit', '-q', '--allow-empty', '-m', 'start'], check=True, env=self.env, capture_output=True)
        if version:
            with open(os.path.join(path, 'package.json'), 'w') as f:
                json.dump({'version': version}, f)
        return path

    def team(self, cwd, repos):
        d = os.path.join(self.tmp, '.tunedteam', 'teams', 't')
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, 'config.json'), 'w') as f:
            json.dump({'cwd': cwd, 'repos': repos}, f)

    def line(self, cwd):
        out = subprocess.run([BIN, 'statusline'], input=json.dumps({'cwd': cwd}), env=self.env,
                             capture_output=True, text=True, check=True).stdout
        return ANSI.sub('', out)

    def test_one_repo_team(self):
        fe = self.repo('shop', 'master', '2.50.0-rc.0')
        self.team(fe, [])
        line = self.line(fe)
        self.assertIn('\nshop 2.50.0-rc.0 master\n', line)
        self.assertNotIn(' · shop', line)

    def test_two_repo_team_window_repo_first(self):
        fe = self.repo('shop', 'master', '2.50.0-rc.0')
        be = self.repo('silk', 'main')
        self.team(fe, [be])
        self.assertIn('\nshop 2.50.0-rc.0 master · silk main\n', self.line(fe))
        os.remove(os.path.join(self.tmp, '.tunedteam', 'teams', 't', 'statusline-repos.json'))
        self.assertIn('\nsilk main · shop 2.50.0-rc.0 master\n', self.line(be))

    def test_long_line_drops_versions_first(self):
        fe = self.repo('a-rather-long-frontend-name', 'feature/something-long', '12.34.56-rc.7')
        be = self.repo('backend-service-name', 'master', '9.9.9')
        self.team(fe, [be])
        line = self.line(fe)
        self.assertIn('a-rather-long-frontend-name feature/something-long · backend-service-name', line)
        self.assertNotIn('12.34.56', line)

    def test_specialist_shows_model_task_and_worktree(self):
        fe = self.repo('shop', 'master')
        wt = os.path.join(self.tmp, 'shop-worktrees.noindex', 'fix-cart')
        other = os.path.join(self.tmp, 'shop-worktrees.noindex', 'fix-old')
        os.makedirs(wt)
        os.makedirs(other)
        self.team(fe, [])
        d = os.path.join(self.tmp, '.tunedteam', 'teams', 't')
        with open(os.path.join(d, 'reports.json'), 'w') as f:
            json.dump({'specialist-1': {'what': 'cart total', 'eta': '~16:00', 'done': False, 'worktree': wt,
                                        'branch': 'fix/cart', 'repo': fe}}, f)
        with open(os.path.join(d, 'worktrees.json'), 'w') as f:
            json.dump({wt: 'specialist-1', other: 'specialist-1'}, f)
        data = {'cwd': fe, 'model': {'id': 'claude-fable-5-2', 'display_name': 'Fable'},
                'context_window': {'context_window_size': 1000000,
                                   'current_usage': {'input_tokens': 120000}}}
        out = subprocess.run([BIN, 'statusline'], input=json.dumps(data), env=self.env,
                             capture_output=True, text=True, check=True).stdout
        lines = ANSI.sub('', out).splitlines()
        self.assertEqual(len(lines), 4)
        self.assertIn('specialist-1 · cart total · ETA ~16:00', lines[0])
        self.assertIn('Fable │ ctx 12% │ tunedteam', lines[0])
        self.assertEqual(lines[1], '⎇ shop · fix/cart · shop-worktrees.noindex/fix-cart (+1)')
        self.assertIn('working', lines[2])
        with open(os.path.join(self.tmp, '.tunedteam', 'windows.json')) as f:
            self.assertEqual(json.load(f), {'claude-fable-5-2': 1000000})

    def test_outside_a_team_only_the_cwd_repo(self):
        fe = self.repo('shop', 'master')
        be = self.repo('silk', 'main')
        self.team(fe, [be])
        del self.env['TUNED_NAME']
        self.assertEqual(self.line(fe).strip(), 'shop master')


if __name__ == '__main__':
    unittest.main()
