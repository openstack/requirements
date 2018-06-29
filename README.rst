============================================
 Global Requirements for OpenStack Projects
============================================

.. image:: https://governance.openstack.org/tc/badges/requirements.svg
    :target: https://governance.openstack.org/tc/reference/tags/index.html

Why Global Requirements?
========================

Refer to the `Dependency Management`_ section of the *Project Team
Guide* for information about the history of the project and the files
involved.

.. _Dependency Management: https://docs.openstack.org/project-team-guide/dependency-management.html

Tools
=====

All the tools require openstack_requirements to be installed (e.g. in a Python
virtualenv). They all have help, which is the authoritative documentation.

update-requirements
-------------------

This will update the requirements in a project from the global requirements
file found in ``.``. Alternatively, pass ``--source`` to use a different
global requirements file::

  update-requirements --source /opt/stack/requirements /opt/stack/nova

Entries in all requirements files will have their versions updated to match
the entries listed in the global requirements.  Excess entries will cause
errors in hard mode (the default) or be ignored in soft mode.

generate-constraints
--------------------

Compile a constraints file showing the versions resulting from installing all
of ``global-requirements.txt``::

  generate-constraints -p /usr/bin/python2.7 -p /usr/bin/python3 \
    -b blacklist.txt -r global-requirements.txt > new-constraints.txt

edit-constraints
----------------

Replace all references to a package in a constraints file with a new
specification. Used by DevStack to enable git installations of libraries that
are normally constrained::

  edit-constraints oslo.db "-e file://opt/stack/oslo.db#egg=oslo.db"

build-lower-constraints
-----------------------

Combine multiple lower-constraints.txt files to produce a list of the
highest version of each package mentioned in the files. This can be
used to produce the "highest minimum" for a global lower constraints
list (a.k.a., the "TJ Maxx").

To use the script, run::

    $ tox -e venv -- build-lower-constraints input1.txt input2.txt

Where the input files are lower-constraints.txt or requirements.txt
files from one or more projects.

If the inputs are requirements files, a lower constraints list for the
requirements is produced. If the inputs are lower-constraints.txt, the
output includes the highest version of each package referenced in the
files.

Proposing changes
=================

Look at the `Review Guidelines` and make sure your change meets them.

All changes to ``global-requirements.txt`` may dramatically alter the contents
of ``upper-constraints.txt`` due to adding or removing transitive
dependencies. As such you should always generate a diff against the current
merged constraints, otherwise your change may fail if it is incompatible with
the current tested constraints.

Regenerating involves five steps.

1) Install the dependencies needed to compile various Python packages::

    sudo apt-get install $(bindep -b)

2) Create a reference file (do this without your patch applied)::

    generate-constraints -p /usr/bin/python2.7 -p /usr/bin/python3 \
      -b blacklist.txt -r global-requirements.txt > baseline

3) Apply your patch and generate a new reference file::

    generate-constraints -p /usr/bin/python2.7 -p /usr/bin/python3 \
      -b blacklist.txt -r global-requirements.txt > updated

4) Diff them::

    diff -p baseline updated

5) Apply the patch to ``upper-constraints.txt``. This may require some
   fiddling. ``edit-constraint`` can do this for you **when the change
   does not involve multiple lines for one package**.

Resources
=========

- Documentation: https://docs.openstack.org/requirements/latest/
- Wiki: https://wiki.openstack.org/wiki/Requirements
- Bugs: https://launchpad.net/openstack-requirements
