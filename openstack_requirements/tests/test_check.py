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

    def test_match_without_python3_markers(self):
        req = requirement.parse(textwrap.dedent("""
        withmarker>=1.5'
        """))['withmarker'][0][0]
        self.assertTrue(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['withmarker'],
                allow_3_only=True
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
        self.assertTrue(
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
        self.assertTrue(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
            )
        )


class TestGetExclusions(testtools.TestCase):

    def test_none(self):
        req = list(check.get_global_reqs('name>=1.2')['name'])[0]
        self.assertEqual(
            set(),
            check._get_exclusions(req),
        )

    def test_one(self):
        req = list(check.get_global_reqs('name>=1.2,!=1.4')['name'])[0]
        self.assertEqual(
            set(['!=1.4']),
            check._get_exclusions(req),
        )

    def test_cap(self):
        req = list(check.get_global_reqs('name>=1.2,!=1.4,<2.0')['name'])[0]
        self.assertEqual(
            set(['!=1.4', '<2.0']),
            check._get_exclusions(req),
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
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
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
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
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
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
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
        global_reqs = check.get_global_reqs('')
        self.assertTrue(
            check._validate_one(
                'name',
                reqs=reqs,
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
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                blacklist=requirement.parse(''),
                global_reqs=global_reqs,
            )
        )

    def test_new_item_lower_min(self):
        # If the new item has a lower minimum value than the global
        # list, that is OK.
        reqs = [
            r
            for r, line in requirement.parse('name>=1.1,!=1.4')['name']
        ]
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                blacklist=requirement.parse(''),
                global_reqs=global_reqs,
            )
        )

    def test_new_item_extra_exclusion(self):
        # If the new item includes an exclusion that is not present in
        # the global list that is not OK.
        reqs = [
            r
            for r, line in requirement.parse('name>=1.2,!=1.4,!=1.5')['name']
        ]
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertTrue(
            check._validate_one(
                'name',
                reqs=reqs,
                blacklist=requirement.parse(''),
                global_reqs=global_reqs,
            )
        )

    def test_new_item_missing_exclusion(self):
        # If the new item does not include an exclusion that is
        # present in the global list that is OK.
        reqs = [
            r
            for r, line in requirement.parse('name>=1.2')['name']
        ]
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
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
        global_reqs = check.get_global_reqs(textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        """))
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
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
        global_reqs = check.get_global_reqs(textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        """))
        self.assertTrue(
            check._validate_one(
                'name',
                reqs=reqs,
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
        global_reqs = check.get_global_reqs(textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        """))
        self.assertTrue(
            check._validate_one(
                'name',
                reqs=reqs,
                blacklist=requirement.parse(''),
                global_reqs=global_reqs,
            )
        )

    def test_new_item_matches_py3_allowed_no_version(self):
        # If the global list has multiple entries for an item but the branch
        # allows python 3 only, then only the py3 entries need to match.
        # Requirements without a python_version marker should always be used.
        r_content = textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        other-name
        """)
        reqs = [
            r
            for r, line in requirement.parse(r_content)['name']
        ]
        global_reqs = check.get_global_reqs(textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        other-name
        """))
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                blacklist=requirement.parse(''),
                global_reqs=global_reqs,
                allow_3_only=True,
            )
        )

    def test_new_item_matches_py3_allowed(self):
        # If the global list has multiple entries for an item but the branch
        # allows python 3 only, then only the py3 entries need to match.
        # Requirements without a python_version marker should always be used.
        r_content = textwrap.dedent("""
        name>=1.5
        other-name
        """)
        reqs = [
            r
            for r, line in requirement.parse(r_content)['name']
        ]
        global_reqs = check.get_global_reqs(textwrap.dedent("""
        name>=1.5;python_version>='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        other-name
        """))
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                blacklist=requirement.parse(''),
                global_reqs=global_reqs,
                allow_3_only=True,
            )
        )

    def test_new_item_matches_py3_allowed_with_py2(self):
        # If the global list has multiple entries for an item but the branch
        # allows python 3 only, then only the py3 entries need to match.
        # It should continue to pass with py2 entries though.
        r_content = textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        """)
        reqs = [
            r
            for r, line in requirement.parse(r_content)['name']
        ]
        global_reqs = check.get_global_reqs(textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        """))
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                blacklist=requirement.parse(''),
                global_reqs=global_reqs,
                allow_3_only=True,
            )
        )

    def test_new_item_matches_py3_allowed_no_py2(self):
        # If the global list has multiple entries for an item but the branch
        # allows python 3 only, then only the py3 entries need to match.
        r_content = textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        """)
        reqs = [
            r
            for r, line in requirement.parse(r_content)['name']
        ]
        global_reqs = check.get_global_reqs(textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        """))
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                blacklist=requirement.parse(''),
                global_reqs=global_reqs,
                allow_3_only=True,
            )
        )


class TestValidateLowerConstraints(testtools.TestCase):

    def setUp(self):
        super(TestValidateLowerConstraints, self).setUp()
        self._stdout_fixture = fixtures.StringStream('stdout')
        self.stdout = self.useFixture(self._stdout_fixture).stream
        self.useFixture(fixtures.MonkeyPatch('sys.stdout', self.stdout))

    def test_no_constraints_file(self):
        constraints_content = None
        project_data = {
            'requirements': {'requirements.txt': 'name>=1.2,!=1.4'},
            'lower-constraints.txt': constraints_content,
        }
        head_reqs = check.RequirementsList('testproj', project_data)
        head_reqs.process(False)
        self.assertFalse(
            check.validate_lower_constraints(
                req_list=head_reqs,
                constraints=project_data['lower-constraints.txt'],
                blacklist=requirement.parse(''),
            )
        )

    def test_no_min(self):
        constraints_content = textwrap.dedent("""
        name==1.2
        """)
        project_data = {
            'requirements': {'requirements.txt': 'name!=1.4'},
            'lower-constraints.txt': constraints_content,
        }
        head_reqs = check.RequirementsList('testproj', project_data)
        head_reqs.process(False)
        self.assertFalse(
            check.validate_lower_constraints(
                req_list=head_reqs,
                constraints=project_data['lower-constraints.txt'],
                blacklist=requirement.parse(''),
            )
        )

    def test_matches(self):
        constraints_content = textwrap.dedent("""
        name==1.2
        """)
        project_data = {
            'requirements': {'requirements.txt': 'name>=1.2,!=1.4'},
            'lower-constraints.txt': constraints_content,
        }
        head_reqs = check.RequirementsList('testproj', project_data)
        head_reqs.process(False)
        self.assertFalse(
            check.validate_lower_constraints(
                req_list=head_reqs,
                constraints=project_data['lower-constraints.txt'],
                blacklist=requirement.parse(''),
            )
        )

    def test_not_constrained(self):
        constraints_content = textwrap.dedent("""
        """)
        project_data = {
            'requirements': {'requirements.txt': 'name>=1.2,!=1.4'},
            'lower-constraints.txt': constraints_content,
        }
        head_reqs = check.RequirementsList('testproj', project_data)
        head_reqs.process(False)
        self.assertTrue(
            check.validate_lower_constraints(
                req_list=head_reqs,
                constraints=project_data['lower-constraints.txt'],
                blacklist=requirement.parse(''),
            )
        )

    def test_mismatch_blacklisted(self):
        constraints_content = textwrap.dedent("""
        name==1.2
        """)
        project_data = {
            'requirements': {'requirements.txt': 'name>=1.3,!=1.4'},
            'lower-constraints.txt': constraints_content,
        }
        head_reqs = check.RequirementsList('testproj', project_data)
        head_reqs.process(False)
        self.assertFalse(
            check.validate_lower_constraints(
                req_list=head_reqs,
                constraints=project_data['lower-constraints.txt'],
                blacklist=requirement.parse('name'),
            )
        )

    def test_lower_bound_lower(self):
        constraints_content = textwrap.dedent("""
        name==1.2
        """)
        project_data = {
            'requirements': {'requirements.txt': 'name>=1.1,!=1.4'},
            'lower-constraints.txt': constraints_content,
        }
        head_reqs = check.RequirementsList('testproj', project_data)
        head_reqs.process(False)
        self.assertTrue(
            check.validate_lower_constraints(
                req_list=head_reqs,
                constraints=project_data['lower-constraints.txt'],
                blacklist=requirement.parse(''),
            )
        )

    def test_lower_bound_higher(self):
        constraints_content = textwrap.dedent("""
        name==1.2
        """)
        project_data = {
            'requirements': {'requirements.txt': 'name>=1.3,!=1.4'},
            'lower-constraints.txt': constraints_content,
        }
        head_reqs = check.RequirementsList('testproj', project_data)
        head_reqs.process(False)
        self.assertTrue(
            check.validate_lower_constraints(
                req_list=head_reqs,
                constraints=project_data['lower-constraints.txt'],
                blacklist=requirement.parse(''),
            )
        )

    def test_constrained_version_excluded(self):
        constraints_content = textwrap.dedent("""
        name==1.2
        """)
        project_data = {
            'requirements': {'requirements.txt': 'name>=1.1,!=1.2'},
            'lower-constraints.txt': constraints_content,
        }
        head_reqs = check.RequirementsList('testproj', project_data)
        head_reqs.process(False)
        self.assertTrue(
            check.validate_lower_constraints(
                req_list=head_reqs,
                constraints=project_data['lower-constraints.txt'],
                blacklist=requirement.parse(''),
            )
        )

    def test_constraints_with_markers(self):
        constraints_content = textwrap.dedent("""
        name==1.1;python_version=='2.7'
        name==2.0;python_version=='3.5'
        name==2.0;python_version=='3.6'
        """)
        project_data = {
            'requirements': {
                'requirements.txt': textwrap.dedent("""
                name>=1.1,!=1.2;python_version=='2.7'
                name>=2.0;python_version=='3.5'
                name>=2.0;python_version=='3.6'
                """),
            },
            'lower-constraints.txt': constraints_content,
        }
        head_reqs = check.RequirementsList('testproj', project_data)
        head_reqs.process(False)
        self.assertFalse(
            check.validate_lower_constraints(
                req_list=head_reqs,
                constraints=project_data['lower-constraints.txt'],
                blacklist=requirement.parse(''),
            )
        )

    def test_constraints_with_markers_missing_one_req(self):
        constraints_content = textwrap.dedent("""
        name==1.1;python_version=='2.7'
        name==2.0;python_version=='3.5'
        name==2.0;python_version=='3.6'
        """)
        project_data = {
            'requirements': {
                'requirements.txt': textwrap.dedent("""
                name>=1.1,!=1.2;python_version=='2.7'
                name>=2.0;python_version=='3.5'
                """),
            },
            'lower-constraints.txt': constraints_content,
        }
        head_reqs = check.RequirementsList('testproj', project_data)
        head_reqs.process(False)
        self.assertFalse(
            check.validate_lower_constraints(
                req_list=head_reqs,
                constraints=project_data['lower-constraints.txt'],
                blacklist=requirement.parse(''),
            )
        )

    def test_constraints_with_markers_missing_one_marker(self):
        constraints_content = textwrap.dedent("""
        name==1.1;python_version=='2.7'
        name==2.0;python_version=='3.5'
        """)
        project_data = {
            'requirements': {
                'requirements.txt': textwrap.dedent("""
                name>=1.1,!=1.2;python_version=='2.7'
                name>=2.0;python_version=='3.5'
                name>=2.0;python_version=='3.6'
                """),
            },
            'lower-constraints.txt': constraints_content,
        }
        head_reqs = check.RequirementsList('testproj', project_data)
        head_reqs.process(False)
        self.assertTrue(
            check.validate_lower_constraints(
                req_list=head_reqs,
                constraints=project_data['lower-constraints.txt'],
                blacklist=requirement.parse(''),
            )
        )

    def test_complex_marker_evaluation(self):
        constraints_content = textwrap.dedent("""
        name===0.8.0;python_version=='2.7'
        name===1.0.0;python_version>='3.0'
        """)
        project_data = {
            'requirements': {
                'requirements.txt': textwrap.dedent("""
                name>=0.8.0;python_version<'3.0'  # BSD
                name>=1.0.0;python_version>='3.0'  # BSD
                """),
            },
            'lower-constraints.txt': constraints_content,
        }
        head_reqs = check.RequirementsList('testproj', project_data)
        head_reqs.process(False)
        self.assertFalse(
            check.validate_lower_constraints(
                req_list=head_reqs,
                constraints=project_data['lower-constraints.txt'],
                blacklist=requirement.parse(''),
            )
        )
