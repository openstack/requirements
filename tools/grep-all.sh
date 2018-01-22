#!/usr/bin/env bash

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

# Note(tonyb): Expand HEAD into something that's hopefully more human
#              readable
declare -a branches=($(git describe --always) origin/master)
branches+=($(git branch --no-color -r --list 'origin/stable/*'))

declare -a tags=($(git tag --list '*-eol' | sort))

if [ $# -ne 1 ]; then
    echo "Usage: $0 dependency-name" 1>&2
    exit 1
fi

function search {
    git grep -hEi "^${1}[=><!]" "${2}:${3}" 2>/dev/null
}

printf '\nRequirements\n------------\n'
for branch in ${branches[@]} ; do
    printf "%-22s: %s\n" $branch "$(search $1 $branch global-requirements.txt)"
done
echo
for tag in ${tags[@]} ; do
    printf "%-22s: %s\n" $tag "$(search $1 $tag global-requirements.txt)"
done

printf '\nConstraints\n-----------\n'
for branch in ${branches[@]} ; do
    printf "%-22s: %s\n" $branch "$(search $1 $branch upper-constraints.txt)"
done
echo
for tag in ${tags[@]} ; do
    printf "%-22s: %s\n" $tag "$(search $1 $tag upper-constraints.txt)"
done
