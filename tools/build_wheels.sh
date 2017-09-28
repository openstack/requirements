#!/bin/bash
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# Generate wheels for all of the requirements, ignoring any packages
# that won't build wheels so we get as many as possible. This is meant
# to be used on a development box combined with devpi and a wheelhouse
# configuration setting for pip, such as described in
# https://www.berrange.com/posts/2014/11/14/faster-rebuilds-for-python-virtualenv-trees/
#
# Usage:
#
#   install pip for the version(s) of python you want
#
#   use each of those versions of pip to install the wheel package
#     pip2.7 install wheel
#     pip3.3 install wheel
#     pip3.4 install wheel
#
#   run this script, passing those versions on the command line:
#
#     ./tools/build_wheels.sh 2.7 3.3 3.4

versions="$*"

if [ -z "$versions" ] ; then
    echo "ERROR: Usage: $0 <version>" 1>&2
    echo "Example: $0 2.7 3.3 3.4" 1>&2
    exit 1
fi

grep -v '^$\|#' global-requirements.txt | while read req
do
    echo "Building $req"
    for v in $versions
    do
        pip${v} wheel "$req"
    done
done
