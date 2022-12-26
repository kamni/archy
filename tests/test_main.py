import unittest
from unittest import mock

from archy.main import _parse_args, main


class ParseArgsTests(unittest.TestCase):
    """
    Tests for main._parse_args
    """
    def test_no_group(self):
        sys_args = ['archy']
        with mock.patch('sys.argv', sys_args):
            self.assertRaises(SystemExit, _parse_args)

    def test_with_group(self):
        group_name = 'groupname'
        sys_args = ['archy', group_name]
        with mock.patch('sys.argv', sys_args):
            cmd_args = _parse_args()
            self.assertEqual(group_name, cmd_args.group)

    def test_with_no_base_dir(self):
        cwd = '/home'
        mock_getcwd = mock.MagicMock()
        mock_getcwd.return_value = cwd
        sys_args = ['archy', 'groupname']
        with mock.patch('sys.argv', sys_args):
            with mock.patch('os.getcwd', mock_getcwd):
                cmd_args = _parse_args()
                self.assertEqual(cwd, cmd_args.base_dir)

    def test_with_base_dir_short(self):
        base_dir = '/home'
        sys_args = ['archy', 'groupname', '-d', base_dir]
        with mock.patch('sys.argv', sys_args):
            cmd_args = _parse_args()
            self.assertEqual(base_dir, cmd_args.base_dir)

    def test_with_base_dir_long(self):
        base_dir = '/home'
        sys_args = ['archy', 'groupname', f'--base-dir={base_dir}']
        with mock.patch('sys.argv', sys_args):
            cmd_args = _parse_args()
            self.assertEqual(base_dir, cmd_args.base_dir)

    def test_with_no_force(self):
        sys_args = ['archy', 'groupname']
        with mock.patch('sys.argv', sys_args):
            cmd_args = _parse_args()
            self.assertFalse(cmd_args.force)

    def test_with_force_short(self):
        sys_args = ['archy', 'groupname', '-f']
        with mock.patch('sys.argv', sys_args):
            cmd_args = _parse_args()
            self.assertTrue(cmd_args.force)

    def test_with_force_long(self):
        sys_args = ['archy', 'groupname', '--force']
        with mock.patch('sys.argv', sys_args):
            cmd_args = _parse_args()
            self.assertTrue(cmd_args.force)


class MainTests(unittest.TestCase):
    """
    Basic tests for main.main
    """
    def test_no_args(self):
        self.assertRaises(SystemExit, main)

    def test_minimal_args(self):
        sys_args = ['archy', 'groupname']
        cwd = '/home'
        mock_getcwd = mock.MagicMock()
        mock_getcwd.return_value = cwd
        mock_runner = mock.MagicMock()
        mock_ArchiveRunner = mock.MagicMock(return_value=mock_runner)
        with mock.patch('sys.argv', sys_args):
            with mock.patch('os.getcwd', mock_getcwd):
                with mock.patch('archy.runner.ArchiveRunner', mock_ArchiveRunner):
                    main()
                    mock_ArchiveRunner.assert_called_with(
                        'groupname',
                        '/home',
                        False,
                    )
                    mock_runner.run.assert_called()


if __name__ == '__main__':
    unittest.main()  # pragma: no cover
