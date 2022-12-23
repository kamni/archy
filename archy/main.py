"""
Main entry point into the archy script.
"""
import argparse
import os

__all__ = ['main']

_VERSION_ = '0.1.0'
_DESCRIPTION_ = """
Command line tool for archiving files based on group membership.
The files belonging to group members will be moved from their current location
to an uncompressed archive in the /tmp directory.
"""
_NOTES_ = """
NOTE: This script must be run as root.
"""


def _parse_args():
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
    args = _parse_args()


if __name__ == '__main__':
    main()
