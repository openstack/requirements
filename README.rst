============================================
 Global Requirements for OpenStack Projects
============================================

Why Global Requirements?
========================

During the Havana release cycle we kept running into coherency issues
with trying to install all the OpenStack components into a single
environment. The issue is that syncing of ``requirements.txt`` between
projects was an eventually consistent problem. Some projects would
update quickly, others would not. We'd never have the same versions
specified as requirements between packages.

Because of the way that python package installation with pip works,
this means that if you get lucky you'll end up with a working
system. If you don't you can easily break all of OpenStack on a
requirements update.

An example of how bad this had gotten is that python-keystoneclient
would typically be installed / uninstalled 6 times during the course
of a devstack gate run during Havana. If the last version of python
keystoneclient happened to be incompatible with some piece of
OpenStack a very hard to diagnose break occurs.

We also had an issue with projects adding dependencies of python
libraries without thinking through the long term implications of those
libraries. Is the library actively maintained? Is the library of a
compatible license? Does the library duplicate the function of existing
libraries that we already have in requirements? Is the library python
3 compatible? Is the library something that already exists in Linux
Distros that we target (Ubuntu / Fedora). The answer to many of these
questions was no.

Global requirements gives us a single place where we can evaluate
these things so that we can make a global decision for OpenStack on
the suitability of the library.

Since Havana we've also observed significant CI disruption occuring due to
upstream releases of software that are are incompatible (whether in small
or large ways) with OpenStack. So Global Requirements also serves as a control
point to determine the precise versions of dependencies that will be used
during CI.

Solution
========

The mechanics of the solution are relatively simple. We maintain a
central list of all the requirements (``global-requirements.txt``)
that are allowed in OpenStack projects. This is enforced for
``requirements.txt``, ``test-requirements.txt`` and extras defined in
``setup.cfg``.

Format
------

``global-requirements.txt`` supports a subset of pip requirement file
contents.  Distributions may only be referenced by name, not URL. Options
(such as -e or -f) may not be used. Version specifiers, environment markers
and comments are all permitted. A single distribution may be listed more than
once if different specifiers are required with different markers - for
instance, if a dependency has dropped Python 2.7 support.

Enforcement for Test Runs
-------------------------

Currently when installing with devstack, we overwrite the ``requirements.txt``
and ``test-requirements.txt`` for **all** installed projects with the versions
from ``global-requirements.txt``. This attempts to ensure that we will get a
deterministic set of requirements installed in the test system, and it won't
be a guessing game based on the last piece of software to be installed.
However due to the interactions with transitive dependencies this doesn't
actually deliver what we need.

We are moving to a system where we will define the precise versions of all
dependencies using ``upper-constraints.txt``. This will be overlaid onto all
pip commands made during devstack, and by tox, and will provide a single,
atomic, source of truth for what works at any given time. The constraints will
be required to be compatible with the global requirements, and will
[eventually] be total.

Enforcement in Projects
-----------------------

All projects that have accepted the requirements contract (as listed
in ``projects.txt``) are expected to run a requirements compatibility
job that ensures that they can not change any dependencies to versions not
compatible with ``global-requirements.txt``. It also ensures that those
projects can't add a requirement that's not already in
``global-requirements.txt``.

Automatic Sync of Accepted Requirements
---------------------------------------

If an updated requirement is proposed to OpenStack and accepted to
``global-requirements.txt``, the system then also automatically pushes
a review request for the new requirements definition to the projects
that include it.

For instance: if a review is accepted to ``global-requirements.txt``
that increases the minimum version of python-keystoneclient, the
system will submit patches to all the OpenStack projects that list
python-keystoneclient as a requirement or test requirement to match
this new version definition.

This is intended as a time saving device for projects, as they can
fast approve requirements syncs and not have to manually worry about
whether or not they are up to date with the global definition.

Running
=======

To run the requirements update manually, run::

  python update.py path/to/project

Entries in requirements.txt and test-requirements.txt will have their
versions updated to match the entries listed here. Any entries in the
target project which do not first exist here will be removed. No
entries will be added.

Review Guidelines
=================

There are a set of questions that every reviewer should ask on any
proposed requirements change (and ones that proposers should pre
answer to make things go smoother).

General Review Criteria
-----------------------

- No specifications for library versions should contain version caps

  As a community we value early feedback of broken upstream
  requirements, so version caps should be avoided except when dealing
  with exceptionally unstable libraries.

  If a library is exceptionally unstable, we should also be
  considering whether we want to replace it over time with one that
  *is* stable, or to contribute to the upstream community to help
  stabilize it.

- Libraries should contain a sensible known working minimum version

  Bare library names are bad. If it's unknown what a working minimum
  is, look at the output of pip freeze at the end of a successful
  devstack/tempest run and use that version. At least that's known to
  be working now.

- Commit message should refer to consuming projects(s)

  Preferably, the comments should also identify which feature or
  blueprint requires the new specification. Ideally, changes should
  already be proposed, so that its use can be seen.

For new Requirements
--------------------

- Is the library actively maintained?

  We *really* want some indication that the library is something we
  can get support on if we or our users find a bug, and that we
  don't have to take over and fork the library.

  Pointers to recent activity upstream and a consistent release model
  are appreciated.

- Is the library good code?

  It's expected, before just telling everyone to download arbitrary 3rd
  party code from the internet, that the submitter has taken a deep dive
  into the code to get a feel on whether this code seems solid enough
  to depend on. That includes ensuring the upstream code has some
  reasonable testing baked in.

- Is the library python 3 compatible?

  OpenStack will eventually need to support python 3. At this point
  adding non python 3 compatible libraries should only be done under
  *extreme* need. It should be considered a very big exception.

- Is the library license compatible?

  Preferably Apache2, BSD, MIT licensed. LGPL is ok. GPL or AGPL is
  verboten. Any other oddball license should be rejected.

- Is the library already packaged in the distros we target (Ubuntu
  latest / Fedora latest)?

  By adding something to OpenStack ``global-requirements.txt`` we are
  basically demanding that Linux Distros package this for the next
  release of OpenStack. If they already have, great. If not, we should
  be cautious of adding it. :ref:`finding-distro-status`

- Is the function of this library already covered by other libraries
  in ``global-requirements.txt``?

  Everyone has their own pet libraries that they like to use, but we
  do not need three different request mocking libraries in OpenStack.

  If this new requirement is about replacing an existing library with
  one that's better suited for our needs, then we also need the
  transition plan to drop the old library in a reasonable amount of
  time.

For Upgrading Requirements Versions
-----------------------------------

- Why is it impossible to use the current version definition?

  Everyone likes everyone else to use the latest version of their
  code. However, deployers really don't like to be constantly updating
  things. Unless it's actually **impossible** to use the minimum
  version specified in ``global-requirements.txt``, it should not be
  changed.

  Leave that decision to deployers and distros.

.. _finding-distro-status:

Finding Distro Status
---------------------

From the OpenStack distro support policy:

OpenStack will target its development efforts to latest Ubuntu/Fedora,
but will not introduce any changes that would make it impossible to
run on the latest Ubuntu LTS or latest RHEL.

As such we really need to know what the current state of packaging is
on these platforms (and ideally Debian and SUSE as well).

For people unfamiliar with Linux Distro packaging you can use the
following tools to search for packages:

 - Ubuntu - http://packages.ubuntu.com/
 - Fedora - https://apps.fedoraproject.org/packages/
