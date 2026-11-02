"""The start asks about lazygit tabs for connected repos only when there is something to decide.
python3 -m unittest discover tests"""
import importlib.machinery, importlib.util, io, os, sys, unittest
from unittest import mock

BIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bin', 'tunedteam')


def load():
    loader = importlib.machinery.SourceFileLoader('tunedteam', BIN)
    tt = importlib.util.module_from_spec(importlib.util.spec_from_loader('tunedteam', loader))
    loader.exec_module(tt)
    return tt


class ChooseLazygitReposTest(unittest.TestCase):
    def setUp(self):
        self.tt = load()

    def answer(self, line, repos=('/r/api',), last=None, installed=True):
        with mock.patch.object(self.tt.shutil, 'which', return_value='/bin/lazygit' if installed else None), \
                mock.patch.object(sys, 'stdin', io.StringIO(line)):
            return self.tt.choose_lazygit_repos(list(repos), last or {})

    def test_no_connected_repos_no_question(self):
        self.assertIs(self.answer('1\n', repos=()), False)

    def test_no_lazygit_no_question(self):
        self.assertIs(self.answer('1\n', installed=False), False)

    def test_enter_means_no(self):
        self.assertIs(self.answer('\n'), False)

    def test_yes(self):
        self.assertIs(self.answer('1\n'), True)

    def test_enter_keeps_the_last_answer(self):
        self.assertIs(self.answer('\n', last={'lazygit_repos': True}), True)


if __name__ == '__main__':
    unittest.main()
