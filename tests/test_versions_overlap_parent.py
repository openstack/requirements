# Copyright 2014 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import pkg_resources
import testtools
from testtools import matchers

import versions_overlap_parent as vop


class TestVersionsOverlapParent(testtools.TestCase):
    def test_increase_version(self):
        self.assertThat(vop.increase_version('1.0'), matchers.Equals('1.1'))

    def test_decrease_version(self):
        self.assertThat(vop.decrease_version('1.0'), matchers.Equals('1.9'))

    def _test_get_version_required(self, start_version, op, exp_version):
        req = pkg_resources.Requirement.parse('pkg%s%s' % (op, start_version))
        self.assertThat(vop.get_version_required(req.specs[0]),
                        matchers.Equals(exp_version))

    def test_get_version_required_eq(self):
        self._test_get_version_required('1.0', '==', '1.0')

    def test_get_version_required_gt(self):
        self._test_get_version_required('1.0', '>', '1.1')

    def test_get_version_required_ge(self):
        self._test_get_version_required('1.0', '>=', '1.0')

    def test_get_version_required_lt(self):
        self._test_get_version_required('1.0', '<', '1.9')

    def test_get_version_required_le(self):
        self._test_get_version_required('1.0', '<=', '1.0')

    def test_get_version_required_ne(self):
        self._test_get_version_required('1.0', '!=', '1.0')

    def test_RequirementsList_read_requirements_empty_line(self):
        rl = vop.RequirementsList('something')
        rl.read_requirements([''])
        self.assertThat(rl.reqs, matchers.Equals({}))

    def test_RequirementsList_read_requirements_comment_line(self):
        rl = vop.RequirementsList('something')
        rl.read_requirements(['# comment'])
        self.assertThat(rl.reqs, matchers.Equals({}))

    def test_RequirementsList_read_requirements_skips(self):
        # Lines starting with certain strings are skipped.
        rl = vop.RequirementsList('something')
        rl.read_requirements(['http://tarballs.openstack.org/something',
                              '-esomething',
                              '-fsomething'])
        self.assertThat(rl.reqs, matchers.Equals({}))

    def test_RequirementsList_read_requirements_parse(self):
        rl = vop.RequirementsList('something')
        rl.read_requirements(['extras',
                              'sphinx>=1.1.2,!=1.2.0,<1.3 # BSD', ])
        self.assertThat(rl.reqs['extras'].specs,
                        matchers.Equals([]))
        exp_sphinx_specs = [('>=', '1.1.2'), ('!=', '1.2.0'), ('<', '1.3')]
        self.assertThat(rl.reqs['sphinx'].specs,
                        matchers.Equals(exp_sphinx_specs))

    def _compare(self, head_reqs, parent_reqs):
        vop_obj = vop.VersionsOverlapParent()
        vop_obj.set_head_requirements(head_reqs)
        vop_obj.set_parent_requirements(parent_reqs)
        vop_obj.compare_reqs()

    def test_VersionsOverlapParent_same(self):
        # No problem if the requirements list is the same.
        self._compare(['extras'], ['extras'])

    def test_VersionsOverlapParent_add(self):
        # No problem if a new requirement is added
        self._compare(['extras'], ['extras', 'new_requirement>=1.0'])

    def test_VersionsOverlapParent_remove(self):
        # No problem if a requirement is removed.
        self._compare(['extras', 'old_requirement>=1.0'], ['extras'])

    def test_VersionsOverlapParent_update_overlap(self):
        # No problem if a requirement is updated and it overlaps
        self._compare(['package>=1.0'], ['package>=1.0,<2.0'])

    def test_VersionsOverlapParent_update_nooverlap_fails(self):
        # Fails if versions don't overlap.
        cmp_fn = lambda: self._compare(['package>=1.0,<2.0'], ['package>=2.0'])
        self.assertThat(cmp_fn, matchers.raises(Exception))
