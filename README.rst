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

Since Havana we've also observed significant CI disruption occurring due to
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
``setup.cfg``. This is maintained by hand, with changes going through CI.

We also maintain a compiled list of the exact versions, including transitive
dependencies, of packages that are known to work in the OpenStack CI system.
This is maintained via an automated process that calculates the list and
proposes a change back to this repository. A consequence of this is that
new releases of OpenStack libraries are not immediately used: they have to
pass through this automated process before we can benefit from (or be harmed
by) them.

Format
------

``global-requirements.txt`` supports a subset of pip requirement file
contents. Distributions may only be referenced by name, not URL. Options
(such as -e or -f) may not be used. Version specifiers, environment markers
and comments are all permitted. A single distribution may be listed more than
once if different specifiers are required with different markers - for
instance, if a dependency has dropped Python 2.7 support.

``upper-constraints.txt`` is machine generated and nothing more or less than
an exact list of versions.

Enforcement for Test Runs
-------------------------

Devstack
++++++++

When ``USE_CONSTRAINTS`` is set ``True``, devstack uses the pip ``-c`` option
to pin all the libraries to known good versions. ``edit-constraints`` can be
used to unpin a single constraint, and this is done to install libraries from
git. This is the **recommended** way to use devstack.

When ``USE_CONSTRAINTS`` is set ``False``, devstack overwrites the
``requirements.txt`` and ``test-requirements.txt`` for **all** installed
projects with the versions from ``global-requirements.txt``. Projects that are
not in ``projects.txt`` get 'soft' updates, ones that are get 'hard' updated.
This attempts to ensure that we will get a deterministic set of requirements
installed in the test system, and it won't be a guessing game based on the
last piece of software to be installed. However due to the interactions with
transitive dependencies this doesn't actually deliver what we need, and is
**not recommended**.

Tox
+++

We are working on the necessary changes to use ``upper-constraints.txt`` in
tox jobs but it is not yet complete.

Enforcement in Projects
-----------------------

All projects that have accepted the requirements contract (as listed
in ``projects.txt``) are expected to run a requirements compatibility
job. This job ensures that a project can not change any dependencies to
versions not compatible with ``global-requirements.txt``. It also ensures that
those projects can not add a requirement that is not already in
``global-requirements.txt``. This ``check-requirements`` job should
be merged in infra before proposing the change to ``projects.txt`` in
``openstack/requirements``.

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
specification. Used by devstack to enable git installations of libraries that
are normally constrained::

  edit-constraints oslo.db "-e file://opt/stack/oslo.db#egg=oslo.db"

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

Review Guidelines
=================

There are a set of questions that every reviewer should ask on any
proposed requirements change. Proposers can make reviewing easier by
including the answers to these questions in the commit message for
their change.

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

- The blacklist is for handling dependencies that cannot be constrained.
  For instance, linters which each project has at a different release level,
  and which make projects fail on every release (because they add rules) -
  those cannot be globally constrained unless we coordinate updating all of
  OpenStack to the new release at the same time - but given the volunteer
  and loosely coupled nature of the big tent that is infeasible. Dependencies
  that are only used in unconstrained places should not be blacklisted - they
  may be constrained in future, and there's no harm caused by constraining
  them today. Entries in the blacklist should have a comment explaining the
  reason for blacklisting.

- Reviews that only update ``projects.txt`` should be workflow approved
  alongside or before other reviews in order to have the OpenStack Proposal Bot
  propagation be useful as soon as possible for the other projects. For project
  removal or addition, the +1 from the current PTL (or core if the PTL proposed
  the change) should be enough.

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

  The library should be licensed as described in `Licensing requirements`_,
  and the license should be described in a comment on the same line as the
  added dependency. If you have doubts over licensing compatibility, like
  for example when adding a GPL test dependency, you can seek advice from
  Robert Collins (lifeless), Monty Taylor (mordred) or Jim Blair (jeblair).

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

- Is the library required for OpenStack project or related dev or
  infrastructure setup? (Answer to this should be Yes, of course)
  Which?

  Please provide details such as gerrit change request or launchpad
  bug/blueprint specifying the need for adding this library.

.. _Licensing requirements: http://governance.openstack.org/reference/licensing.html

For Upgrading Requirements Versions
-----------------------------------

- Why is it impossible to use the current version definition?

  Everyone likes everyone else to use the latest version of their
  code. However, deployers really don't like to be constantly updating
  things. Unless it's actually **impossible** to use the minimum
  version specified in ``global-requirements.txt``, it should not be
  changed.

  Leave that decision to deployers and distros.

- Changes to update the minimum version of a library developed by the
  OpenStack community can be approved by one reviewer, as long as the
  constraints are correct and the tests pass.

.. _finding-distro-status:

Finding Distro Status
---------------------

From the OpenStack distro support policy:

OpenStack will target its development efforts to latest Ubuntu/Fedora,
but will not introduce any changes that would make it impossible to
run on the latest Ubuntu LTS or latest RHEL.

As such we really need to know what the current state of packaging is
on these platforms (and ideally Debian, Gentoo, and SUSE as well).

For people unfamiliar with Linux Distro packaging you can use the
following tools to search for packages:

 - Ubuntu - http://packages.ubuntu.com/
 - Fedora - https://apps.fedoraproject.org/packages/
 - Gentoo - https://packages.gentoo.org/
 - SUSE - https://build.opensuse.org/project/show/devel:languages:python

For ``upper-constraints.txt`` changes
-------------------------------------

If the change was proposed by the OpenStack CI bot, then if the change has
passed CI, only one reviewer is needed and they should +2 +A without thinking
about things.

If the change was not proposed by the OpenStack CI bot, and only
changes the ``upper-constraints.txt`` entry for a new library release,
then the change should be approved if it passes the tests. See the
README.rst in openstack/releases for more details of the release
process.

If the change was not proposed by the OpenStack CI bot, and is not
related to releasing one of our libraries, and does not include a
``global-requirements.txt`` change, then it should be rejected: the CI
bot will generate an appropriate change itself. Ask in
#openstack-infra if the bot needs to be run more quickly.

Otherwise the change may be the result of recalculating the constraints which
changed when a ``global-requirements.txt`` change is proposed. In this case, ignore
the changes to ``upper-constraints.txt`` and review the
``global-requirements.txt`` component of the change.
