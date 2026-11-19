"""Attaching to a running team from inside another tmux server, and the owner's `tunedteam off`.
python3 -m unittest discover tests"""
import importlib.machinery, importlib.util, io, os, subprocess, sys, unittest
from unittest import mock

BIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bin', 'tunedteam')


def load():
    loader = importlib.machinery.SourceFileLoader('tunedteam', BIN)
    tt = importlib.util.module_from_spec(importlib.util.spec_from_loader('tunedteam', loader))
    loader.exec_module(tt)
    return tt


class InTeamServerTest(unittest.TestCase):
    def setUp(self):
        self.tt = load()
        self.socket = self.tt.TMUX[2]

    def test_outside_tmux(self):
        self.assertFalse(self.tt.in_team_server({}))

    def check(self, panes):
        with mock.patch.object(self.tt.os, 'ttyname', return_value='/dev/ttys007'), \
                mock.patch.object(sys.stdin, 'fileno', return_value=0), \
                mock.patch.object(self.tt, 'tmux', return_value=subprocess.CompletedProcess([], 0, panes, '')):
            return self.tt.in_team_server({'TMUX': f'/private/tmp/tmux-502/{self.socket},123,0'})

    def test_team_pane(self):
        self.assertTrue(self.check('/dev/ttys001\n/dev/ttys007\n'))

    def test_inherited_team_var_outside_a_pane(self):
        # An editor opened from a team window passes $TMUX on; its own terminals are not team panes.
        self.assertFalse(self.check('/dev/ttys001\n/dev/ttys002\n'))

    def test_default_server(self):
        self.assertFalse(self.tt.in_team_server({'TMUX': '/private/tmp/tmux-502/default,123,0'}))


class AttachTest(unittest.TestCase):
    def setUp(self):
        self.tt = load()

    def attach(self, tmux_env):
        env = dict(os.environ, TMUX=tmux_env)
        env.pop('TUNED_NO_ATTACH', None)
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(self.tt, 'tmux'), \
                mock.patch.object(sys.stdout, 'isatty', return_value=True), \
                mock.patch.object(self.tt.os, 'execvpe', side_effect=SystemExit) as execvpe, \
                mock.patch.object(self.tt.os, 'execvp', side_effect=SystemExit) as execvp:
            with self.assertRaises(SystemExit):
                self.tt.attach('t')
        return execvpe, execvp

    def test_other_server_attaches_nested_without_tmux_var(self):
        execvpe, execvp = self.attach('/private/tmp/tmux-502/default,1,0')
        args, = execvpe.call_args_list
        self.assertEqual(args[0][1][-3:], ['attach-session', '-t', '=t'])
        self.assertNotIn('TMUX', args[0][2])
        execvp.assert_not_called()

    def test_team_server_switches_client(self):
        with mock.patch.object(self.tt, 'run', return_value=subprocess.CompletedProcess([], 0, '0\n', '')), \
                mock.patch.object(self.tt, 'in_team_server', return_value=True):
            execvpe, execvp = self.attach(f'/private/tmp/tmux-502/{self.tt.TMUX[2]},1,0')
        execvpe.assert_not_called()
        self.assertIn('switch-client', execvp.call_args[0][1])


class OffTest(unittest.TestCase):
    def setUp(self):
        self.tt = load()

    def off(self, running=True, tty=True, answer='y\n', work=()):
        out = io.StringIO()
        stdin = io.StringIO(answer)
        stdin.isatty = lambda: tty
        with mock.patch.object(self.tt, 'team_name', return_value='t'), \
                mock.patch.object(self.tt, 'tmux', return_value=subprocess.CompletedProcess([], 0 if running else 1)), \
                mock.patch.object(self.tt, 'unmerged_work', return_value=list(work)), \
                mock.patch.object(self.tt, 'close_team') as close, \
                mock.patch.object(sys, 'stdin', stdin), mock.patch.object(sys, 'stdout', out):
            try:
                self.tt.off()
            except SystemExit as e:
                out.write(str(e))
        return close, out.getvalue()

    def test_not_running(self):
        close, out = self.off(running=False)
        close.assert_not_called()
        self.assertIn('not running', out)

    def test_no_terminal_no_close(self):
        close, out = self.off(tty=False)
        close.assert_not_called()
        self.assertIn('close-all', out)

    def test_yes_closes_despite_unmerged_work(self):
        close, out = self.off(work=['branch b: not merged into main'])
        close.assert_called_once_with('t')
        self.assertIn('branch b', out)

    def test_enter_keeps_team(self):
        close, out = self.off(answer='\n')
        close.assert_not_called()
        self.assertIn('Nothing closed', out)


if __name__ == '__main__':
    unittest.main()
