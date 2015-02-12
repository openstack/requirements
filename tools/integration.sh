#!/bin/bash -xe

function mkvenv {
    venv=$1

    rm -rf $venv
    virtualenv $venv
    $venv/bin/pip install -U pip wheel pbr
}

function install_all_of_gr {
    mkvenv $tmpdir/all_requirements
    $tmpdir/all_requirements/bin/pip install -r $REPODIR/requirements/global-requirements.txt
}

# BASE should be a directory with a subdir called "new" and in that
#      dir, there should be a git repository for every entry in PROJECTS
BASE=${BASE:-/opt/stack}

REPODIR=${REPODIR:-$BASE/new}

# TODO: Figure out how to get this on to the box properly
sudo apt-get install -y --force-yes libvirt-dev libxml2-dev libxslt-dev libmysqlclient-dev libpq-dev libnspr4-dev pkg-config libsqlite3-dev libzmq-dev libffi-dev libldap2-dev libsasl2-dev ccache

# FOR numpy / pyyaml
sudo apt-get build-dep -y --force-yes python-numpy
sudo apt-get build-dep -y --force-yes python-yaml

# And use ccache explitly
export PATH=/usr/lib/ccache:$PATH

tmpdir=$(mktemp -d)

# Set up a wheelhouse
export WHEELHOUSE=${WHEELHOUSE:-$tmpdir/.wheelhouse}
export PIP_WHEEL_DIR=${PIP_WHEEL_DIR:-$WHEELHOUSE}
export PIP_FIND_LINKS=${PIP_FIND_LINKS:-file://$WHEELHOUSE}
mkvenv $tmpdir/wheelhouse
# Not all packages properly build wheels (httpretty for example).
# Do our best but ignore errors when making wheels.
set +e
grep -v '^#' $REPODIR/requirements/global-requirements.txt | while read req
do
    $tmpdir/wheelhouse/bin/pip wheel "$req"
done
set -e

#BRANCH
BRANCH=${OVERRIDE_ZUUL_BRANCH=:-master}
# PROJECTS is a list of projects that we're testing
PROJECTS=$*

projectdir=$tmpdir/projects
mkdir -p $projectdir

# Attempt to install all of global requirements
install_all_of_gr

for PROJECT in $PROJECTS ; do
    SHORT_PROJECT=$(basename $PROJECT)
    if ! grep 'pbr' $REPODIR/$SHORT_PROJECT/setup.py >/dev/null 2>&1
    then
        # project doesn't use pbr
        continue
    fi
    if [ $SHORT_PROJECT = 'pypi-mirror' ]; then
        # pypi-mirror doesn't consume the mirror
        continue
    fi
    if [ $SHORT_PROJECT = 'jeepyb' ]; then
        # pypi-mirror doesn't consume the mirror
        continue
    fi
    if [ $SHORT_PROJECT = 'tempest' ]; then
        # Tempest doesn't really install
        continue
    fi
    if [ $SHORT_PROJECT = 'requirements' ]; then
        # requirements doesn't really install
        continue
    fi

    # set up the project synced with the global requirements
    sudo chown -R $USER $REPODIR/$SHORT_PROJECT
    (cd $REPODIR/requirements && python update.py $REPODIR/$SHORT_PROJECT)
    pushd $REPODIR/$SHORT_PROJECT
    if ! git diff --quiet ; then
        git commit -a -m'Update requirements'
    fi
    popd

    # Clone from synced repo
    shortprojectdir=$projectdir/$SHORT_PROJECT
    git clone $REPODIR/$SHORT_PROJECT $shortprojectdir

    # Test python setup.py install
    installvenv=$tmpdir/install
    mkvenv $installvenv

    installprojectdir=$projectdir/install$SHORT_PROJECT
    git clone $shortprojectdir $installprojectdir
    cd $installprojectdir
    $installvenv/bin/python setup.py install

    # Ensure the install_package_data is doing the thing it should do
    if [ $SHORT_PROJECT = 'nova' ]; then
        find $installvenv | grep migrate.cfg
    fi
done
