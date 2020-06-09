# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import io
import os
from unittest import mock

import testscenarios
import testtools

from openstack_requirements.cmds import check_exists
from openstack_requirements import project
from openstack_requirements.tests import common

load_tests = testscenarios.load_tests_apply_scenarios


def mock_read_requirements_file(filename):
    if os.path.basename(filename) == 'upper-constraints.txt':
        return common.upper_constraints
    elif os.path.basename(filename) == 'global-requirements.txt':
        return common.global_reqs
    elif os.path.basename(filename) == 'blacklist.txt':
        return common.blacklist
    else:
        raise IOError('No such file or directory: %s' % filename)


class CheckExistsTest(testtools.TestCase):

    def setUp(self):
        super(CheckExistsTest, self).setUp()

    @mock.patch(
        'openstack_requirements.cmds.check_exists.read_requirements_file',
        mock_read_requirements_file)
    @mock.patch('openstack_requirements.project.read',
                return_value=common.project_project)
    def test_good_project(self, mock_project_read):
        ret = check_exists.main([common.project_fixture.root])
        self.assertEqual(ret, 0)

    @mock.patch(
        'openstack_requirements.cmds.check_exists.read_requirements_file',
        mock_read_requirements_file)
    def test_project_missing_from_uc(self):
        self.useFixture(common.project_fixture)
        orig_mocked_read_req = check_exists.read_requirements_file
        read_req_path = ('openstack_requirements.cmds.check_exists.'
                         'read_requirements_file')

        def remove_req_read_reqs_file(filename):
            if filename == 'upper-constraints.txt':
                upper_cons = common.upper_constraints.copy()
                upper_cons.pop('six')
                return upper_cons

            return orig_mocked_read_req(filename)

        expected_out = ('six from requirements.txt not found in'
                        ' upper-constraints')

        # Start capturing some output
        mock_stdout = io.StringIO()
        with mock.patch('openstack_requirements.project.read',
                        return_value=common.project_project), \
                mock.patch('sys.stdout', mock_stdout), \
                mock.patch(read_req_path, remove_req_read_reqs_file):
            ret = check_exists.main([common.project_fixture.root])
        self.assertEqual(ret, 1)
        self.assertIn(expected_out, mock_stdout.getvalue())

    @mock.patch(
        'openstack_requirements.cmds.check_exists.read_requirements_file',
        mock_read_requirements_file)
    def test_project_missing_from_gr(self):
        self.useFixture(common.project_fixture)

        # Add some random package that wont exist in G-R
        with open(common.project_fixture.req_file, 'a') as req_file:
            req_file.write(u'SomeRandomModule #Some random module\n')
            req_file.flush()

        expected_out = ('somerandommodule from requirements.txt not found in'
                        ' global-requirements')

        # Start capturing some output
        mock_stdout = io.StringIO()
        proj_read = project.read(common.project_fixture.root)
        with mock.patch('openstack_requirements.project.read',
                        return_value=proj_read), \
                mock.patch('sys.stdout', mock_stdout):
            ret = check_exists.main([common.project_fixture.root])
        self.assertEqual(ret, 1)
        self.assertIn(expected_out, mock_stdout.getvalue())

    @mock.patch(
        'openstack_requirements.cmds.check_exists.read_requirements_file',
        mock_read_requirements_file)
    def test_project_multiple_missing_from_uc_and_gr(self):
        self.useFixture(common.project_fixture)
        orig_mocked_read_req = check_exists.read_requirements_file
        read_req_path = ('openstack_requirements.cmds.check_exists.'
                         'read_requirements_file')

        def remove_req_read_reqs_file(filename):
            if filename == 'upper-constraints.txt':
                upper_cons = common.upper_constraints.copy()
                upper_cons.pop('lxml')
                return upper_cons

            return orig_mocked_read_req(filename)

        new_reqs = '>1.10.0\nsomerandommodule\n'

        # lets change the six requirement not include the u-c version
        proj_read = project.read(common.project_fixture.root)
        proj_read['requirements']['requirements.txt'] = \
            proj_read['requirements']['requirements.txt'][:-1] + new_reqs
        proj_read['requirements']['test-requirements.txt'] = \
            proj_read['requirements']['test-requirements.txt'] + \
            'anotherrandommodule\n'

        expected_outs = [
            'lxml from requirements.txt not found in upper-constraints',
            'somerandommodule from requirements.txt not found in '
            'global-requirements',
            'anotherrandommodule from test-requirements.txt not found in '
            'global-requirements',
            'six must be <= 1.10.0 from upper-constraints and include the '
            'upper-constraints version']

        # Start capturing some output
        mock_stdout = io.StringIO()
        with mock.patch('openstack_requirements.project.read',
                        return_value=proj_read), \
                mock.patch('sys.stdout', mock_stdout), \
                mock.patch(read_req_path, remove_req_read_reqs_file):
            ret = check_exists.main([common.project_fixture.root])
        self.assertEqual(ret, 1)
        for expected in expected_outs:
            self.assertIn(expected, mock_stdout.getvalue())

    @mock.patch(
        'openstack_requirements.cmds.check_exists.read_requirements_file',
        mock_read_requirements_file)
    def test_project_req_bigger_then_uc(self):
        self.useFixture(common.project_fixture)

        # lets change the six requirement not include the u-c version
        proj_read = project.read(common.project_fixture.root)
        proj_read['requirements']['requirements.txt'] = \
            proj_read['requirements']['requirements.txt'][:-1] + '>1.10.0\n'
        expected_out = ('six must be <= 1.10.0 from upper-constraints and '
                        'include the upper-constraints version')

        # Start capturing some output
        mock_stdout = io.StringIO()
        with mock.patch('openstack_requirements.project.read',
                        return_value=proj_read), \
                mock.patch('sys.stdout', mock_stdout):
            ret = check_exists.main([common.project_fixture.root])
        self.assertEqual(ret, 1)
        self.assertIn(expected_out, mock_stdout.getvalue())

    @mock.patch(
        'openstack_requirements.cmds.check_exists.read_requirements_file',
        mock_read_requirements_file)
    def test_project_req_not_include_uc_version(self):
        self.useFixture(common.project_fixture)

        # lets change the six requirement not include the u-c version
        proj_read = project.read(common.project_fixture.root)
        proj_read['requirements']['requirements.txt'] = \
            proj_read['requirements']['requirements.txt'][:-1] + \
            '<1.10.0,>1.10.0\n'
        expected_out = ('six must be <= 1.10.0 from upper-constraints and '
                        'include the upper-constraints version')

        # Start capturing some output
        mock_stdout = io.StringIO()
        with mock.patch('openstack_requirements.project.read',
                        return_value=proj_read), \
                mock.patch('sys.stdout', mock_stdout):
            ret = check_exists.main([common.project_fixture.root])
        self.assertEqual(ret, 1)
        self.assertIn(expected_out, mock_stdout.getvalue())
