#!/bin/bash -xe
# Parameters
# PBR_PIP_VERSION :- if not set, run pip's latest release, if set must be a
#    valid reference file entry describing what pip to use.
# Bootstrappping the mkenv needs to install *a* pip
export PIPVERSION=pip
PIPFLAGS=${PIPFLAGS:-}

function mkvenv {
    venv=$1

    rm -rf $venv
    virtualenv $venv
    $venv/bin/pip install -U $PIPVERSION wheel pbr
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
mkvenv $tmpdir/wheelhouse
# Specific PIP version - must succeed to be useful.
# - build/download a local wheel so we don't hit the network on each venv.
if [ -n "${PBR_PIP_VERSION:-}" ]; then
    td=$(mktemp -d)
    $tmpdir/wheelhouse/bin/pip wheel -w $td $PBR_PIP_VERSION
    # This version will now be installed in every new venv.
    export PIPVERSION="$td/$(ls $td)"
    $tmpdir/wheelhouse/bin/pip install -U $PIPVERSION
    # We have pip in global-requirements as open-ended requirements,
    # but since we don't use -U in any other invocations, our version
    # of pip should be sticky.
fi

#BRANCH
BRANCH=${OVERRIDE_ZUUL_BRANCH=:-master}
# PROJECTS is a list of projects that we're testing
PROJECTS=$*

projectdir=$tmpdir/projects
mkdir -p $projectdir

# Attempt to install all of global requirements
install_all_of_gr

# Install requirementsrrepo itself.
$tmpdir/all_requirements/bin/pip install $REPODIR/requirements
UPDATE="$tmpdir/all_requirements/bin/update-requirements"

# Check that we can generate a 2.7-only upper-requirements.txt file with the
# change that is being proposed. 2.7-only is needed because we're not
# backporting markers to kilo.
$tmpdir/all_requirements/bin/generate-constraints -p /usr/bin/python2.7 \
    -b $REPODIR/requirements/blacklist.txt \
    -r $REPODIR/requirements/global-requirements.txt

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
    if [[ "$BRANCH" =~ "stable" ]]; then
        # When testing stable, only attempt to sync to projects that also
        # have a corresponding stable branch.  This prevents us from trying and
        # failing to sync stable requirements to a library's master branch,
        # when that same library may be listed and capped in global-requirements.txt.
        proj_branch="$(cd $REPODIR/$SHORT_PROJECT && git rev-parse --symbolic-full-name --abbrev-ref HEAD)"
        if [ "$proj_branch" != "$BRANCH" ]; then
            continue
        fi
    fi

    # set up the project synced with the global requirements
    sudo chown -R $USER $REPODIR/$SHORT_PROJECT
    $UPDATE --source $REPODIR/requirements $REPODIR/$SHORT_PROJECT
    pushd $REPODIR/$SHORT_PROJECT
    if ! git diff --exit-code > /dev/null; then
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
