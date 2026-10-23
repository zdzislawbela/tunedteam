"""`tunedteam check` skips a command that passed on the same clean tree; release.sh skips a release with no
new commits.   python3 -m unittest discover tests"""
import os, shutil, subprocess, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, 'bin', 'tunedteam')
ENV = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
           GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t', GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@t',
           TUNED_CHECK_PATTERN='tunedteam-test-no-such-check')


def sh(cwd, *cmd):
    return subprocess.run(cmd, cwd=cwd, env=ENV, capture_output=True, text=True)


def git(cwd, *args):
    out = sh(cwd, 'git', *args)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.repo = os.path.join(self.tmp, 'repo')
        os.makedirs(self.repo)
        git(self.repo, 'init', '-q', '-b', 'main')
        self.commit('a.txt', 'one')

    def commit(self, name, text):
        with open(os.path.join(self.repo, name), 'w') as f:
            f.write(text)
        git(self.repo, 'add', name)
        git(self.repo, 'commit', '-q', '-m', name + ' ' + text)


class CheckTest(Base):
    def setUp(self):
        super().setUp()
        self.count = os.path.join(self.tmp, 'count')  # outside the repo: counting runs leaves the tree clean

    def check(self, *cmd, cwd=None, force=False):
        return sh(cwd or self.repo, BIN, 'check', *(['--force'] if force else []), *cmd)

    def counting(self, code=0):
        return ('sh', '-c', f'echo x >> {self.count}; exit {code}')

    def runs(self):
        if not os.path.exists(self.count):
            return 0
        with open(self.count) as f:
            return f.read().count('x')

    def test_second_run_on_same_tree_is_skipped(self):
        self.assertEqual(self.check(*self.counting()).returncode, 0)
        out = self.check(*self.counting())
        self.assertEqual(out.returncode, 0)
        self.assertIn('skipped: passed on ' + git(self.repo, 'rev-parse', 'HEAD')[:12], out.stdout)
        self.assertEqual(self.runs(), 1)

    def test_force_runs_again(self):
        self.check(*self.counting())
        self.assertEqual(self.check(*self.counting(), force=True).returncode, 0)
        self.assertEqual(self.runs(), 2)

    def test_failure_is_not_remembered(self):
        self.assertEqual(self.check(*self.counting(1)).returncode, 1)
        self.assertEqual(self.check(*self.counting(1)).returncode, 1)
        self.assertEqual(self.runs(), 2)

    def test_new_tree_or_other_command_runs(self):
        self.check(*self.counting())
        self.commit('a.txt', 'two')
        self.check(*self.counting())
        self.check('sh', '-c', f'echo x >> {self.count}; true')
        self.assertEqual(self.runs(), 3)

    def test_dirty_tree_always_runs(self):
        with open(os.path.join(self.repo, 'new.txt'), 'w') as f:
            f.write('untracked')
        self.check(*self.counting())
        self.check(*self.counting())
        self.assertEqual(self.runs(), 2)

    def test_command_that_changes_the_tree_is_not_remembered(self):
        cmd = ('sh', '-c', f'echo x >> {self.count}; echo changed > a.txt')
        self.check(*cmd)
        git(self.repo, 'checkout', '--', 'a.txt')
        self.check(*cmd)
        self.assertEqual(self.runs(), 2)

    def test_other_worktree_with_same_tree_is_skipped(self):
        self.check(*self.counting())
        wt = os.path.join(self.tmp, 'wt')
        git(self.repo, 'worktree', 'add', '-q', '-b', 'side', wt)
        self.assertIn('skipped', self.check(*self.counting(), cwd=wt).stdout)
        self.assertEqual(self.runs(), 1)


class ReleaseTest(Base):
    def setUp(self):
        super().setUp()
        shutil.copy(os.path.join(ROOT, 'release.sh'), self.repo)
        with open(os.path.join(self.repo, 'VERSION'), 'w') as f:
            f.write('0.1.0\n')
        with open(os.path.join(self.repo, 'CHANGELOG.md'), 'w') as f:
            f.write('# Changelog\n\n## 0.1.1 (2026-10-23)\n\n- two\n\n## 0.1.0\n\n- one\n')
        git(self.repo, 'add', 'release.sh', 'VERSION', 'CHANGELOG.md')
        git(self.repo, 'commit', '-q', '-m', 'Release 0.1.0')
        git(self.repo, 'tag', 'v0.1.0')

    def release(self, v):
        return sh(self.repo, 'sh', 'release.sh', v)

    def test_no_commits_since_tag_skips_release(self):
        head = git(self.repo, 'rev-parse', 'HEAD')
        out = self.release('0.1.1')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('No commits since v0.1.0: nothing to release.', out.stdout)
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), head)
        self.assertEqual(git(self.repo, 'tag', '--list', 'v0.1.1'), '')

    def test_new_commit_goes_on_to_release(self):
        self.commit('a.txt', 'two')
        out = self.release('0.1.1')  # stops at the push: the test repo has no remote
        self.assertNotIn('nothing to release', out.stdout)
        self.assertEqual(git(self.repo, 'log', '-1', '--format=%s'), 'Release 0.1.1')

    def test_no_changelog_entry_no_release(self):
        self.commit('a.txt', 'two')
        out = self.release('0.1.2')
        self.assertNotEqual(out.returncode, 0)
        self.assertIn('no "## 0.1.2" entry', out.stderr)
        self.assertEqual(git(self.repo, 'tag', '--list', 'v0.1.2'), '')
        self.assertEqual(git(self.repo, 'log', '-1', '--format=%s'), 'a.txt two')

    def test_same_tag_can_be_finished_again(self):
        out = self.release('0.1.0')
        self.assertNotIn('nothing to release', out.stdout)


if __name__ == '__main__':
    unittest.main()
