#!/usr/bin/env bash

# Use YYYY-MM-DD format
DATE=`date +%Y-%m-%d`

read -p "Cut the release branch?  (You may lose changes that are not committed or stashed.)  [y/n]  " RESP
if [ "$RESP" != "y" ]; then
    exit 0
fi

echo "Updating origin/master..."
git fetch && git checkout -q origin/master

echo "Creating the release branch..."
BRANCH="rc/$DATE"
git branch | grep -q "$BRANCH$"
if [ $? -eq 0 ]; then
    read -p "Branch $BRANCH already exists.  Delete it? [y/n]  " RESP
    if [ "$RESP" = "y" ]; then
        echo "Deleting $BRANCH"
        git branch -D $BRANCH
    else
        exit 0
    fi
fi

git checkout -b $BRANCH
echo " == Created branch $BRANCH"

echo "Tagging the release branch..."
TAG="release-$DATE"
git tag | grep -q "$TAG"
if [ $? -eq 0 ]; then
    read -p "Tag $TAG already exists.  Delete it? [y/n]  " RESP
    if [ "$RESP" = "y" ]; then
        echo "Deleting $TAG"
        git tag -d $TAG
    else
        exit 0
    fi
fi

git tag -m "release for $DATE" "$TAG"
echo " == Created tag $TAG"

read -p "Push branch $BRANCH and tag $TAG to origin? [y/n]  " RESP
if [ "$RESP" = "y" ]; then
    git push origin $BRANCH && git push origin $TAG
    echo " == Pushed branch $BRANCH and tag $TAG to origin"
fi

echo " == Finished =="
echo "Branch: $BRANCH"
echo "Tag: $TAG"
echo "Commit: `git rev-parse HEAD`"
