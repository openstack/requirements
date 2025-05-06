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

import openstack_requirements
import pkg_resources
import sys
import testtools

from openstack_requirements.cmds import check_conflicts
from openstack_requirements.utils import read_requirements_file
from unittest import mock


class CheckConflictsTest(testtools.TestCase):

    def setUp(self):
        super(CheckConflictsTest, self).setUp()

    @mock.patch.object(pkg_resources, "require")
    def test_all_uc_required(self, mock_require):
        pyver = "python_version=='%s.%s'" % (
            sys.version_info[0],
            sys.version_info[1],
        )

        test_args = [
            "check_conflicts",
            "upper-constraints.txt",
            "upper-constraints-xfails.txt",
        ]
        with mock.patch.object(sys, "argv", test_args):
            ret = check_conflicts.main()
            self.assertEqual(ret, 0)

        pkgs = set()
        for name, spec_list in read_requirements_file(
            "upper-constraints.txt"
        ).items():
            for req, _ in spec_list:
                if req.markers in ["", pyver]:
                    pkgs.add(name)

        rpkgs = set([call.args[0] for call in mock_require.mock_calls])

        self.assertEqual(pkgs, rpkgs)

    @mock.patch("importlib.metadata.version", return_value="1.0.0")
    @mock.patch.object(pkg_resources, "require",
                       side_effect=pkg_resources.DistributionNotFound)
    def test_all_uc_alternative_method(self, mock_require, mock_metadata):
        pyver = "python_version=='%s.%s'" % (
            sys.version_info[0],
            sys.version_info[1],
        )

        test_args = [
            "check_conflicts",
            "upper-constraints.txt",
            "upper-constraints-xfails.txt",
        ]
        original_fn = (
            openstack_requirements.cmds.check_conflicts.read_requirements_file
        )

        def patched_uc_read(filename):
            output = {}
            uc = original_fn(filename)

            for name, spec_list in uc.items():
                fake_spec_list = []
                for spec in spec_list:
                    fake_req = openstack_requirements.requirement.Requirement(
                        name, "", "===1.0.0", spec[0].markers, ""
                    )
                    fake_spec_list.append((fake_req, f"{name}===1.0.0\n"))
                output[name] = fake_spec_list
            return output

        with (
            mock.patch.object(sys, "argv", test_args),
            mock.patch(
                "openstack_requirements.cmds.check_conflicts."
                "read_requirements_file",
                side_effect=patched_uc_read,
            ),
        ):
            ret = check_conflicts.main()
            self.assertEqual(ret, 0)

        pkgs = set()
        for name, spec_list in read_requirements_file(
            "upper-constraints.txt"
        ).items():
            for req, _ in spec_list:
                if req.markers in ["", pyver]:
                    pkgs.add(name)

        rpkgs = set([call.args[0] for call in mock_metadata.mock_calls])

        self.assertEqual(pkgs, rpkgs)

    @mock.patch("importlib.metadata.version", return_value="2.0.0")
    @mock.patch.object(
        pkg_resources,
        "require",
        side_effect=pkg_resources.DistributionNotFound,
    )
    def test_all_uc_alternative_method_failure(
        self, mock_require, mock_metadata
    ):
        test_args = [
            "check_conflicts",
            "upper-constraints.txt",
            "upper-constraints-xfails.txt",
        ]
        original_fn = (
            openstack_requirements.cmds.check_conflicts.read_requirements_file
        )

        def patched_uc_read(filename):
            output = {}
            uc = original_fn(filename)

            for name, spec_list in uc.items():
                fake_spec_list = []
                for spec in spec_list:
                    fake_req = openstack_requirements.requirement.Requirement(
                        name, "", "===1.0.0", spec[0].markers, ""
                    )
                    fake_spec_list.append((fake_req, f"{name}===1.0.0\n"))
                output[name] = fake_spec_list
            return output

        with (
            mock.patch.object(sys, "argv", test_args),
            mock.patch(
                "openstack_requirements.cmds.check_conflicts."
                "read_requirements_file",
                side_effect=patched_uc_read,
            ),
        ):
            exc = self.assertRaises(ValueError, check_conflicts.main)

            self.assertIn(
                "version mismatch version 1.0.0 is required and current "
                "package version is 2.0.0.",
                str(exc),
            )
