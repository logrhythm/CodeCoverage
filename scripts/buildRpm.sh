#!/bin/bash
set -e

PACKAGE=CodeCoverage
VERSION=1.0

# As version number we use the commit number on HEAD 
# we do not bother with other branches for now
GIT_VERSION=`git rev-list --branches HEAD | wc -l`
VERSION="1.$GIT_VERSION"

echo "Building $PACKAGE, type: $BUILD_TYPE, version: $VERSION"

sudo rm -rf ~/rpmbuild
rpmdev-setuptree
cp packaging/$PACKAGE.spec ~/rpmbuild/SPECS
rm -f $PACKAGE-$VERSION.tar.gz
tar czf $PACKAGE-$VERSION.tar.gz ./*
mkdir -p ~/rpmbuild/SOURCES
cp $PACKAGE-$VERSION.tar.gz ~/rpmbuild/SOURCES
cd ~/rpmbuild

rpmbuild -v -bb  --define="version ${VERSION}" --target=x86_64 ~/rpmbuild/SPECS/$PACKAGE.spec
