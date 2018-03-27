# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import textwrap

from openstack_requirements import check
from openstack_requirements import requirement

import fixtures
import testtools


class TestIsReqInGlobalReqs(testtools.TestCase):

    def setUp(self):
        super(TestIsReqInGlobalReqs, self).setUp()

        self._stdout_fixture = fixtures.StringStream('stdout')
        self.stdout = self.useFixture(self._stdout_fixture).stream
        self.useFixture(fixtures.MonkeyPatch('sys.stdout', self.stdout))

        self.global_reqs = check.get_global_reqs(textwrap.dedent("""
        name>=1.2,!=1.4
        withmarker>=1.5;python_version=='3.5'
        withmarker>=1.2,!=1.4;python_version=='2.7'
        """))
        print('global_reqs', self.global_reqs)

    def test_match(self):
        req = requirement.parse('name>=1.2,!=1.4')['name'][0][0]
        self.assertTrue(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
            )
        )

    def test_match_with_markers(self):
        req = requirement.parse(textwrap.dedent("""
        withmarker>=1.5;python_version=='3.5'
        """))['withmarker'][0][0]
        self.assertTrue(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['withmarker'],
            )
        )

    def test_name_mismatch(self):
        req = requirement.parse('wrongname>=1.2,!=1.4')['wrongname'][0][0]
        self.assertFalse(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
            )
        )

    def test_min_mismatch(self):
        req = requirement.parse('name>=1.3,!=1.4')['name'][0][0]
        self.assertFalse(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
            )
        )

    def test_extra_exclusion(self):
        req = requirement.parse('name>=1.2,!=1.4,!=1.5')['name'][0][0]
        self.assertFalse(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
            )
        )

    def test_missing_exclusion(self):
        req = requirement.parse('name>=1.2')['name'][0][0]
        self.assertFalse(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
            )
        )


