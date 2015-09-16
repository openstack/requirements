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

import io
import os
import textwrap

import fixtures
import testscenarios
import testtools

from openstack_requirements.cmds import edit_constraint as edit
from openstack_requirements import requirement


load_tests = testscenarios.load_tests_apply_scenarios


class SmokeTest(testtools.TestCase):

    def test_make_url(self):
        stdout = io.StringIO()
        tmpdir = self.useFixture(fixtures.TempDir()).path
        constraints_path = os.path.join(tmpdir, 'name.txt')
        with open(constraints_path, 'wt') as f:
            f.write('bar===1\nfoo===1.0.2\nquux==3\n')
        rv = edit.main(
            [constraints_path, 'foo', '--', '-e /path/to/foo'], stdout)
        self.assertEqual(0, rv)
        content = open(constraints_path, 'rt').read()
        self.assertEqual('-e /path/to/foo\nbar===1\nquux==3\n', content)

    def test_edit_paths(self):
        stdout = io.StringIO()
        tmpdir = self.useFixture(fixtures.TempDir()).path
        constraints_path = os.path.join(tmpdir, 'name.txt')
        with open(constraints_path, 'wt') as f:
            f.write(textwrap.dedent("""\
                file:///path/to/foo#egg=foo
                -e file:///path/to/bar#egg=bar
                """))
        rv = edit.main(
            [constraints_path, 'foo', '--', '-e file:///path/to/foo#egg=foo'],
            stdout)
        self.assertEqual(0, rv)
        content = open(constraints_path, 'rt').read()
        self.assertEqual(textwrap.dedent("""\
            -e file:///path/to/foo#egg=foo
            -e file:///path/to/bar#egg=bar
            """), content)


class TestEdit(testtools.TestCase):

    def test_add(self):
        reqs = {}
        res = edit.edit(reqs, 'foo', 'foo==1.2')
        self.assertEqual(requirement.Requirements(
            [requirement.Requirement('', '', '', '', 'foo==1.2')]), res)

    def test_delete(self):
        reqs = requirement.parse('foo==1.2\n')
        res = edit.edit(reqs, 'foo', '')
        self.assertEqual(requirement.Requirements([]), res)

    def test_replace(self):
        reqs = requirement.parse('foo==1.2\n')
        res = edit.edit(reqs, 'foo', 'foo==1.3')
        self.assertEqual(requirement.Requirements(
            [requirement.Requirement('', '', '', '', 'foo==1.3')]), res)

    def test_replace_many(self):
        reqs = requirement.parse('foo==1.2;p\nfoo==1.3;q')
        res = edit.edit(reqs, 'foo', 'foo==1.3')
        self.assertEqual(requirement.Requirements(
            [requirement.Requirement('', '', '', '', 'foo==1.3')]), res)

    def test_replace_non_canonical(self):
        new_req = '-e file:///path#egg=foo_baz'
        reqs = requirement.parse("foo-baz===1.0.2\n")
        res = edit.edit(reqs, 'foo_baz', new_req)
        self.assertEqual(res, requirement.Requirements(
            [requirement.Requirement('', '', '', '', new_req)]))
