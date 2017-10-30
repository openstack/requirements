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

function cleanup {
    # Don't abort early if there's a problem in the clean up
    set +e
    git checkout $start_branch
    git branch -D ${topic}
}

function usage {
    (
    if [ -n "$1" ] ; then
        echo $0 $1
    fi
    echo $0 '-p [project] -t [topic] -c [change] -s [style]'
    echo ' project: The directory for the openstack project'
    echo ' topic  : The topic as passed to git review'
    echo ' change : The change that the no-op change depends on if any'
    echo ' style  : the style of change [doc|python|releasenotes]'
    ) >&2
    exit 1
}

project=''
topic=''
change=''
style=''
verbose=0

while getopts vp:t:c:s: opt ; do
    case $opt in
    p)
        project=${OPTARG/=}
    ;;
    t)
        topic=${OPTARG/=}
    ;;
    c)
        change=${OPTARG/=}
    ;;
    s)
        style=${OPTARG/=}
    ;;
    v)
        verbose=$((verbose + 1))
    ;;
    \?)
        usage
    ;;
    esac
done

if [ -z "$project" ] ; then
    usage 'project missing!'
fi

if [ -z "$topic" ] ; then
    usage 'topic missing!'
# NOTE(tonyb): if the topic without white space or / == itself then it didn't
#              contain any bad characters
elif [ "${topic/[ 	\/]/}" != "${topic}" ] ; then
    echo "topic [$topic] contains white space or /'s"
    exit 1
fi

# TODO(tonyb): Do we need to validate that change looks like a change ID?
#             With zuulv3 it could infact be a url or anything so it'd be
#             hard to validate

if [ -z "$style" ] ; then
    usage 'style missing!'
elif [[ ! 'releasenotes doc python' =~ "$style" ]] ; then
    usage "style $style invalid"
fi

if [ $verbose -ge 1 ] ; then
    printf '%-10s: %s\n' 'Project' "$project"
    printf '%-10s: %s\n' 'Topic' "$topic"
    printf '%-10s: %s\n' 'Change' "$change"
    printf '%-10s: %s\n' 'Style' "$style"
    printf '%-10s: %s\n' 'Verbosity' "$verbose"
fi

[ $verbose -ge 2 ] && set -x

cd $project

# FIXME(tonyb): Save the current branch
start_branch=$(git rev-parse --symbolic --abbrev-ref HEAD)
if [ "$start_branch" == "$topic" ] ; then
    echo $0 Current git branch is the same as topic aborting >&2
    exit 1
fi

# NOTE(tonyb): git diff exits with 0 if the tree is clean
if ! git diff --exit-code -s ; then
    echo $0 Current working tree is dirty aborting >&2
    exit 1
fi

# The real works starts here so now lets get a bit careful and exit if a
# command fails
set -e

git branch -D ${topic} || true
# NOTE(tonyb): We don't really need to switch branches we could do it all in
#              the current branch but this is easier.
git checkout -b ${topic} -t origin/master

# Install the clean up handler
trap cleanup EXIT

case "$style" in
releasenotes|doc)
    file="${style}/source/index.rst"
    [ "$verbose" -ge 3 ] && git diff
    echo -e '\n\n.. # no-op test' >> $file
    git add $file
;;
python)
    # TODO(tonyb): work out a 99% safe way to modify python code
    echo $0 python syle change isn\'t finished
    # NOTE(tonyb): The pipeline works like:
    # Find all the __init__.py files that contain something.
    #   We know this has to be code of some sort or they'd file pep8.
    # Remove tests
    #   Tests might trick the gate into using a subset of jobs
    # Sort by the 3rd path element.
    #  project/dir/__init__.py this will mean that paths that don't have a
    #  dir component will sort to the top.  This (I hope) means that we'll
    #  prefer the project __init__.py if it exists
    # Grab only the first item
    #  We could store this in an array and do something smarter if we wanted
    file=$(find * -type f -name __init__.py -not -empty | \
                grep -v tests | \
                sort -t / -k+3 |\
                head -n 1)
    if [ -n "$file" ] ; then
        echo -e '\n\n# no-op test' >> ${file}
        [ "$verbose" -ge 3 ] && git diff
        git add $file
    else
        echo $0 failed to find file to patch for $style
        exit 1
    fi
;;
esac

commit_msg="WiP: Do not merge - $topic"
if [ -n "$change" ] ; then
    commit_msg+="

Depends-On: $change"
fi

git commit -m "$commit_msg"
git review -t ${topic}
# TODO(tonyb): Check for vote-a-tron and -W the change if it's available
