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
from testtools import matchers

from openstack_requirements import project
from openstack_requirements.tests import common


load_tests = testscenarios.load_tests_apply_scenarios


class TestReadProject(testtools.TestCase):
    def test_pbr(self):
        root = self.useFixture(common.pbr_fixture).root
        proj = project.read(root)
        self.expectThat(proj['root'], matchers.Equals(root))
        setup_py = open(root + '/setup.py').read()
        self.expectThat(proj['setup.py'], matchers.Equals(setup_py))
        setup_cfg = open(root + '/setup.cfg').read()
        self.expectThat(proj['setup.cfg'], matchers.Equals(setup_cfg))
        self.expectThat(
            proj['requirements'],
            matchers.KeysEqual('requirements.txt', 'test-requirements.txt'),
        )

    def test_no_setup_py(self):
        root = self.useFixture(fixtures.TempDir()).path
        proj = project.read(root)
        self.expectThat(
            proj,
            matchers.Equals(
                {
                    'root': root,
                    'requirements': {},
                    'extras': {},
                }
            ),
        )


class TestProjectExtras(testtools.TestCase):
    def test_smoke(self):
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
        expected = {'1': '\nfoo', '2': '\nfoo # fred\nbar'}
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
