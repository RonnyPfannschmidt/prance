#!/bin/bash

set -o errexit -o nounset

rev=$(git rev-parse --short HEAD)

cd build/sphinx/html
rm -rf .git

git init
git config user.name "Jens Finkhaeuser (Sphinx Build)"
git config user.email "jens@finkhaeuser.de"

git remote add upstream "https://$GITHUB_TOKEN@github.com/jfinkhaeuser/prance"
git fetch upstream
git reset upstream/gh-pages

touch .

git add -A .
git commit -m "Rebuild pages at ${rev}"
git push -q upstream HEAD:gh-pages
