#!/usr/bin/env bash
set -euo pipefail

# Installs these skills so Claude Code can find them.
#
# Claude Code discovers skills at exactly ONE level below a skills directory:
#   ~/.claude/skills/<skill-name>/SKILL.md      (personal, all your projects)
#   <repo>/.claude/skills/<skill-name>/SKILL.md (one project only)
#
# skills/ holds the starter set and is what you get by default.
# extras/ holds the rest, grouped into folders for browsing. Nothing in
# extras/ installs unless you name it (or pass --all).
#
# Naming a skill also installs whatever that skill calls, because a skill
# whose dependencies are missing fails at the point you try to use it.
#
# Usage:
#   ./install.sh                          the starter set, for all your projects
#   ./install.sh --all                    everything, starter set plus extras
#   ./install.sh code-review wayfinder    the named skills, plus what they call
#   ./install.sh --project /path/to/repo  install into one project instead
#   ./install.sh --list                   show what is available, install nothing

REPO="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.claude/skills"
WANTED=()
PULLED=()
ALL=no

find_skills() {  # find_skills <dir> -> null-separated SKILL.md paths
  [ -d "$1" ] && find "$1" -name SKILL.md -print0 || true
}

names_in() {     # names_in <dir> -> one skill name per line, sorted
  find_skills "$1" | while IFS= read -r -d '' f; do basename "$(dirname "$f")"; done | sort
}

dir_of() {       # dir_of <name> -> the skill's folder, or non-zero if unknown
  local d
  for d in "$REPO/skills/$1" "$REPO"/extras/*/"$1"; do
    if [ -f "$d/SKILL.md" ]; then printf '%s\n' "$d"; return 0; fi
  done
  return 1
}

deps_of() {      # deps_of <dir> -> skills this one calls, one per line
  grep -ho 'Skill tool[^.]*' "$1"/*.md 2>/dev/null \
    | grep -o '"[a-z][a-z0-9-]*"' | tr -d '"' | sort -u
}

in_wanted() {    # in_wanted <name>
  local w
  for w in ${WANTED[@]+"${WANTED[@]}"}; do [ "$w" = "$1" ] && return 0; done
  return 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    --all)     ALL=yes; shift ;;
    --project) DEST="${2:?--project needs a path}/.claude/skills"; shift 2 ;;
    --list)
      echo "Starter set (installed by default):"
      names_in "$REPO/skills" | sed 's/^/  /'
      echo
      echo "Extras (install by name, or with --all):"
      names_in "$REPO/extras" | sed 's/^/  /'
      exit 0 ;;
    -h|--help) sed -n '4,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)        echo "unknown option: $1" >&2; exit 1 ;;
    *)         WANTED+=("$1"); shift ;;
  esac
done

# A name that matches nothing is almost always a typo, and silence would hide it.
for w in ${WANTED[@]+"${WANTED[@]}"}; do
  dir_of "$w" >/dev/null || echo "No skill named '$w'. Run ./install.sh --list to see the names." >&2
done

# Pull in whatever the named skills call, transitively. Without this,
# `./install.sh wayfinder` installs a skill that calls two you do not have.
changed=yes
while [ "$changed" = yes ]; do
  changed=no
  for name in ${WANTED[@]+"${WANTED[@]}"}; do
    src="$(dir_of "$name")" || continue
    for dep in $(deps_of "$src"); do
      if ! in_wanted "$dep" && dir_of "$dep" >/dev/null; then
        WANTED+=("$dep"); PULLED+=("$dep"); changed=yes
      fi
    done
  done
done

# Default installs the starter set only. Naming skills, or --all, opens up extras.
SEARCH=("$REPO/skills")
if [ "$ALL" = yes ] || [ ${#WANTED[@]} -gt 0 ]; then
  SEARCH+=("$REPO/extras")
fi

mkdir -p "$DEST"

installed=0
replaced=()

for dir in "${SEARCH[@]}"; do
  while IFS= read -r -d '' skill_md; do
    src="$(dirname "$skill_md")"
    name="$(basename "$src")"

    if [ ${#WANTED[@]} -gt 0 ] && ! in_wanted "$name"; then
      continue
    fi

    # Anything already here is a different copy of this skill, not ours.
    if [ -e "$DEST/$name" ]; then
      if ! diff -rq "$src" "$DEST/$name" >/dev/null 2>&1; then
        replaced+=("$name")
      fi
      rm -rf "$DEST/$name"
    fi

    cp -r "$src" "$DEST/$name"
    installed=$((installed+1))
  done < <(find_skills "$dir")
done

echo "Installed $installed skill(s) into $DEST"

if [ ${#PULLED[@]} -gt 0 ]; then
  echo
  echo "Also installed, because the skills you named call them:"
  printf '  %s\n' "${PULLED[@]}" | sort -u
fi

if [ ${#replaced[@]} -gt 0 ]; then
  echo
  echo "Replaced a different skill of the same name:"
  printf '  %s\n' "${replaced[@]}"
fi

cat <<'NOTE'

Next: start a new Claude Code session, then type /grill-me
If it autocompletes, the install worked.

Add more later with ./install.sh <name>, or see them all with --list.
NOTE

# Only worth saying when it actually applies.
if [ -e "$DEST/code-review" ]; then
  echo
  echo "Heads-up: code-review overrides Claude Code's built-in /code-review."
  echo "Delete $DEST/code-review to get the built-in back."
fi
