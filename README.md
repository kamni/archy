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

### Operating System and Python Version

This project was tested on a default install of Debian 11.6.0, against Python
3.9.2.

### Additional Design Decisions

To keep the scope of this project within reasonable time limits, the following
design decisions have been made:

* The script expects to be run as root and will complain if not run as root.
* The output archive isn't configurable. It will be set to
  `/tmp/<group-name>.tgz`.
* We won't support compression (bzip, gzip) in this toy project.
* We will only support Linux file permissions; no ACLs.
* If the user running the script doesn't have permissions to 
* Logging file is not configurable, and is set to
  `/var/log/archy/<group-name>.log`. The permissions on the folder will be
  755 (root:root) and the file 644.
