import grp
import os
import pathlib
import tarfile
import unittest
from unittest import mock

import fasteners

from archy.runner import (
    ArchiveRunner,
    Group,
    _linux_group_to_archy_group,
)


class LinuxToArchyTests(unittest.TestCase):
    """
    Tests for conversion from linux system objects to archy classes.
    """
    def test_linux_group_to_archy_group(self):
        linux_group = ('group1', 'x', 222, ['foo', 'bar'])
        expected_group = Group(id=222, name='group1', members=['foo', 'bar'])
        self.assertEqual(
            expected_group,
            _linux_group_to_archy_group(linux_group),
        )


def _mock_linux_user_call(name='root'):
    mock_getuser = mock.MagicMock(return_value=name)
    return mock_getuser


def _mock_linux_group_call(id=1500, name='notagroup', members=None):
    members = members if members is not None else ['user1', 'user2']
    mock_getgrnam = mock.MagicMock(return_value=(name, 'x', id, members))
    return mock_getgrnam


class ArchiveRunnerTests(unittest.TestCase):
    """
    Tests for runner.ArchiveRunner
    """
    TESTFILE_DIR = '/tmp/archy-test'
    TESTFILE_BASE = 'archy-test'

    def _get_testfile_name(self, file_extension: str) -> str:
        return self.TESTFILE_DIR + '/' + self.TESTFILE_BASE + file_extension

    def _get_runner(self, **kwargs):
        default = {
            'group_name': 'notagroup',
            'base_dir': self.TESTFILE_DIR,
            'force_archive': False,
            'logfile_base': self._get_testfile_name('.log'),
            'lockfile_base': self._get_testfile_name('.lock'),
            'tarfile_base': self._get_testfile_name('.tar'),
        }
        default.update(kwargs)
        return ArchiveRunner(**default)

    def _get_group(self, **kwargs):
        default = {
            'id': 1500,
            'name': 'notagroup',
            'members': ['user1', 'user2'],
        }
        default.update(kwargs)
        return Group(**default)

    def setUp(self):
        try:
            pathlib.Path(self.TESTFILE_DIR).mkdir()
        except FileExistsError:  # pragma: no cover
            pass

        self.group = self._get_group()
        self.runner = self._get_runner()

    def tearDown(self):
        def rm(item):
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                for subitem in item.rglob('*'):
                    rm(subitem)
                item.rmdir()

        directory = pathlib.Path(self.TESTFILE_DIR)
        rm(directory)

    def test_acquire_process_lock_integration_success(self):
        self.assertTrue(self.runner._acquire_process_lock())
        self.assertIsNotNone(self.runner.lock)

        self.runner.lock.release()

    def test_acquire_process_lock_integration_not_successful(self):
        mock_lock = mock.MagicMock()
        mock_lock.acquire.return_value = False
        mock_InterProcessLock = mock.MagicMock(return_value=mock_lock)
        with mock.patch('fasteners.InterProcessLock', mock_InterProcessLock):
            self.assertFalse(self.runner._acquire_process_lock())
            self.assertIsNotNone(self.runner.lock)

    def test_acquire_process_lock_force(self):
        runner = self._get_runner(force_archive=True)
        mock_lock = mock.MagicMock()
        mock_lock.acquire.return_value = False
        mock_InterProcessLock = mock.MagicMock(return_value=mock_lock)
        with mock.patch('fasteners.InterProcessLock', mock_InterProcessLock):
            self.assertTrue(runner._acquire_process_lock())
            self.assertIsNone(runner.lock)

    def test_archive_file_integration(self):
        testfile_name = self._get_testfile_name('.txt')
        pathlib.Path(testfile_name).touch()

        tarfile_name = self._get_testfile_name('.tar')
        with tarfile.open(tarfile_name, 'a') as tar:
            self.runner._archive_file(testfile_name, tar)
            expected_files = [testfile_name.split('/', 1)[1]]
            self.assertEqual(expected_files, tar.getnames())

    def test_archive_files_for_group_integration(self):
        dirpath = pathlib.Path(f'{self.TESTFILE_DIR}/bar')
        group = _linux_group_to_archy_group(grp.getgrgid(os.getgid()))
        runner = self._get_runner(
            group_name=group.name,
            base_dir=dirpath,
        )
        expected_filenames = []
        dirpath.mkdir()
        for file_ext in ['1.txt', '2.txt', '3.txt']:
            filename = f'{self.TESTFILE_DIR}/bar/test{file_ext}'
            expected_filenames.append(filename.split('/', 1)[1])
            pathlib.Path(filename).touch()

        subdirpath = pathlib.Path(f'{self.TESTFILE_DIR}/bar/baz')
        subdirpath.mkdir()
        for file_ext in ['4.txt', '5.txt', '6.txt']:
            filename = f'{self.TESTFILE_DIR}/bar/baz/test{file_ext}'
            expected_filenames.append(filename.split('/', 1)[1])
            pathlib.Path(filename).touch()

        runner._archive_files_for_group(group)
        with tarfile.open(runner._get_tarfile_name(), 'r') as tar:
            self.assertEqual(
                set(tar.getnames()),
                set(expected_filenames),
            )

        # Testing deletion
        files = [filepath for filepath in dirpath.rglob('*')
                 if filepath.is_file()]
        self.assertEqual([], files)

    def test_archive_files_for_group(self):
        group = self._get_group()

        file1 = mock.MagicMock()
        file1.is_file.return_value = True
        file1.owner.return_value = 'user1'
        file1.group.return_value = group.name
        file1.absolute.return_value = file1
        file1.as_posix.return_value = self._get_testfile_name('-file1.txt')

        file2 = mock.MagicMock()
        file2.is_file.return_value = True
        file2.owner.return_value = 'some_user'
        file2.group.return_value = 'some_group'
        file2.absolute.return_value = file2
        file2.as_posix.return_value = self._get_testfile_name('-file2.txt')

        mock_tar = mock.MagicMock()
        mock_delete = mock.MagicMock()
        with mock.patch.multiple(
                'archy.runner.ArchiveRunner',
                _delete_file=mock_delete,
                _get_files=mock.MagicMock(return_value=[file1, file2]),
                _open_archive=mock.MagicMock(return_value=mock_tar),
        ):
            self.assertEqual(1, self.runner._archive_files_for_group(group))
            mock_tar.__enter__().add.assert_called_once_with(file1.as_posix())
            mock_delete.assert_called_once_with(file1)

    def test_archive_files_for_group_no_files(self):
        group = self._get_group()
        with mock.patch(
                'archy.runner.ArchiveRunner._get_files',
                mock.MagicMock(return_value=[]),
        ):
            self.assertEqual(0, self.runner._archive_files_for_group(group))

    def test_archive_files_for_group_cant_get_lock(self):
        group = self._get_group()

        file1 = mock.MagicMock()
        file1.is_file.return_value = True
        file1.owner.return_value = 'user1'
        file1.group.return_value = group.name
        file1.absolute.return_value = file1
        file1.as_posix.return_value = self._get_testfile_name('-file1.txt')

        file2 = mock.MagicMock()
        file2.is_file.return_value = True
        file2.owner.return_value = 'user1'
        file2.group.return_value = group.name
        file2.absolute.return_value = file2
        file2.as_posix.return_value = self._get_testfile_name('-file2.txt')

        mock_tar = mock.MagicMock()
        mock_delete = mock.MagicMock()
        with mock.patch.multiple(
                'archy.runner.ArchiveRunner',
                _delete_file=mock_delete,
                _get_filelock=mock.MagicMock(side_effect=[mock.MagicMock(), None]),
                _get_files=mock.MagicMock(return_value=[file1, file2]),
                _open_archive=mock.MagicMock(return_value=mock_tar),
        ):
            self.assertEqual(1, self.runner._archive_files_for_group(group))
            mock_tar.__enter__().add.assert_called_once_with(file1.as_posix())
            mock_delete.assert_called_once_with(file1)

    def test_archive_files_for_group_when_file_errors(self):
        group = self._get_group()

        file1 = mock.MagicMock()
        file1.is_file.return_value = True
        file1.owner.return_value = 'user1'
        file1.group.return_value = group.name
        file1.absolute.return_value = file1
        file1.as_posix.return_value = self._get_testfile_name('-file1.txt')

        file2 = mock.MagicMock()
        file2.is_file.return_value = True
        file2.owner.return_value = 'user1'
        file2.group.return_value = group.name
        file2.absolute.return_value = file2
        file2.as_posix.return_value = self._get_testfile_name('-file2.txt')

        mock_tar = mock.MagicMock()
        mock_archive = mock.MagicMock(side_effect=[None, Exception()])
        mock_delete = mock.MagicMock()
        mock_lock1 = mock.MagicMock()
        mock_lock2 = mock.MagicMock()
        with mock.patch.multiple(
                'archy.runner.ArchiveRunner',
                _archive_file=mock_archive,
                _delete_file=mock_delete,
                _get_filelock=mock.MagicMock(side_effect=[mock_lock1, mock_lock2]),
                _get_files=mock.MagicMock(return_value=[file1, file2]),
                _open_archive=mock.MagicMock(return_value=mock_tar),
        ):
            self.assertEqual(1, self.runner._archive_files_for_group(group))
            mock_delete.assert_called_once_with(file1)
            # Even though file2 errors, it should release both locks
            mock_lock1.release.assert_called_once()
            mock_lock2.release.assert_called_once()

    def test_current_user_has_permissions_false(self):
        self.assertFalse(self.runner._current_user_has_permissions('user1'))

    def test_current_user_has_permissions_true(self):
        self.assertTrue(self.runner._current_user_has_permissions('root'))

    def test_delete_file_integration(self):
        filename = self._get_testfile_name('-deleteme.txt')
        filepath = pathlib.Path(filename)
        filepath.touch()
        self.assertTrue(filepath.exists())
        self.runner._delete_file(filepath)
        self.assertFalse(filepath.exists())

    def test_directory_exists_true(self):
        self.assertTrue(self.runner._directory_exists())

    def test_directory_exists_false(self):
        runner = self._get_runner(base_dir='foobar')
        self.assertFalse(runner._directory_exists())

    def test_get_absolute_path(self):
        expected_path = pathlib.Path('foo').absolute().as_posix()
        self.assertEqual(expected_path, self.runner._get_absolute_path('foo'))

    def test_get_current_user(self):
        expected_user = 'root'
        mock_getuser = _mock_linux_user_call(expected_user)
        with mock.patch('getpass.getuser', mock_getuser):
            self.assertEqual(expected_user, self.runner._get_current_user())

    def test_get_filelock_true(self):
        mock_lock = mock.MagicMock()
        mock_lock.acquire.return_value = True
        mock_InterProcessLock = mock.MagicMock(return_value=mock_lock)
        with mock.patch('fasteners.InterProcessLock', mock_InterProcessLock):
            self.assertEqual(mock_lock, self.runner._get_filelock('/home/user1/foo.txt'))

    def test_get_filelock_false(self):
        mock_lock = mock.MagicMock()
        mock_lock.acquire.return_value = False
        mock_InterProcessLock = mock.MagicMock(return_value=mock_lock)
        with mock.patch('fasteners.InterProcessLock', mock_InterProcessLock):
            self.assertIsNone(self.runner._get_filelock('/home/user1/foo.txt'))

    def test_get_filename_integration(self):
        filepath = pathlib.Path()
        expected_filename = filepath.absolute().as_posix()
        self.assertEqual(expected_filename, self.runner._get_filename(filepath))

    def test_get_files_integration(self):
        dirpath = pathlib.Path(f'{self.TESTFILE_DIR}/foo')
        runner = self._get_runner(base_dir=dirpath)
        expected_filenames = []
        dirpath.mkdir()
        for file_ext in ['1.txt', '2.txt', '3.txt']:
            filename = f'{self.TESTFILE_DIR}/foo/test{file_ext}'
            expected_filenames.append(filename)
            pathlib.Path(filename).touch()

        self.assertEqual(
            set(expected_filenames),
            set([fl.absolute().as_posix() for fl in runner._get_files()]),
        )

    def test_get_files(self):
        dir1 = mock.MagicMock()
        dir2 = mock.MagicMock()
        file1 = mock.MagicMock()
        file2 = mock.MagicMock()
        expected_files = [dir1, file1, dir2, file2]
        mock_path = mock.MagicMock()
        mock_path.rglob.return_value = expected_files
        mock_PathCls = mock.MagicMock(return_value=mock_path)
        with mock.patch('pathlib.Path', mock_PathCls):
            self.assertEqual(expected_files, self.runner._get_files())

    def test_get_group_exists_true_no_members(self):
        mock_getgrnam = _mock_linux_group_call(members=[])
        expected_group = self._get_group(members=[])
        with mock.patch('grp.getgrnam', mock_getgrnam):
            print('foo')
            self.assertEqual(expected_group, self.runner._get_group())

    def test_get_group_exists_true_with_members(self):
        mock_getgrnam = _mock_linux_group_call()
        expected_group = self._get_group()
        with mock.patch('grp.getgrnam', mock_getgrnam):
            self.assertEqual(expected_group, self.runner._get_group())

    def test_get_group_exists_false(self):
        self.assertIsNone(self.runner._get_group())

    def test_get_lockfile_name_default(self):
        runner = ArchiveRunner(
            'testgroup',
            '/home',
            logfile_base=self._get_testfile_name('.log'),
        )
        expected_name = ArchiveRunner.LOCKFILE_BASE % 'testgroup'
        self.assertEqual(expected_name, runner._get_lockfile_name())

    def test_get_lockfile_name_specified_base(self):
        runner = self._get_runner(
            group_name='testgroup',
            lockfile_base='foo-%s-bar.lock',
        )
        expected_name = 'foo-testgroup-bar.lock'
        self.assertEqual(expected_name, runner._get_lockfile_name())

    def test_get_lockfile_name_no_formatting(self):
        runner = self._get_runner(
            group_name='testgroup',
            lockfile_base='foo-bar.lock',
        )
        expected_name = 'foo-bar.lock'
        self.assertEqual(expected_name, runner._get_lockfile_name())

    def test_get_logfile_name_specified_base(self):
        runner = self._get_runner(
            group_name='testgroup',
            logfile_base='foo-%s-bar.log',
        )
        expected_name = 'foo-testgroup-bar.log'
        self.assertEqual(expected_name, runner._get_logfile_name())

    def test_get_logfile_name_no_formatting(self):
        runner = self._get_runner(
            group_name='testgroup',
            logfile_base='foo-bar.log',
        )
        expected_name='foo-bar.log'
        self.assertEqual(expected_name, runner._get_logfile_name())

    def test_get_tarfile_name_default(self):
        runner = ArchiveRunner(
            'testgroup',
            '/home',
            logfile_base=self._get_testfile_name('.log'),
        )
        expected_name = ArchiveRunner.TARFILE_BASE % 'testgroup'
        self.assertEqual(expected_name, runner._get_tarfile_name())

    def test_get_tarfile_name_specified_base(self):
        runner = self._get_runner(
            group_name='testgroup',
            tarfile_base='/tmp/foo-%s-bar.tar',
        )
        expected_name = '/tmp/foo-testgroup-bar.tar'
        self.assertEqual(expected_name, runner._get_tarfile_name())

    def test_get_tarfile_name_no_formatting(self):
        runner = self._get_runner(
            group_name='testgroup',
            tarfile_base='/tmp/foo-bar.tar',
        )
        expected_name = '/tmp/foo-bar.tar'
        self.assertEqual(expected_name, runner._get_tarfile_name())

    def test_is_root_directory_true(self):
        runner = self._get_runner(base_dir='/')
        self.assertTrue(runner._is_root_directory())

    def test_is_root_directory_false(self):
        runner = self._get_runner(base_dir='/home')
        self.assertFalse(runner._is_root_directory())

    def test_log_debug(self):
        runner = self._get_runner()
        runner.logger = mock.MagicMock()
        runner._log_debug('%s: %s', 1, 2, foo=1, bar=2)
        runner.logger.debug.assert_called_once_with(
            '%s: %s', 1, 2, extra={'foo': 1, 'bar': 2, 'level': 'DEBUG'},
        )

    def test_log_error(self):
        runner = self._get_runner()
        runner.logger = mock.MagicMock()
        runner._log_error('%s: %s', 1, 2, foo=1, bar=2)
        runner.logger.error.assert_called_once_with(
            '%s: %s', 1, 2, extra={'foo': 1, 'bar': 2, 'level': 'ERROR'},
        )

    def test_log_info(self):
        runner = self._get_runner()
        runner.logger = mock.MagicMock()
        runner._log_info('%s: %s', 1, 2, foo=1, bar=2)
        runner.logger.info.assert_called_once_with(
            '%s: %s', 1, 2, extra={'foo': 1, 'bar': 2, 'level': 'INFO'},
        )

    def test_open_archive_integration(self):
        tarfile_name = self._get_testfile_name('.tar')
        tar = self.runner._open_archive(tarfile_name)
        self.assertEqual(tarfile.TarFile, type(tar))
        self.assertEqual(tarfile_name, tar.name)
        self.assertFalse(tar.closed)

        tar.close()

    def test_release_filelock_integration(self):
        filelock_file = self._get_testfile_name('-file.lock')
        filelock = fasteners.InterProcessLock(filelock_file)
        self.assertTrue(filelock.acquire())
        self.runner._release_filelock(filelock)
        self.assertFalse(filelock.acquired)

    def test_release_process_lock_integration(self):
        runner = self._get_runner()
        self.assertTrue(runner._acquire_process_lock())
        self.assertTrue(runner.lock.acquired)
        runner._release_process_lock()
        self.assertFalse(runner.lock.acquired)

    def test_release_process_lock_integration_never_acquired(self):
        runner = self._get_runner()
        filelock_file = self._get_testfile_name('-process.lock')
        runner.lock = fasteners.InterProcessLock(filelock_file)
        self.assertFalse(runner.lock.acquired)
        runner._release_process_lock()
        self.assertFalse(runner.lock.acquired)

    def test_should_archive_integration(self):
        filepath = pathlib.Path(self._get_testfile_name('-foo.txt'))
        filepath.touch()
        self.assertFalse(self.runner._should_archive(filepath, self.group))

    def test_should_archive_true_group(self):
        file1 = mock.MagicMock()
        file1.is_file.return_value = True
        file1.owner.return_value = 'some_user'
        file1.group.return_value = self.runner.group_name
        self.assertTrue(self.runner._should_archive(file1, self.group))

    def test_should_archive_true_user(self):
        user_name = 'user1'
        file1 = mock.MagicMock()
        file1.is_file.return_value = True
        file1.owner.return_value = user_name
        file1.group.return_value = user_name
        self.assertTrue(self.runner._should_archive(file1, self.group))

    def test_should_archive_false_directory(self):
        file1 = mock.MagicMock()
        file1.is_file.return_value = False
        file1.owner.return_value = 'user1'
        file1.group.return_value = self.runner.group_name
        self.assertFalse(self.runner._should_archive(file1, self.group))

    def test_should_archive_false_user_with_wrong_group(self):
        file1 = mock.MagicMock()
        file1.is_file.return_value = True
        file1.owner.return_value = 'user1'
        file1.group.return_value = 'some_group'
        self.assertFalse(self.runner._should_archive(file1, self.group))

    def test_should_archive_false_wrong_user_and_group(self):
        file1 = mock.MagicMock()
        file1.is_file.return_value = True
        file1.owner.return_value = 'some_user'
        file1.group.return_value = 'some_group'
        self.assertFalse(self.runner._should_archive(file1, self.group))

    def test_run_user_has_permission(self):
        mock_logger = mock.MagicMock()
        with mock.patch.multiple(
                'archy.runner.ArchiveRunner',
                _get_current_user=mock.MagicMock(return_value='user'),
                _is_root_directory=mock.MagicMock(return_value=False),
                _directory_exists=mock.MagicMock(return_value=True),
                _get_group=mock.MagicMock(return_value=self._get_group()),
                _acquire_process_lock=mock.MagicMock(return_value=True),
                _log_error=mock_logger,
        ):
            self.assertRaises(SystemExit, self.runner.run)
            mock_logger.assert_called_once_with(
                'Non-root user tried to run archy',
                user='user',
            )

    def test_run_is_root_directory(self):
        with mock.patch.multiple(
                'archy.runner.ArchiveRunner',
                _current_user_has_permissions=mock.MagicMock(return_value=True),
                _is_root_directory=mock.MagicMock(return_value=True),
                _directory_exists=mock.MagicMock(return_value=True),
                _get_group=mock.MagicMock(return_value=self._get_group()),
                _acquire_process_lock=mock.MagicMock(return_value=True),
        ):
            self.assertRaises(SystemExit, self.runner.run)

    def test_run_directory_doesnt_exist(self):
        with mock.patch.multiple(
                'archy.runner.ArchiveRunner',
                _current_user_has_permissions=mock.MagicMock(return_value=True),
                _is_root_directory=mock.MagicMock(return_value=False),
                _directory_exists=mock.MagicMock(return_value=False),
                _get_group=mock.MagicMock(return_value=self._get_group()),
                _acquire_process_lock=mock.MagicMock(return_value=True),
        ):
            self.assertRaises(SystemExit, self.runner.run)

    def test_run_group_doesnt_exist(self):
        with mock.patch.multiple(
                'archy.runner.ArchiveRunner',
                _current_user_has_permissions=mock.MagicMock(return_value=True),
                _is_root_directory=mock.MagicMock(return_value=False),
                _directory_exists=mock.MagicMock(return_value=True),
                _get_group=mock.MagicMock(return_value=None),
                _acquire_process_lock=mock.MagicMock(return_value=True),
        ):
            self.assertRaises(SystemExit, self.runner.run)

    def test_run_cant_acquire_process_lock(self):
        with mock.patch.multiple(
                'archy.runner.ArchiveRunner',
                _current_user_has_permissions=mock.MagicMock(return_value=True),
                _is_root_directory=mock.MagicMock(return_value=False),
                _directory_exists=mock.MagicMock(return_value=True),
                _get_group=mock.MagicMock(return_value=self._get_group()),
                _acquire_process_lock=mock.MagicMock(return_value=False),
        ):
            self.assertRaises(SystemExit, self.runner.run)

    def test_run_no_files(self):
        with mock.patch.multiple(
                'archy.runner.ArchiveRunner',
                _current_user_has_permissions=mock.MagicMock(return_value=True),
                _is_root_directory=mock.MagicMock(return_value=False),
                _directory_exists=mock.MagicMock(return_value=True),
                _get_group=mock.MagicMock(return_value=self._get_group()),
                _acquire_process_lock=mock.MagicMock(return_value=True),
                _get_files=mock.MagicMock(return_value=[]),
        ):
            self.assertRaises(SystemExit, self.runner.run)

    def test_run_miscellaneous_error(self):
        file1 = mock.MagicMock()
        file1.is_file.return_value = True
        file1.owner.return_value = 'user1'
        file1.group.return_value = self.runner.group_name
        file1.absolute.return_value = file1
        file1.as_posix.return_value = self._get_testfile_name('-file1.txt')

        with mock.patch.multiple(
                'archy.runner.ArchiveRunner',
                _current_user_has_permissions=mock.MagicMock(return_value=True),
                _is_root_directory=mock.MagicMock(return_value=False),
                _directory_exists=mock.MagicMock(return_value=True),
                _get_group=mock.MagicMock(return_value=self._get_group()),
                _get_files=mock.MagicMock(return_value=[file1]),
                _open_archive=mock.MagicMock(side_effect=Exception()),
        ):
            self.runner.run()
            # It should have released the process lock
            self.assertIsNotNone(self.runner.lock)
            self.assertFalse(self.runner.lock.acquired)

    def test_run(self):
        group = self._get_group()

        file1 = mock.MagicMock()
        file1.is_file.return_value = True
        file1.owner.return_value = 'user1'
        file1.group.return_value = group.name
        file1.absolute.return_value = file1
        file1.as_posix.return_value = self._get_testfile_name('-file1.txt')

        file2 = mock.MagicMock()
        file2.is_file.return_value = True
        file2.owner.return_value = 'some_user'
        file2.group.return_value = 'some_group'
        file2.absolute.return_value = file2
        file2.as_posix.return_value = self._get_testfile_name('-file2.txt')

        mock_tar = mock.MagicMock()
        mock_delete = mock.MagicMock()
        with mock.patch.multiple(
                'archy.runner.ArchiveRunner',
                _current_user_has_permissions=mock.MagicMock(return_value=True),
                _is_root_directory=mock.MagicMock(return_value=False),
                _directory_exists=mock.MagicMock(return_value=True),
                _get_group=mock.MagicMock(return_value=group),
                _delete_file=mock_delete,
                _get_files=mock.MagicMock(return_value=[file1, file2]),
                _open_archive=mock.MagicMock(return_value=mock_tar),
        ):
            self.runner.run()
            mock_tar.__enter__().add.assert_called_once_with(file1.as_posix())
            mock_delete.assert_called_once_with(file1)
            # It should have released the process lock
            self.assertIsNotNone(self.runner.lock)
            self.assertFalse(self.runner.lock.acquired)


if __name__ == '__main__':
    unittest.main()  # pragma: no cover
