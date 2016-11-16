#! /usr/bin/env python

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


import argparse
import re

import pkg_resources

overrides = dict()
# List of overrides needed. Ignore version in pip-freeze and use the one here
# instead. Example:
# suds 0.4.1 isn't pip installable but is in distribution packages
# overrides['suds'] = 'suds==0.4'
# apt package of libvirt-python is lower then our minimum requirement
# overrides['libvirt-python'] = None


def cap(requirements, frozen):
    """Cap requirements to version in freeze.

    Go through every package in requirements and try to cap.

    Input: two arrays of lines.
    Output: Array of new lines.
    """
    output = []
    for line in requirements:
        try:
            req = pkg_resources.Requirement.parse(line)
            specifier = str(req.specifier)
            if any(op in specifier for op in ['==', '~=', '<']):
                # if already capped, continue
                output.append(line)
                continue
        except ValueError:
            # line was a comment, continue
            output.append(line)
            continue
        if req.project_name in overrides:
            new_line = overrides[req.project_name]
            if new_line:
                output.append(overrides[req.project_name])
            else:
                output.append(line)
            continue
        # add cap
        new_cap = cap_requirement(req.project_name, frozen)
        if new_cap:
            output.append(pin(line, new_cap))
        else:
            output.append(line)
    return output


def pin(line, new_cap):
    """Add new cap into existing line

    Don't use pkg_resources so we can preserve the comments.
    """
    end = None
    use_comma = False
    parts = line.split(' #')
    if len(split(parts[0].strip())) > 1:
        use_comma = True
    if "#" in line:
        # if comment
        end = parts[1]
    # cap to new max version
    if end:
        new_end = "<=%s #%s" % (new_cap, end)
    else:
        new_end = "<=%s" % new_cap
    if use_comma is True:
        return "%s,%s" % (parts[0].strip(), new_end)
    else:
        return "%s%s" % (parts[0].strip(), new_end)


def split(line):
    return re.split('[><=]', line)


def cap_requirement(requirement, frozen):
    # Find current version of requirement in freeze
    specifier = frozen.get(requirement, None)
    if specifier:
        return split(str(specifier))[-1]
    return None


def freeze(lines):
    """Parse lines from freeze file into a dict.

    Where k:v is project_name:specifier.
    """
    freeze = dict()

    for line in lines:
        try:
            req = pkg_resources.Requirement.parse(line)
            freeze[req.project_name] = req.specifier
        except ValueError:
            # not a valid requirement, can be a comment, blank line etc
            continue
    return freeze


def main():
    parser = argparse.ArgumentParser(
        description="Take the output of "
                    "'pip freeze' and use the installed versions to "
                    "caps requirements.")
    parser.add_argument('requirements', help='requirements file input')
    parser.add_argument(
        'freeze',
        help='output of pip freeze, taken from a full tempest job')
    args = parser.parse_args()
    with open(args.requirements) as f:
        requirements = [line.strip() for line in f.readlines()]
    with open(args.freeze) as f:
        frozen = freeze([line.strip() for line in f.readlines()])
    for line in cap(requirements, frozen):
        print(line)


if __name__ == '__main__':
    main()
