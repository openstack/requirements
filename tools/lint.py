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

import os

GLOBAL_REQS = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    '..',
    'global-requirements.txt',
)


def sort() -> None:
    """Sort global-requirements, respecting sections."""
    section_headers: dict[str, str] = {}
    section_deps: dict[str, list[tuple[str, str | None]]] = {}
    section: str = ''
    deps: list[tuple[str, str | None]] = []
    comment: str = ''

    with open(GLOBAL_REQS) as fh:
        for line in fh.readlines():
            if not line.strip():
                continue

            if line.startswith('## section:'):
                if section:
                    section_deps[section] = sorted(
                        deps, key=lambda x: x[0].lower()
                    )
                    deps = []

                section = line.removeprefix('## section:')
                section_headers[section] = line
                continue

            if line.startswith('##'):
                section_headers[section] += line
                continue

            if line.startswith('#'):
                comment += line
                continue

            deps.append((line, comment or None))
            comment = ''

    section_deps[section] = sorted(
        deps, key=lambda x: x[0].lower()
    )

    with open(GLOBAL_REQS, 'w') as fh:
        for i, section in enumerate(section_deps):
            if i != 0:
                fh.write('\n')

            fh.write(section_headers[section])
            fh.write('\n')

            for dep, dep_comment in section_deps[section]:
                if dep_comment:
                    fh.write(dep_comment)

                fh.write(dep)


if __name__ == '__main__':
    sort()
