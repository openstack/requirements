Global dependencies for OpenStack Projects

To use this, run:

  python update.py path/to/project

Entries in tools/pip-requires and tools/test-requires
will have their versions updated to match the entires
listed here. Any entries in the target project which
do not first exist here will be removed. No entries
will be added.
