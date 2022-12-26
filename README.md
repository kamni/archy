# Archy

Command line tool for archiving files based on group membership.

## Explanation of Toy Project

This is a toy project with the following parameters:

```
A Python script should be implemented which moves all files from all members of
a group to an archive folder. The name of the group should be a parameter of
the program.

The program should be robust, e.g. with respect to multiple invocations in
short time. The events and results should be available in a log file.

The program should be installable as a Debian package and should be made
available for download. The Debian package does not have to be built, the
sources are sufficient.
```


## Design Decisions

### What is this project?

Normally when making design decisions for a project, it's good to ask "Why are
we doing this?" -- in this case, why are we archiving files for all members of
a group? The actual answer to this question may suggest implementation details
or even design flaws in the specification.

Additional questions that might follow from this:

* Are the files of these group members likely to be system-wide, or do we have
  some kind of shared server environment where people are sandboxed to
  particular directories?
* What do we want to do with this archive -- e.g., do we need to restore from
  it?
* Why are we moving files, instead of just copying them into the archive?
* Why are we doing this at the group level, and not a user level?
* Do we want to get rid of all files owned by the individuals, even if it is
  owned by another group?

For the purposes of this project (and also reasonable amount of programming
time), we're going to pretend the following are true:

1. Every summer we have groups of interns that collaborate on various projects
   together. We might have multiple groups in any one summer, working on
   different projects.
2. At the end of the summer, they hand over their respective projects (stored
   on another server). When they leave, we want to delete their personal
   files, including any shared group files, but we also want to make a backup.
3. The backup will mostly be used by sysadmins in case we need to recover
   project files, so we'll preserve the permissions and folder hierarchy.
4. If one of the interns did work for another group, we don't want that file
   to be archived.
5. If a non-intern has files belonging to the intern group, it's okay to archive
   it, because we assume that file belonged to the interns' project.
6. Interns have restricted privileges, so we don't need to worry about them
   having files in system folders. We will not include flags to exclude
   directories from search (e.g., `/proc`), and the script will actively
   complain if it's run with the `/` directory.
7. Additionally, removal of the interns' personal accounts is assumed to be
   handled as part of a separate administrative process, so we don't need to
   (for example) look up each intern's home directory and delete those files
   if they're located elsewhere in the system.

### Operating System and Python Version

This project was tested on a default install of Debian 11.6.0, against Python
3.9.2.

### Additional Design Decisions

To keep the scope of this project within reasonable time limits, the following
design decisions have been made:

* The script expects to be run as root and will complain if not run as root.
* The output archive isn't configurable. It will be set to
  `/tmp/<group-name>.tar`.
* We won't support compression (bzip, gzip) in this toy project.
* We will only support Linux file permissions and groups/users; e.g., no ACLs
  or LDAP.
* The user running the script must be root.
* The script can't be run from `/`; we won't provide any flags for excluding
  certain folders.
* Logging file is not configurable, and is set to
  `/var/log/archy/<group-name>.log`. 
* We won't clean up empty directories after the files have been moved.


## Development

This project currently requires Python 3.9.2. For running tests, it's fine to
use pyenv or another Python version manager, but for building the debian
packages you need a system Python installation compiled with debian-specific
support. If you use pyenv and your system version does not match 3.9.2, you may
want to set the following:

```
pyenv local system 3.9.2
```

Local development requires installing the packages in `requirements.txt`:

```
pip install -r requirements.txt
```

Please note that we use `stdeb` to build the debian package, and this may
require the installation of other system packages, such as `fakeroot` and
`debhelper`.


### Testing

To run tests:

```
tox
```

There is also a Docker image provided for testing, with some files ready for
archiving:
```
docker build -t archy .
docker run --rm -it archy
archy group1
```

### Building the .deb

To build the debian package:

```
python3 setup.py --command-packages=stdeb.command bdist_deb
```

To install the package:

```
sudo dpkg -i deb_dist/<version>.deb
sudo apt-get -f install
```

