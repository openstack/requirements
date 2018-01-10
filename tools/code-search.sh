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

declare -a projects
in_projects=0
base=$HOME

while [ $# -gt 1 ] ; do
    case "$1" in
    --prefix)
        prefix=$2
        shift 1
    ;;
    --projects)
        in_projects=1
    ;;
    --)
        break
    ;;
    *)
        if [ "$in_projects" == 1 ] ; then
            projects+=($1)
        else
            echo Unknown arg/context >&2
            exit 1
        fi
    ;;
    esac
    shift 1
done

for prj in ${projects[@]} ; do
    (
    cd $prj>/dev/null 2>&1 && \
        git grep -HEin $@ 2>/dev/null|sed -e "s,^,${prj#$prefix}:,g"
    )
done
