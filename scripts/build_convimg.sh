#!/bin/bash
# Builds convimg v9.3 (BSD-licensed, github.com/mateoconlechuga/convimg) into bin/convimg.
# Needs: git, make, and a C compiler (on Mac: xcode-select --install).
set -e
cd "$(dirname "$0")/.."
[ -x bin/convimg ] && exit 0
tmp="$(mktemp -d)"
git clone --depth 1 --branch v9.3 --recurse-submodules --shallow-submodules \
  https://github.com/mateoconlechuga/convimg.git "$tmp/convimg"
make -C "$tmp/convimg" -j4
cp "$tmp/convimg/bin/convimg" bin/convimg
rm -rf "$tmp"
echo "convimg ready."
