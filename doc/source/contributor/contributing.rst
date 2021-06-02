============================
So You Want to Contribute...
============================

For general information on contributing to OpenStack, please check out the
`contributor guide <https://docs.openstack.org/contributors/>`_ to get started.
It covers all the basics that are common to all OpenStack projects: the accounts
you need, the basics of interacting with our Gerrit review system, how we
communicate as a community, etc.

Below will cover the more project specific information you need to get started
with openstack/requirements.

Communication
=============
We are on the #openstack-requirements channel on the OFTC IRC network.

Our meetings are currently Wednesdays at 2030 UTC.  See the
`official meeting <https://wiki.openstack.org/wiki/Meetings/Requirements>`_ for
up to date info.

Contacting the Core Team
++++++++++++++++++++++++
On IRC the nicks of our core team are as follows.

* dirk
* smcginnis
* prometheanfire

New Feature Planning
====================
New features should have a bug associated with it and be discussed during the
weekly meeting (see below for how to report a bug and above for meeting info.)

Task Tracking
=============
We track our tasks in
`Storyboard
<https://storyboard.openstack.org/#!/project/openstack/requirements>`_.

If you're looking for some smaller, easier work item to pick up and get started
on, comment in IRC and we'll find something.

Reporting a Bug
===============
If you have found an issue and want to make sure we are aware of it, please
report the issue on
`Storyboard
<https://storyboard.openstack.org/#!/project/openstack/requirements>`_.

Getting Your Patch Merged
=========================
Updates proposed to by the infra-bot to master only need one core reviewer to
approve and merge.

All other updates require two reviewers to merge.

Project Team Lead Duties
========================

Openstack Freeze Process
++++++++++++++++++++++++

Notice
------

- Email the developer mailing list approximately two weeks before the freeze.
  This email should contain a notice that requirements will branch and
  cycle-trailing projects should be careful if they have not branched.  The
  cycle-trailing projects can retarget their constraints usage to the stable
  branch.

Branch
------

- File a review in ``openstack/releases`` with -W and only remove the -W when
  ready to branch.

- Once branched, change the publish location to the new release branch.

- Once branched, update devstack grenade for the new release.  For example,
  use https://review.openstack.org/#/c/493057/13/devstack-vm-gate-wrap.sh

Potential issues
----------------

- Use something like https://review.openstack.org/#/c/492382 to find problem
  projects.

All common PTL duties are enumerated in the `PTL guide
<https://docs.openstack.org/project-team-guide/ptl.html>`_.

