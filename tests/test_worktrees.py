"""`tunedteam worktrees` shows a team's worktrees, `prune` removes only the merged, clean and unused ones, and
   `done` keeps track of every worktree a window made, also after a second worktree or a restart.
   python3 -m unittest discover tests"""
import json, os, shutil, subprocess, tempfile, time, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, 'bin', 'tunedteam')


class WorktreesTest(unittest.TestCase):
    def setUp(self):
        self.home = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home)
        self.repo = os.path.join(self.home, 'app')
        os.makedirs(self.repo)
        self.git(self.repo, 'init', '-q', '-b', 'main')
        self.git(self.repo, 'config', 'user.email', 't@example.com')
        self.git(self.repo, 'config', 'user.name', 't')
        with open(os.path.join(self.repo, '.gitignore'), 'w') as f:
            f.write('node_modules\n')
        self.git(self.repo, 'add', '.')
        self.git(self.repo, 'commit', '-qm', 'first')
        os.makedirs(os.path.join(self.repo, 'node_modules', 'x'))
        self.team = os.path.join(self.home, '.tunedteam', 'teams', 't')
        os.makedirs(self.team)
        with open(os.path.join(self.team, 'config.json'), 'w') as f:
            json.dump({'cwd': self.repo, 'specialists': 2}, f)
        # A socket with no server: `done` reaches its restart step only when nothing stops it.
        self.env = dict(os.environ, HOME=self.home, TUNED_TEAM='t', TUNED_NAME='specialist-1',
                        TUNED_TMUX_SOCKET=f'tuned-test-wt-{os.getpid()}')
        self.env.pop('TMUX', None)

    def git(self, cwd, *args):
        out = subprocess.run(['git', '-C', cwd, *args], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout

    def tt(self, *args, name='specialist-1'):
        return subprocess.run([BIN, *args], cwd=self.repo, env=dict(self.env, TUNED_NAME=name),
                              capture_output=True, text=True)

    def path(self, branch):
        return os.path.join(self.home, 'app-worktrees.noindex', branch.replace('/', '-'))

    def worktree(self, branch, old=True, name='specialist-1', commit=False):
        self.assertEqual(self.tt('worktree', branch, 'main', name=name).returncode, 0)
        path = self.path(branch)
        if commit:
            self.git(path, '-c', 'user.email=t@example.com', '-c', 'user.name=t',
                     'commit', '-q', '--allow-empty', '-m', 'work')
        if old:
            then = time.time() - 7200
            os.utime(path, (then, then))
        return path

    def finish_report(self):
        """The window's current task is over, so its report no longer marks the worktree as in use."""
        p = os.path.join(self.team, 'reports.json')
        with open(p) as f:
            r = json.load(f)
        r.pop('specialist-1', None)
        with open(p, 'w') as f:
            json.dump(r, f)

    def branch_exists(self, branch):
        return subprocess.run(['git', '-C', self.repo, 'rev-parse', '--verify', '--quiet', f'refs/heads/{branch}'],
                              capture_output=True).returncode == 0

    def test_list_shows_branch_owner_and_state(self):
        path = self.worktree('s1/open', commit=True)
        out = self.tt('worktrees').stdout
        for word in ('s1/open', 'specialist-1', 'not merged', path):
            self.assertIn(word, out)

    def test_list_removes_nothing(self):
        path = self.worktree('s1/merged')
        self.finish_report()
        self.tt('worktrees')
        self.assertTrue(os.path.isdir(path))

    def test_prune_removes_merged_clean_worktree_and_branch(self):
        path = self.worktree('s1/merged')
        self.finish_report()
        out = self.tt('worktrees', 'prune')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertFalse(os.path.exists(path))
        self.assertFalse(self.branch_exists('s1/merged'))

    def test_prune_removes_ignored_node_modules_too(self):
        path = self.worktree('s1/merged')
        self.assertTrue(os.path.isdir(os.path.join(path, 'node_modules')))
        self.finish_report()
        self.tt('worktrees', 'prune')
        self.assertFalse(os.path.exists(path))

    def test_prune_keeps_unmerged(self):
        path = self.worktree('s1/open', commit=True)
        self.finish_report()
        self.tt('worktrees', 'prune')
        self.assertTrue(os.path.isdir(path))
        self.assertTrue(self.branch_exists('s1/open'))

    def test_prune_keeps_uncommitted_files(self):
        path = self.worktree('s1/dirty')
        with open(os.path.join(path, 'new.txt'), 'w') as f:
            f.write('work')
        then = time.time() - 7200
        os.utime(path, (then, then))
        self.finish_report()
        self.tt('worktrees', 'prune')
        self.assertTrue(os.path.exists(os.path.join(path, 'new.txt')))

    def test_prune_keeps_a_fresh_worktree(self):
        path = self.worktree('s1/fresh', old=False)
        self.finish_report()
        self.tt('worktrees', 'prune')
        self.assertTrue(os.path.isdir(path))

    def test_prune_keeps_the_worktree_of_a_running_task(self):
        path = self.worktree('s1/current')
        self.tt('worktrees', 'prune')
        self.assertTrue(os.path.isdir(path))

    def test_prune_keeps_a_parked_worktree(self):
        path = self.worktree('s1/parked')
        self.assertEqual(self.tt('park', 'waits for the owner').returncode, 0)
        self.tt('worktrees', 'prune')
        self.assertTrue(os.path.isdir(path))

    def test_prune_keeps_a_worktree_a_process_runs_in(self):
        path = self.worktree('s1/server')
        self.finish_report()
        proc = subprocess.Popen(['sleep', '30'], cwd=path)
        self.addCleanup(proc.wait)
        self.addCleanup(proc.kill)
        then = time.time() - 7200
        os.utime(path, (then, then))
        self.tt('worktrees', 'prune')
        self.assertTrue(os.path.isdir(path))

    def test_prune_leaves_other_files_in_the_folder(self):
        self.worktree('s1/merged')
        self.finish_report()
        other = os.path.join(self.home, 'app-worktrees.noindex', 'run.log')
        with open(other, 'w') as f:
            f.write('log')
        self.tt('worktrees', 'prune')
        self.assertTrue(os.path.exists(other))

    def test_done_sees_an_earlier_worktree_of_the_window(self):
        first = self.worktree('s1/first')
        self.worktree('s1/second')
        out = self.tt('done')
        self.assertNotEqual(out.returncode, 0)
        self.assertIn(first, out.stderr)

    def test_done_sees_a_worktree_after_the_report_is_gone(self):
        path = self.worktree('s1/first')
        self.finish_report()  # what `tunedteam restart` does to the report
        out = self.tt('done')
        self.assertIn('Still open', out.stderr)
        self.assertIn(path, out.stderr)

    def test_done_ignores_another_windows_worktree(self):
        self.worktree('s2/other', name='specialist-2')
        self.assertNotIn('Still open', self.tt('done').stderr)

    def test_done_ignores_a_parked_worktree(self):
        self.worktree('s1/parked')
        self.assertEqual(self.tt('park', 'waits').returncode, 0)
        self.assertNotIn('Still open', self.tt('done').stderr)

    def test_unpark_moves_the_worktree_to_the_new_window(self):
        path = self.worktree('s1/parked')
        self.assertEqual(self.tt('park', 'waits').returncode, 0)
        self.assertEqual(self.tt('unpark', '1', name='specialist-2').returncode, 0)
        self.assertNotIn('Still open', self.tt('done').stderr)
        self.assertIn(path, self.tt('done', name='specialist-2').stderr)

    def test_done_force_hands_the_worktree_on(self):
        path = self.worktree('s1/first')
        self.finish_report()
        self.assertNotIn('Still open', self.tt('done', '--force').stderr)
        self.assertNotIn('Still open', self.tt('done').stderr)
        self.assertTrue(os.path.isdir(path))


if __name__ == '__main__':
    unittest.main()
