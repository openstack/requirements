#!/bin/bash -ex

# Copyright 2015 OpenStack Foundation
#
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

# Remove the raw list if a copy already exists, since we're going to
# append to it in this loop.
rm -f raw-requirements.txt
for PROJECT in $(cat projects.txt); do
    # Reuse existing clones in case this is being rerun.
    if [ ! -d $PROJECT ]; then
        mkdir -p $PROJECT
        # In case this makes it into a CI job, use local copies.
        if [ -d /opt/git/$PROJECT/.git ]; then
            git clone file:///opt/git/$PROJECT $PROJECT
        else
            git clone https://git.openstack.org/$PROJECT.git $PROJECT
        fi
    fi
    pushd $PROJECT
    git remote update
    # Loop over the default (HEAD) and any feature branches.
    for BRANCH in $(
        git branch -a \
            | grep '^  remotes/origin/\(feature/\|HEAD \)' \
            | cut -d' ' -f3
    ); do
        git checkout $BRANCH
        # These are files which are considered by the update.py script,
        # so check them all for the sake of completeness.
        for FILE in \
            requirements-py2.txt \
            requirements-py3.txt \
            requirements.txt \
            test-requirements-py2.txt \
            test-requirements-py3.txt \
            test-requirements.txt \
            tools/pip-requires \
            tools/test-requires \
            doc/requirements.txt
        do
            if [ -f $FILE ]; then
                # Add diagnostic comments to aid debugging.
                echo -e "\n# -----\n# $PROJECT $BRANCH $FILE\n# -----" \
                    >> ${OLDPWD}/raw-requirements.txt
                cat $FILE >> ${OLDPWD}/raw-requirements.txt
            fi
        done
    done
    popd
done

# Generate a unique set of package names from the raw list of all
# project requirements filtered for the same lines ignored by the
# update.py script, lower-cased with hyphens normalized to underscores.
sed -e '/^\($\|#\|http:\/\/tarballs.openstack.org\/\|-e\|-f\)/d' \
    -e 's/^\([^<>=! ]*\).*/\L\1/' -e s/-/_/g raw-requirements.txt \
    | sort -u > all-requirements.txt

# From here on, xtrace gets uselessly noisy.
set +x

# Loop over the set of package names from the global requirements list.
for CANDIDATE in $(
    sed -e '/^\($\|#\)/d' -e 's/^\([^<>=!; ]*\).*/\1/' global-requirements.txt
); do
    # Search for the package name in the set of project requirements,
    # normalizing hyphens to underscores, and output the package name if
    # not found.
    grep -iq ^$(echo $CANDIDATE | sed s/-/_/g)$ all-requirements.txt \
        || echo $CANDIDATE
done | sort > cruft-requirements.txt

# Provide a helpful summary of the results.
if [ -s cruft-requirements.txt ] ; then
    echo -e "\nCruft entries found in global-requirements.txt:\n"
    cat cruft-requirements.txt
else
    echo -e "\nSomething must be wrong--I found no cruft!!!"
fi
