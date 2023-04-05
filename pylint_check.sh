#!/bin/bash

SOURCE_LOCATION="$(dirname "$0")"
PYLINT="`type -p pylint-learn 2>/dev/null || type -p pylint3 2>/dev/null || type -p pylint`"
echo "Using pylint bin at $PYLINT"
PYLINTRC=$SOURCE_LOCATION/.pylintrc

# Use * as the default argument to avoid descending into hidden directories like .git
# don't use advanced functions of find without verifying they are present in
# the archaic default version on macos
function find_pyfiles() {
    if [ $# -eq 0 ]; then set -- *; fi
    for f in $(find "$@" -type f -iname '*.py'); do
        if [ ! -e "$(dirname $f)/.circuitpython.skip" ]; then
            echo "$f"
        fi
    done
}

find_pyfiles "$@" | xargs "$PYLINT" --rcfile "$PYLINTRC"
