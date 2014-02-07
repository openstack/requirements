Global dependencies for OpenStack Projects

All official OpenStack projects should be added to
projects.txt. Once they are added here the gate/check
jobs for the projects will use the OpenStack
internal pypi mirror to ensure stability. The
continuous integration infrastructure will also
sync up the requirements across all the official
projects and will create reviews in the participating
projects for any mis-matches.

This process above will ensure that users of OpenStack
will have one single set of python package requirements/
dependencies to install and run the individual OpenStack
components.

To use this, run:

  python update.py path/to/project

Entries in requirements.txt and test-requirements.txt
will have their versions updated to match the entires
listed here. Any entries in the target project which
do not first exist here will be removed. No entries
will be added.
