#!/bin/bash

PYLINT="`type -p pylint3 2>/dev/null || type -p pylint`"
echo "Using pylint bin at $PYLINT"

# Use * as the default argument to avoid descending into hidden directories like .git
function find_pyfiles() {
    if [ $# -eq 0 ]; then set -- *; fi
    for f in $(find "$@" -type f -iname '*.py'); do
        if [ ! -e "$(dirname $f)/.circuitpython.skip" ]; then
            echo "$f"
        fi
    done
}

find_pyfiles "$@" | xargs "$PYLINT"
