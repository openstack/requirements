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


class TestRequirementsList(testtools.TestCase):
    def setUp(self):
        super().setUp()
        self._stdout_fixture = fixtures.StringStream('stdout')
        self.stdout = self.useFixture(self._stdout_fixture).stream
        self.useFixture(fixtures.MonkeyPatch('sys.stdout', self.stdout))

    def test_extras__setup_cfg(self):
        project_data = {
            'root': '/fake/root',
            'requirements': {
                'requirements.txt': 'requests>=2.0.0\n'
            },
            'extras': {
                'setup.cfg': {
                    'test': 'pytest>=6.0.0\nflake8>=3.8.0\n',
                    'dev': 'black>=24.0.0\nmypy>=0.900\n'
                }
            }
        }

        req_list = check.RequirementsList('test-project', project_data)
        req_list.process(strict=False)

        self.assertIn('test', req_list.reqs_by_file)
        self.assertIn('dev', req_list.reqs_by_file)

        test_reqs = req_list.reqs_by_file['test']
        dev_reqs = req_list.reqs_by_file['dev']

        self.assertEqual(len(test_reqs), 2)
        self.assertIn('pytest', test_reqs)
        self.assertIn('flake8', test_reqs)

        self.assertEqual(len(dev_reqs), 2)
        self.assertIn('black', dev_reqs)
        self.assertIn('mypy', dev_reqs)


