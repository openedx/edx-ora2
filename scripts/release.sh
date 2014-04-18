#!/usr/bin/env bash

###################################################################
#
#   Create a new tag for a release of edx-ora2 and
#   push it to the remote.
#
#   Release tags have a uniform naming scheme that includes
#   the current date.
#
#   Usage:
#
#       ./release.sh COMMIT
#
#   If no commit is specified, use origin/master.
#
#   Examples:
#
#       Create a release tag for origin/master:
#       ./release.sh
#
#       Create a release tag for a specific commit:
#       ./release.sh f921f3ee4bc07edf2f1b492f94350cb1dd844100
#
#       Create a release tag without user input:
#       yes | ./release.sh
#
###################################################################

# Use YYYY-MM-DD-HH:MM format (UTC)
DATE=`date -u +%Y-%m-%dT%H.%M`

read -p "Create the release candidate?  (You may lose changes that are not committed or stashed.)  [y/n]  " RESP
if [ "$RESP" != "y" ]; then
    exit 0
fi

echo "Updating origin/master..."
git fetch

# If no commit is specified, use origin/master
if [ -z "$1" ]; then
    git checkout -q origin/master || exit 1
else
    git checkout -q $1 || exit 1
fi

echo "Tagging the release candidate..."
TAG="release-$DATE"
git tag | grep -q "$TAG"
if [ $? -eq 0 ]; then
    read -p "Tag $TAG already exists.  Delete it and create a new one? [y/n]  " RESP
    if [ "$RESP" = "y" ]; then
        echo "Deleting $TAG"
        git tag -d $TAG
    else
        exit 0
    fi
fi

git tag -m "release for $DATE" "$TAG"
echo " == Created tag $TAG"

read -p "Push tag $TAG to origin? [y/n]  " RESP
if [ "$RESP" = "y" ]; then
    git push origin $TAG
    echo " == Pushed tag $TAG to origin"
fi

echo " == Finished =="
echo "Tag: $TAG"
echo "Commit: `git rev-parse HEAD`"
