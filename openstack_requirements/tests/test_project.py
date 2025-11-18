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

import os
import textwrap

import fixtures
import testscenarios
import testtools

from openstack_requirements import project
from openstack_requirements.tests import common


load_tests = testscenarios.load_tests_apply_scenarios


class TestReadProject(testtools.TestCase):
    def test_pyproject_toml(self):
        root = self.useFixture(common.pep_518_fixture).root
        proj = project.read(root)
        self.assertEqual(proj['root'], root)
        self.assertEqual(
            list(sorted(proj['requirements'])),
            ['pyproject.toml'],
        )

    def test_setup_cfg(self):
        root = self.useFixture(common.pbr_fixture).root
        proj = project.read(root)
        self.assertEqual(proj['root'], root)
        self.assertEqual(
            list(sorted(proj['requirements'])),
            ['requirements.txt', 'test-requirements.txt'],
        )

    def test_empty(self):
        root = self.useFixture(fixtures.TempDir()).path
        proj = project.read(root)
        self.assertEqual(
            proj,
            {
                'root': root,
                'requirements': {},
                'extras': {},
            },
        )


class TestProjectExtras(testtools.TestCase):
    def test_pyproject_toml(self):
        root = self.useFixture(fixtures.TempDir()).path
        with open(os.path.join(root, 'pyproject.toml'), 'w') as fh:
            fh.write(
                textwrap.dedent("""
                [project.optional-dependencies]
                1 = [
                  "foo",
                ]
                2 = [
                  "foo", # fred
                  "bar",
                ]
                """)
            )
        expected = {'1': ['foo'], '2': ['foo', 'bar']}
        self.assertEqual(expected, project._read_pyproject_toml_extras(root))

    def test_setup_cfg(self):
        root = self.useFixture(fixtures.TempDir()).path
        with open(os.path.join(root, 'setup.cfg'), 'w') as fh:
            fh.write(
                textwrap.dedent("""
                [extras]
                1 =
                  foo
                2 =
                  foo # fred
                  bar
                """)
            )
        expected = {'1': ['foo'], '2': ['foo # fred', 'bar']}
        self.assertEqual(expected, project._read_setup_cfg_extras(root))

    def test_none(self):
        root = self.useFixture(fixtures.TempDir()).path
        with open(os.path.join(root, 'setup.cfg'), 'w') as fh:
            fh.write(
                textwrap.dedent("""
                [metadata]
                name = foo
                """)
            )
        self.assertIsNone(project._read_setup_cfg_extras(root))

    def test_no_setup_cfg(self):
        root = self.useFixture(fixtures.TempDir()).path
        self.assertIsNone(project._read_setup_cfg_extras(root))
