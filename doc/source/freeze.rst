========================
Openstack Freeze Process
========================

PTL Actions
===========

Notice
++++++

- Email the developer mailing list approximately two weeks before the freeze.
  This email should contain a notice that requirements will branch and
  cycle-trailing projects should be careful if they have not branched.  The
  cycle-trailing projects can retarget their constraints usage to the stable
  branch.

Branch
++++++

- File a review in ``openstack/releases`` with -W and only remove the -W when
  ready to branch.

- Once branched, change the publish location to the new release branch.

- Once branched, update devstack grenade for the new release.  For example,
  use https://review.openstack.org/#/c/493057/13/devstack-vm-gate-wrap.sh

Potential issues
++++++++++++++++

- Use something like https://review.openstack.org/#/c/492382 to find problem
  projects.
