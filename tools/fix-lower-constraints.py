#!/usr/bin/env python
#
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
"""
Instructions:

 1. virtualenv venv
 2. source venv/bin/activate
 3. pip install /path/to/local/copy/of/requirements/repository
 4. cd /path/to/project/to/fix
 5. .../requirements/tools/fix-lower-constraints.py > new-lc.txt
 6. mv new-lc.txt lower-constraints.txt
 7. Update the patch and resubmit it to gerrit.
"""

import io

from openstack_requirements import requirement


def read_file(name):
    with io.open(name, 'r', encoding='utf-8') as f:
        return requirement.parse(f.read())


requirements = read_file('requirements.txt')
requirements.update(read_file('test-requirements.txt'))
constraints = read_file('lower-constraints.txt')

output = []

for const in constraints.values():
    const = const[0][0]
    actual = const.specifiers.lstrip('=')
    name = const.package.lower()
    if name not in requirements:
        # Ignore secondary dependencies
        output.append(const.to_line())
        continue
    for req, _ in requirements[name]:
        min = [
            s
            for s in req.specifiers.split(',')
            if '>' in s
        ]
        if not min:
            # If there is no lower bound, assume the constraint is
            # right.
            output.append(const.to_line())
            continue
        required = min[0].lstrip('>=')
        if required != actual:
            output.append('{}=={}\n'.format(
                const.package, required))
        else:
            output.append(const.to_line())

for line in sorted(output, key=lambda x: x.lower()):
    if not line.strip():
        continue
    print(line.rstrip())
