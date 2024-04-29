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

from concurrent import futures
import datetime
import os
import sys

from packaging import requirements
import requests

GLOBAL_REQS = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    '..',
    'global-requirements.txt',
)
MAX_EXCLUDE_AGE = datetime.timedelta(365 * 2)


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


def validate_excludes(
    name: str, specifiers: requirements.SpecifierSet
) -> tuple[str, str]:
    data = requests.get(f'https://pypi.org/pypi/{name}/json').json()
    latest_release = max(data['releases'])

    result = []
    for specifier in specifiers:
        if specifier.operator != '!=':
            result.append(specifier)
            # non-exclusion specifier
            continue

        exclude = specifier.version

        if exclude == latest_release:
            print(
                f'Release {exclude} is the latest release for package {name}. '
                f'Skipping checks.'
            )
            result.append(specifier)
            continue

        release = data['releases'].get(exclude)
        if not release:
            print(
                f'Failed to find release {exclude} for package {name}',
                file=sys.stderr,
            )
            continue

        if all(r['yanked'] for r in release):
            print(f'Release {exclude} for package {name} was yanked')
            continue

        now = datetime.datetime.now(datetime.timezone.utc)
        age = min(
            (now - datetime.datetime.fromisoformat(r['upload_time_iso_8601']))
            for r in release
        )
        if age >= MAX_EXCLUDE_AGE:
            print(
                f'Release {exclude} for package {name} is older than the '
                f'upper limit for age '
                f'({age.days} days >= {MAX_EXCLUDE_AGE.days} days)'
            )
            continue

        # exclude is recent enough and not yanked so keep it
        result.append(specifier)

    return name, ','.join(sorted(str(r) for r in result))


def remove_old_excludes():
    """Remove excludes for old package versions.

    If we exclude e.g. v1.22 of a package but that version was release over 2
    years ago and said package is currently at v1.45, then there's no reason to
    keep that exclude around.
    """
    deps: dict[str, set[str]] = {}

    with open(GLOBAL_REQS) as fh:
        for line in fh.readlines():
            if not line.strip() or line.startswith('#'):
                # ignore blank lines and comments
                continue

            req = requirements.Requirement(line.split(' #')[0])

            if req.name in ('setuptools',):
                # ignore certain packages where we want to retain all excludes
                continue

            # these shouldn't be in our global-requirements file so we don't
            # handle them...but make sure
            assert not req.extras, f'unexpected extras: {req}'
            assert not req.url, f'unexpected url: {req}'

            if any(s.operator == '!=' for s in req.specifier):
                deps[req.name] = req.specifier

    with futures.ThreadPoolExecutor() as executor:
        res = executor.map(validate_excludes, *zip(*deps.items()))

    deps.update(dict(res))

    with open(GLOBAL_REQS) as fh:
        data = fh.read()

    with open(GLOBAL_REQS, 'w') as fh:
        for i, line in enumerate(data.split('\n')):
            if i != 0:
                fh.write('\n')

            if line.startswith('#') or not line.strip():
                # skipped (empty or comment)
                fh.write(line)
                continue

            dep, comment, license = line.partition('  #')
            req = requirements.Requirement(dep)
            if req.name not in deps:
                # skipped (no cap)
                fh.write(line)
                continue

            req.specifier = deps[req.name]
            # requirements.Requirement.__str__ adds a space after the semicolon
            # which we don't want
            fh.write(str(req).replace('; ', ';') + comment + license)


if __name__ == '__main__':
    remove_old_excludes()
    sort()
