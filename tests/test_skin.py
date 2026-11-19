"""A team's skin is tmux's own session styling, so it shows in any terminal and stays on its own team.
   Runs on its own tmux socket. python3 -m unittest discover tests"""
import importlib.machinery, importlib.util, io, os, subprocess, sys, unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, 'bin', 'tunedteam')


def load():
    loader = importlib.machinery.SourceFileLoader('tunedteam', BIN)
    tt = importlib.util.module_from_spec(importlib.util.spec_from_loader('tunedteam', loader))
    loader.exec_module(tt)
    return tt


class SkinTest(unittest.TestCase):
    def setUp(self):
        self.socket = f'tuned-skin-test-{os.getpid()}'
        with mock.patch.dict(os.environ, TUNED_TMUX_SOCKET=self.socket):
            self.tt = load()
        self.addCleanup(self.tt.tmux, 'kill-server')
        for team in ('a', 'b'):
            self.tt.tmux('new-session', '-d', '-s', team, 'exec sleep 100')

    def option(self, team, name):
        return self.tt.tmux('show-options', '-v', '-t', f'={team}:', name).stdout.strip()

    def backgrounds(self, team):
        return self.tt.tmux('list-windows', '-t', f'={team}:', '-F', '#{window-style}').stdout.split()

    def test_asked_in_any_terminal(self):
        for term in ('Apple_Terminal', 'iTerm.app', ''):
            with mock.patch.dict(os.environ, TERM_PROGRAM=term), mock.patch.object(sys, 'stdin', io.StringIO('\n')):
                self.assertEqual(self.tt.choose_skin('a', {'skin': 'jade'}), 'jade')

    def test_paints_only_its_own_session(self):
        self.tt.apply_skin('a', {'skin': 'lagoon'})
        self.assertEqual(self.option('a', 'status-style'), 'bg=#1264a3,fg=#ffffff')
        self.tt.tmux('new-window', '-d', '-t', '=a:', 'exec sleep 100')  # opened later: painted too
        self.tt.tmux('new-window', '-d', '-t', '=b:', 'exec sleep 100')
        self.assertEqual(self.backgrounds('a'), ['bg=#162028', 'bg=#162028'])
        self.assertEqual(self.option('b', 'status-style'), '')
        self.assertEqual(self.backgrounds('b'), ['default', 'default'])

    def test_no_skin_no_options(self):
        self.tt.apply_skin('a', {})
        self.assertEqual(self.option('a', 'status-style'), '')
        self.assertEqual(self.backgrounds('a'), ['default'])


if __name__ == '__main__':
    unittest.main()
