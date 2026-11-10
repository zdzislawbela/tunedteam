"""The start's own steps: the lazygit tab, keeping the Mac awake, and the model a window starts on.
python3 -m unittest discover tests"""
import importlib.machinery, importlib.util, io, json, os, shutil, sys, tempfile, unittest
from unittest import mock

BIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bin', 'tunedteam')


def load():
    loader = importlib.machinery.SourceFileLoader('tunedteam', BIN)
    tt = importlib.util.module_from_spec(importlib.util.spec_from_loader('tunedteam', loader))
    loader.exec_module(tt)
    return tt


class ChooseLazygitTest(unittest.TestCase):
    def setUp(self):
        self.tt = load()

    def answer(self, line, repos=('/r/api',), last=None, installed=True):
        with mock.patch.object(self.tt.shutil, 'which', return_value='/bin/lazygit' if installed else None), \
                mock.patch.object(sys, 'stdin', io.StringIO(line)):
            return self.tt.choose_lazygit(list(repos), last or {})

    def test_no_lazygit_no_question(self):
        self.assertEqual(self.answer('1\n', installed=False), 'off')

    def test_enter_means_this_repo(self):
        self.assertEqual(self.answer('\n'), 'repo')

    def test_connected_repos_too(self):
        self.assertEqual(self.answer('2\n'), 'all')

    def test_off(self):
        self.assertEqual(self.answer('3\n'), 'off')
        self.assertEqual(self.answer('2\n', repos=()), 'off')  # no connected repos: this repo, off

    def test_enter_keeps_the_last_answer(self):
        self.assertEqual(self.answer('\n', last={'lazygit': 'off'}), 'off')
        self.assertEqual(self.answer('\n', last={'lazygit_repos': True}), 'all')  # the answer of versions before 0.2.39

    def test_all_without_connected_repos_falls_back_to_this_repo(self):
        self.assertEqual(self.answer('\n', repos=(), last={'lazygit': 'all'}), 'repo')


class ChooseAwakeTest(unittest.TestCase):
    def setUp(self):
        self.tt = load()

    def answer(self, line, last=None, there=True):
        with mock.patch.object(self.tt.os.path, 'exists', return_value=there), \
                mock.patch.object(sys, 'stdin', io.StringIO(line)):
            return self.tt.choose_awake(last or {})

    def test_on_by_default_and_remembered(self):
        self.assertIs(self.answer('\n'), True)
        self.assertIs(self.answer('2\n'), False)
        self.assertIs(self.answer('\n', last={'awake': False}), False)

    def test_no_caffeinate_no_question(self):
        self.assertIs(self.answer('1\n', there=False), False)

    def test_caffeinate_lives_as_long_as_the_session(self):
        with mock.patch.object(self.tt.subprocess, 'Popen') as popen:
            self.tt.keep_awake('shop')
        cmd = popen.call_args[0][0]
        self.assertEqual(cmd[:5], ['/usr/bin/caffeinate', '-i', '-d', 'sh', '-c'])
        self.assertIn('has-session -t =shop', cmd[5])


class WindowModelTest(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.tt = load()
        self.tt.HOME = self.tmp
        self.tt.WINDOWS = os.path.join(self.tmp, '.tunedteam', 'windows.json')
        self.cfg = {'model': 'sonnet'}
        self.tt.write_json(os.path.join(self.tt.state_dir('t'), 'config.json'), self.cfg)

    def test_director_on_opus_specialists_on_the_teams_model(self):
        self.assertEqual(self.tt.window_model('t', 'director', self.cfg), 'opus')
        self.assertEqual(self.tt.window_model('t', 'specialist-2', self.cfg), 'sonnet')

    def test_a_given_model_holds_until_it_is_taken_back(self):
        self.tt.set_window_model('t', 'specialist-2', 'fable')
        self.assertEqual(self.tt.window_model('t', 'specialist-2', self.cfg), 'fable')
        self.assertEqual(self.tt.window_model('t', 'specialist-1', self.cfg), 'sonnet')
        self.tt.set_window_model('t', 'specialist-2', None)
        self.assertEqual(self.tt.window_model('t', 'specialist-2', self.cfg), 'sonnet')

    def test_the_teams_model_is_no_override(self):
        self.tt.set_window_model('t', 'specialist-2', 'fable')
        self.tt.set_window_model('t', 'specialist-2', 'sonnet')
        with open(os.path.join(self.tt.state_dir('t'), 'models.json')) as f:
            self.assertEqual(json.load(f), {})

    def test_launch_uses_the_windows_model(self):
        self.tt.set_window_model('t', 'specialist-2', 'fable')
        cfg = dict(self.cfg, cwd=self.tmp, specialists=2, control='owner', speak='off')
        with mock.patch.object(self.tt, 'numbers', return_value=[1, 2]):
            _, cmd = self.tt.launch('t', 'specialist-2', cfg)
            _, other = self.tt.launch('t', 'specialist-1', cfg)
        self.assertIn('--model fable', cmd)
        self.assertIn('--model sonnet', other)

    def test_director_prompt_carries_the_fable_rule(self):
        cfg = dict(self.cfg, cwd=self.tmp, specialists=1, control='owner', speak='off')
        with mock.patch.object(self.tt, 'numbers', return_value=[1]):
            ask = open(self.tt.prompt_file('t', 'director', cfg)).read()
            auto = open(self.tt.prompt_file('t', 'director', dict(cfg, fable='auto'))).read()
            spec = open(self.tt.prompt_file('t', 'specialist-1', dict(cfg, fable='auto'))).read()
        self.assertIn('Fable (the largest model) is ON REQUEST', ask)
        self.assertIn('Fable (the largest model) is AUTOMATIC', auto)
        self.assertNotIn('Fable (the largest model)', spec)

    def test_context_counts_against_the_real_window(self):
        self.assertEqual(self.tt.ctx_pct(300_000, 'claude-fable-5-2'), 30)
        self.assertEqual(self.tt.ctx_pct(300_000, 'claude-opus-5-5'), 30)
        self.assertEqual(self.tt.ctx_pct(100_000, 'claude-sonnet-5-5'), 50)
        self.tt.write_json(self.tt.WINDOWS, {'claude-sonnet-5-5': 1_000_000, 'claude-opus-5-5': 200_000})
        self.assertEqual(self.tt.ctx_pct(100_000, 'claude-sonnet-5-5'), 10)  # Claude Code's own word, when larger
        self.assertEqual(self.tt.ctx_pct(300_000, 'claude-opus-5-5'), 30)    # a 200k report never shrinks 1M

    def test_names(self):
        self.assertEqual(self.tt.model_name('claude-fable-5-2'), 'Fable')
        self.assertEqual(self.tt.model_name('sonnet'), 'Sonnet')
        self.assertEqual(self.tt.worktree_short('/r/shop-worktrees.noindex/fix-cart'), 'shop/fix-cart')
        self.assertEqual(self.tt.worktree_short(''), '')


if __name__ == '__main__':
    unittest.main()
