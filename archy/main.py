"""
Main entry point into the archy script.
"""
import argparse
import os


__all__ = ['main']

_VERSION_ = '0.2.0'
_DESCRIPTION_ = """
Command line tool for archiving files based on group membership.
The files belonging to group members will be moved from their current location
to an uncompressed archive in the /tmp directory.
"""
_NOTES_ = """
NOTE: This script must be run as root, and can't be run from `/`.
"""


def _parse_args():
    # Future feature: flags to control verbosity of logging
    parser = argparse.ArgumentParser(
        prog='Archy',
        description=_DESCRIPTION_,
        epilog=_NOTES_,
    )
    parser.add_argument(
        'group',
        type=str,
        help='GROUP whose files should be archived',
    )
    parser.add_argument(
        '-d',
        '--base-dir',
        nargs='?',
        default=os.getcwd(),
        type=str,
        help=(
            'BASE_DIR to look for files. Cannot be /. '
            'If not specified, defaults to cwd'
        )
    )
    parser.add_argument(
        '-f',
        '--force',
        action='store_true',
        help='Force archiving of group, even if another process is running'
    )
    return parser.parse_args()


def main():
    # For setup.py, ArchiveRunner requires dependencies that haven't yet been
    # installed. In order to use `main` as an entry point, we need to move
    # this import here.
    from .runner import ArchiveRunner

    args = _parse_args()
    runner = ArchiveRunner(
        args.group,
        args.base_dir,
        args.force,
    )
    runner.run()
