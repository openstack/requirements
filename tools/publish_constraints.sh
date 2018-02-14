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

function get_from_git {
    ref=$1
    series=$2
    path=${3:-publish/constraints/upper}

    git show ${ref}:upper-constraints.txt > ${path}/${series}.txt
}

# Make the directory tree, don't fail if it already exists
mkdir -p publish/constraints/upper
# Clear out any stale files, don't fail if we just created it
rm publish/constraints/upper/* || true

case "$ZUUL_BRANCH" in
stable/*)
    series=$(basename "$ZUUL_BRANCH")
    get_from_git origin/$ZUUL_BRANCH $series
;;
master)
    # NOTE(tonyb): Publish EOL'd constraints files.  We do this here as a
    # quick way to publish the data.  It can be removed anytime after the first
    # successful run
    for tag in juno-eol kilo-eol liberty-eol mitaka-eol newton-eol ; do
        # trim the '-eol'
        series=${tag::-4}
        get_from_git $tag $series
    done

    for series in queens rocky ; do
        if ! git rev-parse origin/stable/$series ; then
            get_from_git origin/master $series
        fi
    done
    get_from_git origin/master master
;;
esac
