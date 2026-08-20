#!/usr/bin/env bash
set -euo pipefail

# Installs these skills so Claude Code can find them.
#
# Claude Code discovers skills at exactly ONE level below a skills directory:
#   ~/.claude/skills/<skill-name>/SKILL.md      (personal, all your projects)
#   <repo>/.claude/skills/<skill-name>/SKILL.md (one project only)
# This repo groups skills into engineering/ and productivity/ for navigation,
# so a plain `cp -r skills/* ...` would install two folders named after the
# buckets and nothing would load. This script flattens them.
#
# Usage:
#   ./install.sh                          install everything, for all projects
#   ./install.sh grill-me wait-what       install only the named skills
#   ./install.sh --project /path/to/repo  install into one project instead
#   ./install.sh --list                   show what is available, install nothing

REPO="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.claude/skills"
WANTED=()

while [ $# -gt 0 ]; do
  case "$1" in
    --project) DEST="${2:?--project needs a path}/.claude/skills"; shift 2 ;;
    --list)    find "$REPO/skills" -name SKILL.md -print0 | while IFS= read -r -d '' f; do basename "$(dirname "$f")"; done | sort; exit 0 ;;
    -h|--help) sed -n '3,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)        echo "unknown option: $1" >&2; exit 1 ;;
    *)         WANTED+=("$1"); shift ;;
  esac
done

mkdir -p "$DEST"

installed=0
skipped=0
shadowed=()

while IFS= read -r -d '' skill_md; do
  src="$(dirname "$skill_md")"
  name="$(basename "$src")"

  if [ ${#WANTED[@]} -gt 0 ]; then
    match=no
    for w in "${WANTED[@]}"; do [ "$w" = "$name" ] && match=yes; done
    [ "$match" = no ] && { skipped=$((skipped+1)); continue; }
  fi

  # An existing directory here is a different copy of this skill, not ours.
  if [ -e "$DEST/$name" ] && [ ! -L "$DEST/$name" ]; then
    if ! diff -rq "$src" "$DEST/$name" >/dev/null 2>&1; then
      shadowed+=("$name")
    fi
    rm -rf "$DEST/$name"
  fi

  cp -r "$src" "$DEST/$name"
  installed=$((installed+1))
done < <(find "$REPO/skills" -name SKILL.md -print0)

echo "Installed $installed skill(s) into $DEST"
[ "$skipped" -gt 0 ] && echo "Skipped $skipped not named on the command line."

if [ ${#shadowed[@]} -gt 0 ]; then
  echo
  echo "Replaced an existing skill of the same name:"
  printf '  %s\n' "${shadowed[@]}"
fi

cat <<'NOTE'

Note: a skill installed here overrides a built-in Claude Code command of the
same name. This set includes `code-review`, which shadows the bundled
/code-review. Remove ~/.claude/skills/code-review to get the built-in back.

Next: start a new Claude Code session, then type /grill-me
If it autocompletes, the install worked.
NOTE
