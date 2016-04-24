#!/bin/bash -xe

pybabel extract \
    --add-comments Translators: \
    --msgid-bugs-address="https://bugs.launchpad.net/openstack-i18n/" \
    --project=requirements --version=1 \
    -k "_C:1c,2" -k "_P:1,2" \
    -o babel-test/test.pot  babel-test

pybabel extract --no-default-keywords \
    --add-comments Translators: \
    --msgid-bugs-address="https://bugs.launchpad.net/openstack-i18n/" \
    --project=requirements --version=1 \
    -k "_LE" \
    -o babel-test/test-log-error.pot  babel-test

# Entries to ignore
REGEX="(POT-Creation-Date|Generated-By|Copyright (C) |FIRST AUTHOR <EMAIL@ADDRESS>)"

function diff_files {
    local expected=$1
    local testfile=$2
    local extra

    # grep fails if there's no content - which is fine here.
    set +e
    extra=$(diff -u0 $expected $testfile | \
        egrep -v "$REGEX" |egrep -c "^([-+][^-+#])")
    set -e

    if [ $extra -ne 0 ] ; then
        echo "Generation of test.pot failed."
        echo "Extra content is:"
        diff -u0 $expected $testfile | egrep -v "$REGEX"
        exit 1
    fi
}

diff_files babel-test/expected.pot babel-test/test.pot
diff_files babel-test/expected-log-error.pot babel-test/test-log-error.pot

echo "Everything fine"
