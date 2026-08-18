#!/bin/sh
# Copy the gates into a repo and wire the hook.
#
#   ./install.sh /path/to/your-repo

set -e
TARGET=${1:?usage: ./install.sh /path/to/your-repo}
HERE=$(cd "$(dirname "$0")" && pwd)

mkdir -p "$TARGET/scripts"
cp "$HERE"/gates/*.py "$TARGET/scripts/"

[ -f "$TARGET/frozen.json" ]     || cp "$HERE/examples/frozen.json" "$TARGET/frozen.json"
[ -f "$TARGET/git_policy.json" ] || cp "$HERE/examples/git_policy.json" "$TARGET/git_policy.json"

cp "$HERE/hooks/pre-commit" "$TARGET/.git/hooks/pre-commit"
chmod +x "$TARGET/.git/hooks/pre-commit"

echo "Installed."
echo "Start with an empty frozen list. Add the first path the day an agent"
echo "edits something you thought was finished."
