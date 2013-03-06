#!/bin/bash

GIT_DIR=${GIT_DIR-~/git/openstack}
FETCH_REMOTE=${FETCH_REMOTE-}
REMOTE_BRANCH=${REMOTE_BRANCH-gerrit/master}
PROJECTS=${PROJECTS-"nova glance keystone cinder quantum horizon swift heat ceilometer oslo-incubator python-novaclient python-glanceclient python-keystoneclient python-cinderclient python-quantumclient python-swiftclient"}

fetch() {
    for p in $PROJECTS; do
        cd $GIT_DIR/$p
        git fetch gerrit
    done
}

concat() {
    path=$1; shift

    for p in $PROJECTS; do
        cd $GIT_DIR/$p
        git cat-file -p $REMOTE_BRANCH:$path
    done | tr A-Z a-z| sed 's/#.*$//; s/ *$//; /^ *$/d' | sort | uniq
}

[ -n "$FETCH_REMOTE" ] && fetch

concat tools/pip-requires > $GIT_DIR/requirements/tools/pip-requires

(sed p $GIT_DIR/requirements/tools/pip-requires;
    concat tools/test-requires ) |
sort | uniq -u > $GIT_DIR/requirements/tools/test-requires