class TestValidateOne(testtools.TestCase):

    def setUp(self):
        super(TestValidateOne, self).setUp()
        self._stdout_fixture = fixtures.StringStream('stdout')
        self.stdout = self.useFixture(self._stdout_fixture).stream
        self.useFixture(fixtures.MonkeyPatch('sys.stdout', self.stdout))

    def test_unchanged(self):
        # If the line matches the value in the branch list everything
        # is OK.
        reqs = [
            r
            for r, line in requirement.parse('name>=1.2,!=1.4')['name']
        ]
        branch_reqs = check.RequirementsList(
            'testproj',
            {'requirements': {'requirements.txt': 'name>=1.2,!=1.4'}},
        )
        branch_reqs.process(False)
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                branch_reqs=branch_reqs,
                blacklist=requirement.parse(''),
                global_reqs=global_reqs,
            )
        )

    def test_blacklisted(self):
        # If the package is blacklisted, everything is OK.
        reqs = [
            r
            for r, line in requirement.parse('name>=1.2,!=1.4')['name']
        ]
        branch_reqs = check.RequirementsList(
            'testproj',
            {'requirements': {'requirements.txt': 'name>=1.2,!=1.4'}},
        )
        branch_reqs.process(False)
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                branch_reqs=branch_reqs,
                blacklist=requirement.parse('name'),
                global_reqs=global_reqs,
            )
        )

    def test_blacklisted_mismatch(self):
        # If the package is blacklisted, it doesn't matter if the
        # version matches.
        reqs = [
            r
            for r, line in requirement.parse('name>=1.5')['name']
        ]
        branch_reqs = check.RequirementsList(
            'testproj',
            {'requirements': {'requirements.txt': 'name>=1.2,!=1.4'}},
        )
        branch_reqs.process(False)
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                branch_reqs=branch_reqs,
                blacklist=requirement.parse('name'),
                global_reqs=global_reqs,
            )
        )

    def test_not_in_global_list(self):
        # If the package is not in the global list, that is an error.
        reqs = [
            r
            for r, line in requirement.parse('name>=1.2,!=1.4')['name']
        ]
        branch_reqs = check.RequirementsList(
            'testproj',
            {'requirements': {'requirements.txt': 'name>=1.2,!=1.4'}},
        )
        branch_reqs.process(False)
        global_reqs = check.get_global_reqs('')
        self.assertTrue(
            check._validate_one(
                'name',
                reqs=reqs,
                branch_reqs=branch_reqs,
                blacklist=requirement.parse(''),
                global_reqs=global_reqs,
            )
        )

    def test_new_item_matches_global_list(self):
        # If the new item matches the global list exactly that is OK.
        reqs = [
            r
            for r, line in requirement.parse('name>=1.2,!=1.4')['name']
        ]
        branch_reqs = check.RequirementsList(
            'testproj',
            {'requirements': {'requirements.txt': ''}},
        )
        branch_reqs.process(False)
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                branch_reqs=branch_reqs,
                blacklist=requirement.parse(''),
                global_reqs=global_reqs,
            )
        )

    def test_new_item_mismatches_global_list(self):
        # If the new item does not match the global value, that is an
        # error.
        reqs = [
            r
            for r, line in requirement.parse('name>=1.2,!=1.4,!=1.5')['name']
        ]
        branch_reqs = check.RequirementsList(
            'testproj',
            {'requirements': {'requirements.txt': ''}},
        )
        branch_reqs.process(False)
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertTrue(
            check._validate_one(
                'name',
                reqs=reqs,
                branch_reqs=branch_reqs,
                blacklist=requirement.parse(''),
                global_reqs=global_reqs,
            )
        )

    def test_new_item_matches_global_list_with_extra(self):
        # If the global list has multiple entries for an item with
        # different "extra" specifiers, the values must all be in the
        # requirements file.
        r_content = textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        """)
        reqs = [
            r
            for r, line in requirement.parse(r_content)['name']
        ]
        branch_reqs = check.RequirementsList(
            'testproj',
            {'requirements': {'requirements.txt': ''}},
        )
        branch_reqs.process(False)
        global_reqs = check.get_global_reqs(textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        """))
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                branch_reqs=branch_reqs,
                blacklist=requirement.parse(''),
                global_reqs=global_reqs,
            )
        )

    def test_new_item_missing_extra_line(self):
        # If the global list has multiple entries for an item with
        # different "extra" specifiers, the values must all be in the
        # requirements file.
        r_content = textwrap.dedent("""
        name>=1.2,!=1.4;python_version=='2.6'
        """)
        reqs = [
            r
            for r, line in requirement.parse(r_content)['name']
        ]
        branch_reqs = check.RequirementsList(
            'testproj',
            {'requirements': {'requirements.txt': ''}},
        )
        branch_reqs.process(False)
        global_reqs = check.get_global_reqs(textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        """))
        self.assertTrue(
            check._validate_one(
                'name',
                reqs=reqs,
                branch_reqs=branch_reqs,
                blacklist=requirement.parse(''),
                global_reqs=global_reqs,
            )
        )

    def test_new_item_mismatches_global_list_with_extra(self):
        # If the global list has multiple entries for an item with
        # different "extra" specifiers, the values must all be in the
        # requirements file.
        r_content = textwrap.dedent("""
        name>=1.5;python_version=='3.6'
        name>=1.2,!=1.4;python_version=='2.6'
        """)
        reqs = [
            r
            for r, line in requirement.parse(r_content)['name']
        ]
        branch_reqs = check.RequirementsList(
            'testproj',
            {'requirements': {'requirements.txt': ''}},
        )
        branch_reqs.process(False)
        global_reqs = check.get_global_reqs(textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        """))
        self.assertTrue(
            check._validate_one(
                'name',
                reqs=reqs,
                branch_reqs=branch_reqs,
                blacklist=requirement.parse(''),
                global_reqs=global_reqs,
            )
        )
