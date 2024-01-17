#!/bin/sh
UNAME_OUT="$(uname -s)"

case "${UNAME_OUT}" in
    Linux*)     ./buildreqs_lin.sh;;
    Darwin*)    ./buildreqs_osx.sh;;
    *)          echo "System $UNAME_OUT not supported by buildreqs.sh.";
                exit 1;;
esac
exit 0;