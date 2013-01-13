Global dependencies for OpenStack Projects

To use this, run:

  python update.py path/to/project

Entries in requirements.txt and test-requirements.txt
will have their versions updated to match the entires
listed here. Any entries in the target project which
do not first exist here will be removed. No entries
will be added.