class TestIsReqInGlobalReqs(testtools.TestCase):
    def setUp(self):
        super().setUp()

        self._stdout_fixture = fixtures.StringStream('stdout')
        self.stdout = self.useFixture(self._stdout_fixture).stream
        self.backports = list()
        self.useFixture(fixtures.MonkeyPatch('sys.stdout', self.stdout))

        self.global_reqs = check.get_global_reqs(
            textwrap.dedent("""
        name>=1.2,!=1.4
        withmarker>=1.5;python_version=='3.5'
        withmarker>=1.2,!=1.4;python_version=='2.7'
        """)
        )

    def test_match(self):
        """Test a basic package."""
        req = requirement.parse('name>=1.2,!=1.4')['name'][0][0]
        self.assertTrue(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
                self.backports,
            )
        )

    def test_match_with_markers(self):
        """Test a package specified with python 3 markers."""
        req = requirement.parse(
            textwrap.dedent("""
        withmarker>=1.5;python_version=='3.5'
        """)
        )['withmarker'][0][0]
        self.assertTrue(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['withmarker'],
                self.backports,
            )
        )

    def test_match_with_local_markers(self):
        """Test a package specified with python 3 markers."""
        req = requirement.parse(
            textwrap.dedent("""
        name;python_version=='3.5'
        """)
        )['name'][0][0]
        self.assertTrue(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
                self.backports,
                allow_3_only=True,
            )
        )

    def test_match_without_python3_markers(self):
        """Test a package specified without python 3 markers.

        Python 3 packages are a thing. On those, it's totally unnecessary to
        specify e.g. a "python_version>'3" marker for packages.
        """
        req = requirement.parse(
            textwrap.dedent("""
        withmarker>=1.5
        """)
        )['withmarker'][0][0]
        self.assertTrue(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['withmarker'],
                self.backports,
                allow_3_only=True,
            )
        )

    def test_backport(self):
        """Test a stdlib backport pacakge.

        The python_version marker should be ignored for stdlib backport-type
        packages.
        """
        req = requirement.parse("name;python_version<'3.9'")['name'][0][0]
        self.assertTrue(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
                ['name'],
            )
        )

    def test_name_mismatch(self):
        """Test a mismatch in package names.

        Obviously a package with a different name is not the same thing.
        """
        req = requirement.parse('wrongname>=1.2,!=1.4')['wrongname'][0][0]
        self.assertFalse(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
                self.backports,
            )
        )

    def test_marker_mismatch(self):
        """Test a mismatch in markers.

        This should be a failure since the only marker we allow to be different
        is the python_version marker.
        """
        req = requirement.parse("name; sys_platform == 'win32'")['name'][0][0]
        self.assertFalse(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
                self.backports,
            )
        )

    def test_min_mismatch(self):
        """Test a mismatch in minimum version.

        We actually allow this since we only enforce a common upper constraint.
        Packages can specify whatever minimum they like so long as it doesn't
        exceed the upper-constraint value.
        """
        req = requirement.parse('name>=1.3,!=1.4')['name'][0][0]
        self.assertTrue(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
                self.backports,
            )
        )

    def test_extra_exclusion(self):
        """Test that we validate exclusions.

        A package can't exclude a version unless that is also excluded in
        global requirements.
        """
        req = requirement.parse('name>=1.2,!=1.4,!=1.5')['name'][0][0]
        self.assertFalse(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
                self.backports,
            )
        )

    def test_missing_exclusion(self):
        """Test that we ignore missing exclusions.

        A package can specify fewer exclusions than global requirements.
        """
        req = requirement.parse('name>=1.2')['name'][0][0]
        self.assertTrue(
            check._is_requirement_in_global_reqs(
                req,
                self.global_reqs['name'],
                self.backports,
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
        super().setUp()
        self._stdout_fixture = fixtures.StringStream('stdout')
        self.stdout = self.useFixture(self._stdout_fixture).stream
        self.useFixture(fixtures.MonkeyPatch('sys.stdout', self.stdout))
        self.backports = dict()

    def test_unchanged(self):
        # If the line matches the value in the branch list everything
        # is OK.
        reqs = [r for r, line in requirement.parse('name>=1.2,!=1.4')['name']]
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                denylist=requirement.parse(''),
                backports=self.backports,
                global_reqs=global_reqs,
            )
        )

    def test_denylisted(self):
        # If the package is denylisted, everything is OK.
        reqs = [r for r, line in requirement.parse('name>=1.2,!=1.4')['name']]
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                denylist=requirement.parse('name'),
                backports=self.backports,
                global_reqs=global_reqs,
            )
        )

    def test_denylisted_mismatch(self):
        # If the package is denylisted, it doesn't matter if the
        # version matches.
        reqs = [r for r, line in requirement.parse('name>=1.5')['name']]
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                denylist=requirement.parse('name'),
                backports=self.backports,
                global_reqs=global_reqs,
            )
        )

    def test_not_in_global_list(self):
        # If the package is not in the global list, that is an error.
        reqs = [r for r, line in requirement.parse('name>=1.2,!=1.4')['name']]
        global_reqs = check.get_global_reqs('')
        self.assertTrue(
            check._validate_one(
                'name',
                reqs=reqs,
                denylist=requirement.parse(''),
                backports=self.backports,
                global_reqs=global_reqs,
            )
        )

    def test_new_item_matches_global_list(self):
        # If the new item matches the global list exactly that is OK.
        reqs = [r for r, line in requirement.parse('name>=1.2,!=1.4')['name']]
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                denylist=requirement.parse(''),
                backports=self.backports,
                global_reqs=global_reqs,
            )
        )

    def test_new_item_lower_min(self):
        # If the new item has a lower minimum value than the global
        # list, that is OK.
        reqs = [r for r, line in requirement.parse('name>=1.1,!=1.4')['name']]
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                denylist=requirement.parse(''),
                backports=self.backports,
                global_reqs=global_reqs,
            )
        )

    def test_new_item_extra_exclusion(self):
        # If the new item includes an exclusion that is not present in
        # the global list that is not OK.
        reqs = [
            r for r, line in requirement.parse('name>=1.2,!=1.4,!=1.5')['name']
        ]
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertTrue(
            check._validate_one(
                'name',
                reqs=reqs,
                denylist=requirement.parse(''),
                backports=self.backports,
                global_reqs=global_reqs,
            )
        )

    def test_new_item_missing_exclusion(self):
        # If the new item does not include an exclusion that is
        # present in the global list that is OK.
        reqs = [r for r, line in requirement.parse('name>=1.2')['name']]
        global_reqs = check.get_global_reqs('name>=1.2,!=1.4')
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                denylist=requirement.parse(''),
                backports=self.backports,
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
        reqs = [r for r, line in requirement.parse(r_content)['name']]
        global_reqs = check.get_global_reqs(
            textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        """)
        )
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                denylist=requirement.parse(''),
                backports=self.backports,
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
        reqs = [r for r, line in requirement.parse(r_content)['name']]
        global_reqs = check.get_global_reqs(
            textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        """)
        )
        self.assertTrue(
            check._validate_one(
                'name',
                reqs=reqs,
                denylist=requirement.parse(''),
                backports=self.backports,
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
        reqs = [r for r, line in requirement.parse(r_content)['name']]
        global_reqs = check.get_global_reqs(
            textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        """)
        )
        self.assertTrue(
            check._validate_one(
                'name',
                reqs=reqs,
                denylist=requirement.parse(''),
                backports=self.backports,
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
        reqs = [r for r, line in requirement.parse(r_content)['name']]
        global_reqs = check.get_global_reqs(
            textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        other-name
        """)
        )
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                denylist=requirement.parse(''),
                backports=self.backports,
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
        reqs = [r for r, line in requirement.parse(r_content)['name']]
        global_reqs = check.get_global_reqs(
            textwrap.dedent("""
        name>=1.5;python_version>='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        other-name
        """)
        )
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                denylist=requirement.parse(''),
                backports=self.backports,
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
        reqs = [r for r, line in requirement.parse(r_content)['name']]
        global_reqs = check.get_global_reqs(
            textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        """)
        )
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                denylist=requirement.parse(''),
                backports=self.backports,
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
        reqs = [r for r, line in requirement.parse(r_content)['name']]
        global_reqs = check.get_global_reqs(
            textwrap.dedent("""
        name>=1.5;python_version=='3.5'
        name>=1.2,!=1.4;python_version=='2.6'
        """)
        )
        self.assertFalse(
            check._validate_one(
                'name',
                reqs=reqs,
                denylist=requirement.parse(''),
                backports=self.backports,
                global_reqs=global_reqs,
                allow_3_only=True,
            )
        )


class TestBackportPythonMarkers(testtools.TestCase):
    def setUp(self):
        super().setUp()
        self._stdout_fixture = fixtures.StringStream('stdout')
        self.stdout = self.useFixture(self._stdout_fixture).stream
        self.useFixture(fixtures.MonkeyPatch('sys.stdout', self.stdout))

        self.req = requirement.parse(
            textwrap.dedent("""
        name>=1.5;python_version=='3.11'
        """)
        )['name'][0][0]
        self.global_reqs = check.get_global_reqs(
            textwrap.dedent("""
        name>=1.5;python_version=='3.10'
        """)
        )

    def test_notmatching_no_backport(self):
        backports = requirement.parse("")
        self.assertFalse(
            check._is_requirement_in_global_reqs(
                self.req,
                self.global_reqs["name"],
                list(backports.keys()),
                allow_3_only=True,
            )
        )

    def test_notmatching_with_backport(self):
        b_content = textwrap.dedent("""
        name
        """)
        backports = requirement.parse(b_content)
        self.assertTrue(
            check._is_requirement_in_global_reqs(
                self.req,
                self.global_reqs["name"],
                list(backports.keys()),
                allow_3_only=True,
            )
        )
