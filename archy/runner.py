import getpass
import grp
import logging
import pathlib
import sys
import tarfile
from typing import Any, Dict, Iterable, List, Optional

import fasteners  # type: ignore[import]
from pydantic import BaseModel
from pythonjsonlogger import jsonlogger  # type: ignore[import]

from .logger import ExtraStreamHandler


__all__ = ['ArchiveRunner']


class Group(BaseModel):
    """
    Represents a group on the linux system.
    """
    id: int
    name: str
    members: List[str]


def _linux_group_to_archy_group(linux_group: Any) -> Group:
    # Requires a grp.struct_group or a tuple/list with a similar format.
    # Note: can't convert the group members, because that requires a system
    # lookup. That must be handled separately.
    return Group(
        id=linux_group[2],
        name=linux_group[0],
        members=linux_group[3],
    )


class ArchiveRunner:
    """
    Coordinates the actions of finding group files and moving them to an archive
    """
    LOCKFILE_BASE = '/var/run/archy-%s.lock'
    LOGFILE_BASE = '/var/log/archy.%s.log'
    TARFILE_BASE = '/tmp/archy-%s.tar'

    def __init__(self, group_name: str, base_dir: str,
                 force_archive: bool = False,
                 logfile_base: str = LOGFILE_BASE,
                 lockfile_base: str = LOCKFILE_BASE,
                 tarfile_base: str = TARFILE_BASE):
        self.group_name = group_name
        self.base_dir = self._get_absolute_path(base_dir)
        self.force_archive = force_archive
        self.logfile_base = logfile_base
        self.lockfile_base = lockfile_base
        self.tarfile_base = tarfile_base

        self.lock: Optional[fasteners.InterProcessLock] = None
        self.logger: Optional[logging.Logger] = None

    def _acquire_process_lock(self) -> bool:
        if self.force_archive:
            return True

        self.lock = fasteners.InterProcessLock(self._get_lockfile_name())
        return self.lock.acquire(blocking=False)

    def _archive_file(self, filename: str, tar: tarfile.TarFile):
        tar.add(filename)

    def _archive_files_for_group(self, group: Group):
        # Design Decision: if we were planning to implement this in hexagonal
        # architecture, we'd separate out the reading/deleting of the files
        # from the writing of the archive. This would make it easier to
        # implement a runner that could handle archiving from another server
        # to the current server; the down side to this is that it would force
        # us to make multiple passes through the files, and in large file sets
        # we'd need to check the file again with each pass. For this toy
        # project, we'll just keep this to one pass.
        linux_files = self._get_files()
        archived_file_count = 0
        not_transferred = 0
        tarfile_name = self._get_tarfile_name()
        # Future feature: clean up empty directories
        with self._open_archive(tarfile_name) as tar:
            for fl in linux_files:
                filename = self._get_filename(fl)
                try:
                    if self._should_archive(fl, group):
                        self._log_debug(
                            'Acquiring file lock to transfer file',
                            file_name=filename,
                        )
                        file_lock = self._get_filelock(filename)
                        if not file_lock:
                            # Possible future feature: create a retry queue.
                            # But given this script can be run multiple times,
                            # missed files can just be appended to the archive
                            # after they're no longer in use by re-running this
                            # script.
                            not_transferred += 1
                            self._log_error(
                                'Unable to transfer file. File in use',
                                file_name=filename,
                            )
                            continue

                        try:
                            self._log_debug(
                                'Archiving file',
                                file_name=filename,
                            )
                            self._archive_file(filename, tar)

                            self._log_debug(
                                'Deleting file',
                                file_name=filename,
                            )
                            self._delete_file(fl)
                            archived_file_count += 1

                            self._log_info(
                                'File successfully archived',
                                file_name=filename,
                            )

                        finally:
                            self._release_filelock(file_lock)

                    elif fl.is_file():
                        self._log_debug(
                            'Not archiving file. Wrong ownership',
                            file_name=filename,
                        )

                except Exception as ex:
                    not_transferred += 1
                    self._log_error(
                        'Unable to transfer file',
                        file_name=filename,
                        error=ex,
                    )

        if not_transferred:
            self._log_error(
                ('Some files were not transferred. '
                 'Please fix problems, and rerun this script'),
                not_transferred_count=not_transferred,
            )
        if archived_file_count == 0:
            self._log_error(
                ('No files transferred to archive. '
                 'You may want to manually delete %s if it is empty'),
                tarfile_name,
            )

        return archived_file_count

    def _current_user_has_permissions(self, user: str) -> bool:
        return user == 'root'

    def _delete_file(self, filepath: pathlib.Path):
        filepath.unlink()

    def _directory_exists(self) -> bool:
        return pathlib.Path(self.base_dir).is_dir()

    def _get_absolute_path(self, base_dir: str) -> str:
        return pathlib.Path(base_dir).absolute().as_posix()

    def _get_current_user(self) -> str:
        return getpass.getuser()

    def _get_filelock(self, filename: str) -> Optional[fasteners.InterProcessLock]:
        # Given that we're going to delete this file in a moment,
        # let's exclude all access, including reads
        filelock = fasteners.InterProcessLock(filename)
        if filelock.acquire(blocking=True, timeout=5):
            return filelock
        return None

    def _get_filename(self, filepath: pathlib.Path) -> str:
        return filepath.absolute().as_posix()

    def _get_files(self) -> Iterable[pathlib.Path]:
        # Design note: rglob silently ignores files it can't access, which means
        # we can't necessarily log files that we're not able to transfer (hence
        # one reason to run this script only as root). We may want to consider
        # whether there are alternatives that would give an error.
        return pathlib.Path(self.base_dir).rglob('*')

    def _get_group(self) -> Optional[Group]:
        try:
            linux_group = grp.getgrnam(self.group_name)
            return _linux_group_to_archy_group(linux_group)
        except KeyError:
            # The group wasn't found
            return None

    def _get_lockfile_name(self) -> str:
        try:
            return self.lockfile_base % self.group_name
        except TypeError:
            return self.lockfile_base

    def _get_log_extra(self, extra_kwargs: Dict, loglevel: int) -> Dict:
        # TODO: this is manually added, because right now there doesn't
        # seem to be a way to add levelname to pythonjsonlogger, which seems
        # odd. Do some more research into the 2.0.1 docs to see if we're
        # missing something.
        level_str = {
            logging.DEBUG: 'DEBUG',
            logging.INFO: 'INFO',
            logging.ERROR: 'ERROR',
            logging.CRITICAL: 'CRITICAL',
        }.get(loglevel, 'NOTSET')
        # pythonjsonlogger has a `static_fields` option in 3.0.4 that allows
        # us to add these automatically. Unfortunately, it's not yet supported
        # in 2.0.1, which is the debian version.
        extra_kwargs.update({
            'level': level_str,
            'group': self.group_name,
            'dirname': self.base_dir,
            'destination_tar': self._get_tarfile_name(),
        })
        return extra_kwargs

    def _get_logfile_name(self):
        try:
            return self.logfile_base % self.group_name
        except TypeError:
            return self.logfile_base

    def _get_logger(self) -> logging.Logger:
        # Future feature: make the logger configurable
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        # For logging to the console while running
        cmdln_handler = ExtraStreamHandler(
            stream=sys.stdout,
            exclude_extra=['level', 'group', 'dirname', 'destination_tar'],
        )
        cmdln_handler.setLevel(logging.INFO)
        cmdln_formatter = logging.Formatter(
            '[%(levelname)s] %(message)s',
        )
        cmdln_handler.setFormatter(cmdln_formatter)
        logger.addHandler(cmdln_handler)

        # For longer-term records, let's use structured logging
        file_handler = logging.FileHandler(self._get_logfile_name())
        file_handler.setLevel(logging.DEBUG)
        file_formatter = jsonlogger.JsonFormatter(timestamp=True)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        return logger

    def _get_tarfile_name(self) -> str:
        try:
            return self.tarfile_base % self.group_name
        except TypeError:
            return self.tarfile_base

    def _is_root_directory(self) -> bool:
        return pathlib.Path('/') == pathlib.Path(self.base_dir)

    def _log(self, loglevel: int, msg: str, *args, **kwargs):
        extra = self._get_log_extra(kwargs, loglevel)
        try:
            self.logger.log(loglevel, msg, *args, extra=extra)  # type: ignore[union-attr]
        except AttributeError:
            # We don't actually instantiate the logger until the first time
            # it is used. This is to prevent permissions errors when creating
            # an instance of the class, when the logger points to a file where
            # the user has insufficient permissions.
            self.logger = self._get_logger()
            self.logger.log(loglevel, msg, *args, extra=extra)

    def _log_debug(self, msg: str, *args, **kwargs):
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def _log_error(self, msg: str, *args, **kwargs):
        self._log(logging.ERROR, msg, *args, **kwargs)

    def _log_info(self, msg: str, *args, **kwargs):
        self._log(logging.INFO, msg, *args, **kwargs)

    def _open_archive(self, tarfile_name: str):
        # Design Decision: we always want to open this as append, so if we
        # run the script multiple times (e.g., we needed to fix permissions on
        # a file and rerun) it won't overwrite the existing archive.
        # This is another reason for not supporting compression, as tarfile
        # doesn't allow appending to a compressed file. We can always manually
        # compress the archive after running the script.
        return tarfile.open(tarfile_name, 'a')

    def _release_filelock(self, lock):
        lock.release()

    def _release_process_lock(self):
        try:
            if self.lock:
                self.lock.release()
        except RuntimeError:
            # Lock was never acquired, but we ran anyhow
            pass

    def _should_archive(self, fl: pathlib.Path, group: Group) -> bool:
        # We archive files if:
        # 1. The file belongs to the group.
        # 2. The file belongs solely to the group user.
        # We don't archive files if it belongs to the user but also belongs
        # to another group.
        group_name = fl.group()
        user_name = fl.owner()
        is_file = fl.is_file()
        is_group_file = group_name == group.name
        is_user_file = user_name in group.members and user_name == group_name
        return is_file and (is_group_file or is_user_file)

    def run(self):
        user = self._get_current_user()
        if not self._current_user_has_permissions(user):
            sys.exit('[ERROR] Please run archy as root')

        if self._is_root_directory():
            sys.exit(
                ('[ERROR] Archy is not safe to run from the root directory. '
                 'Please specify --base-dir'),
            )
        if not self._directory_exists():
            sys.exit(f'[ERROR] Invalid directory: {self.base_dir}')

        group = self._get_group()
        if not group:
            sys.exit(f'[ERROR] Invalid group name: {self.group_name}')

        if not self._acquire_process_lock():
            sys.exit(
                ('[ERROR] Another archy process is already running for this '
                 'group. Wait for it to finish, or use --force to run anyhow.'),
            )

        self._log_info('Beginning archive')
        archived_file_count = -1
        try:
            archived_file_count = self._archive_files_for_group(group)
        except Exception as ex:
            self._log_error('Unrecoverable error', error=ex)
        finally:
            self._release_process_lock()

        if archived_file_count == 0:
            self._log_error(
                'No files for group %s found in directory %s',
                self.group_name,
                self.base_dir,
            )
        else:
            self._log_info('Archiving completed')
