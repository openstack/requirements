OpenStack Requirements tools.

This directory contains a number of tools that are useful to the requirements core team and OpenStack
developers.

babel-test.sh
-------------
A tool check for regressions with new Babel releases.

build_wheels.sh
---------------

Generate wheels for all of the requirements, ignoring any packages
that won't build wheels so we get as many as possible. This is meant
to be used on a development box combined with devpi and a wheelhouse
configuration setting for pip, such as described in
https://www.berrange.com/posts/2014/11/14/faster-rebuilds-for-python-virtualenv-trees/

cap.py
------

Take the output of 'pip freeze' and use the installed versions to caps requirements.

check-install.py
----------------

Used in tox environment pip-install.  Only installs requirements (as opposed to
test-requirements and verifies that all console-scripts have all modules
needed.

code-search.sh
--------------
Assuming you have a set of local git repos grep them all for interesting things.

cruft.sh
--------

This script, when run from the root directory of this repository, will search
the default and feature branches of all projects listed in the projects.txt
file for declared dependencies, then output a list of any entries in the
global-requirements.txt file which are not actual dependencies of those
projects. Old dependencies which were removed from projects or which were used
only for projects which have since been removed should be cleaned up, but many
entries likely represent recent additions which still have pending changes to
add them to one or more projects. In most cases, git pickaxe will yield the
answer.

grep-all.sh
-----------

List a requirements specification and constratint for a given libarary

noop-change.sh
--------------

Generate a bulk no-op changes in supplied projects.  Useful if we have a risky
change in global-requirements or upper-constraints and we want to test impacted
projects.

publish_constraints.sh
----------------------
Used in the gate!  Generate the constraints files from git for publishing to a
static server.

what-broke.py
-------------
figure out what requirements change likely broke us.
