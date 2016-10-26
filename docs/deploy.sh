#!/bin/bash

set -o errexit -o nounset

rev=$(git rev-parse --short HEAD)

cd build/sphinx/html
rm -rf .git

git init
git config user.name "Jens Finkhaeuser (Sphinx Build)"
git config user.email "jens@finkhaeuser.de"

touch .

git add -A .
git commit -m "Rebuild pages at ${rev}"
git push --force --quiet "https://${GITHUB_TOKEN}@github.com/${TRAVIS_REPO_SLUG}.git" master:gh-pages
