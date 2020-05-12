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

# Lists any packages in global-constraints that appear to no longer be used

TOOLSDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASEDIR=$(dirname ${TOOLSDIR})

source ${TOOLSDIR}/functions

# Make sure we are using our venv
enable_venv "${BASEDIR}"

update=
if [[ "$#" -eq 1 ]]; then
    update="${1}"
fi

# Loop through each package and check for its presence in any repo's
# requirements files other than mentions in its own repo
get_tracked_requirements
for req in $reqs; do
    count=$(search_reqs ${req} |
            grep -v " openstack/${req}  " |
            wc -l)
    if [[ ${count} -eq 0 ]]; then
        echo "${req}"

        # See if we should clean up the requirements files
        if [[ "${update}" == "--update" ]]; then
            sed -i "/${req}/d" global-requirements.txt
            sed -i "/${req}/d" upper-constraints.txt
        fi
    fi
done
