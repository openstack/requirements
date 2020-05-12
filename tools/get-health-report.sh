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

# Checks all of our tracked packages for any issues

TOOLSDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASEDIR=$(dirname ${TOOLSDIR})

source ${TOOLSDIR}/functions

# Make sure we are using our venv
enable_venv "${BASEDIR}"

update=
if [[ "$#" -eq 1 ]]; then
    update="${1}"
fi

# Save off our current timestamp for use later
current=$(date +%s)

# Loop through each package to get details and check for issues
get_tracked_requirements
for req in $reqs; do
    count=$(search_reqs ${req} |
            grep -v " openstack/${req}  " |
            wc -l)

    metadata=$(curl -s -L "https://pypi.org/pypi/$req/json")
    summary=$(echo "${metadata}" | jq -r '.info.summary')
    last_release=$(echo "${metadata}" | jq -r '.info.version')
    release_date=$(echo "${metadata}" | jq -r ".releases.\"${last_release}\" | .[0].upload_time")

    # Print basic package information
    echo "${req}"
    if [[ "${summary}" != "" ]]; then
        echo "    Summary:       ${summary}"
    fi
    echo "    Used by repos: ${count}"
    echo "    Last release:  ${last_release}"
    echo "    Release date:  ${release_date}"

    # Check for various things to warn about
    package_name=$(echo "${metadata}" | jq -r '.info.name')
    if [[ "${req}" != "${package_name}" ]]; then
        echo "    WARNING: In g-r as ${req} but actual name is ${package_name}"
    fi

    py3=$(echo "${metadata}" | \
        jq -r '.info.classifiers | .[]' | \
        grep "Programming Language :: Python :: 3")
    if [[ -z ${py3} ]]; then
        echo "    WARNING: No python 3 classifier in metadata"
    fi

    release=$(date -d $release_date +%s)
    seconds_since_release=$((current-release))
    years_since_release=$((seconds_since_release/60/60/24/365))
    message=$(echo "It's been ${years_since_release} years since last release")
    if [[ ${years_since_release} -gt 4 ]]; then
        echo "    !!WARNING!! ${message}"
    elif [[ ${years_since_release} -gt 2 ]]; then
        echo "    WARNING ${message}"
    fi
done
