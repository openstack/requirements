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

# This script, when run from the root directory of this repository, will
# search the default and feature branches of all projects listed in the
# projects.txt file for declared dependencies, then output a list of any
# entries in the global-requirements.txt file which are not actual
# dependencies of those projects. Old dependencies which were removed
# from projects or which were used only for projects which have since
# been removed should be cleaned up, but many entries likely represent
# recent additions which still have pending changes to add them to one
# or more projects. In most cases, git pickaxe will yield the answer.

# Note(tonyb): Expand HEAD into something that's hopefully more human
#              readable
declare -a branches=($(git describe --always) origin/master
                     origin/stable/ocata
                     origin/stable/newton
                     origin/stable/mitaka
                    )

function search() {
    git grep -hEi "^${1}[=><!]" ${2} -- "${3}"
}

printf '\nRequirements\n'
for branch in ${branches[@]} ; do
    printf "%-22s: %s\n" $branch "$(search $1 $branch global-requirements.txt)"
done

printf '\nConstraints\n'
for branch in ${branches[@]} ; do
    printf "%-22s: %s\n" $branch "$(search $1 $branch upper-constraints.txt)"
done
