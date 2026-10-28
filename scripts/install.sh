#!/usr/bin/env bash
#
# vibe.md skill installer
#
# Copies one skill from the vibe.md collection into a project so that your
# AI coding agent can discover it. Skills are found by looking inside the
# skills/ directory; nothing in this script knows about individual skills.
#
#   bash scripts/install.sh --list
#   bash scripts/install.sh --skill <name> --agent <agent> [--project <dir>]
#
# Run with --help for all options. Works with bash 3.2+ on macOS and Linux,
# and on Windows through WSL or Git Bash.

set -euo pipefail

REPO_SLUG="vibe-md/vibe.md"
REPO_URL="https://github.com/${REPO_SLUG}"
DEFAULT_REF="main"
NAME_REGEX='^[a-z0-9]+(-[a-z0-9]+)*$'
REF_REGEX='^[A-Za-z0-9._/-]+$'

# ---------------------------------------------------------------------------
# Supported agents. To add an agent, add its id to SUPPORTED_AGENTS and a case
# to each of the three functions below. Nothing else needs to change.
# ---------------------------------------------------------------------------
SUPPORTED_AGENTS="claude-code codex cursor gemini copilot"

# Project-level directory (relative to the project root) that holds skills.
agent_skills_dir() {
  case "$1" in
    claude-code) echo ".claude/skills" ;;
    codex) echo ".agents/skills" ;;
    cursor) echo ".cursor/skills" ;;
    gemini) echo ".gemini/skills" ;;
    copilot) echo ".github/skills" ;;
    *) return 1 ;;
  esac
}

agent_label() {
  case "$1" in
    claude-code) echo "Claude Code" ;;
    codex) echo "Codex" ;;
    cursor) echo "Cursor" ;;
    gemini) echo "Gemini CLI" ;;
    copilot) echo "GitHub Copilot" ;;
    *) return 1 ;;
  esac
}

# What to do after installing, so the agent notices the new skill.
agent_next_steps() {
  case "$1" in
    claude-code)
      echo "Claude Code detects new skills during a session. If .claude/skills did not exist"
      echo "when the session started, run /reload-skills or restart Claude Code."
      echo "Invoke it with /$2, or let Claude load it when your request matches."
      ;;
    codex)
      echo "Codex usually detects new skills automatically; restart Codex if it does not appear."
      echo "Invoke it with \$$2 or pick it from /skills, or let Codex choose it implicitly."
      ;;
    cursor)
      echo "Cursor discovers skills when it starts; restart Cursor if the skill is not listed."
      echo "Invoke it by typing /$2 in Agent chat, or let the agent apply it when relevant."
      ;;
    gemini)
      echo "Run /skills reload in Gemini CLI (or start a new session) to pick up the skill."
      echo "Gemini asks for your consent the first time it activates a skill."
      ;;
    copilot)
      echo "Copilot in VS Code agent mode and Copilot CLI read skills from your workspace."
      echo "Commit and push .github/skills/$2 to make it available to Copilot cloud agent."
      ;;
  esac
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
DOWNLOAD_DIR=""
STAGE_DIR=""
PREPARE_DIR=""

cleanup() {
  if [ -n "$PREPARE_DIR" ] && [ -d "$PREPARE_DIR" ]; then rm -rf "$PREPARE_DIR"; fi
  if [ -n "$STAGE_DIR" ] && [ -d "$STAGE_DIR" ]; then rm -rf "$STAGE_DIR"; fi
  if [ -n "$DOWNLOAD_DIR" ] && [ -d "$DOWNLOAD_DIR" ]; then rm -rf "$DOWNLOAD_DIR"; fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

die() {
  printf 'error: %s\n' "$1" >&2
  shift
  while [ $# -gt 0 ]; do
    printf '       %s\n' "$1" >&2
    shift
  done
  exit 1
}

usage_error() {
  printf 'error: %s\n' "$1" >&2
  printf "Run 'install.sh --help' for usage.\n" >&2
  exit 2
}

usage() {
  cat <<EOF
vibe.md skill installer

Usage:
  install.sh --list
  install.sh --skill <name> --agent <agent> [options]
  install.sh --group <name> --agent <agent> [options]

Options:
  --skill <name>        One skill to install (see --list).
  --group <name>        Install every skill in a group (see --list).
  --agent <agent>       Agent to install for: ${SUPPORTED_AGENTS// /, }.
  --project <dir>       Project to install into (default: current directory).
  --dry-run             Show what would happen without writing anything.
  --force               Replace an existing, different copy of the skill.
  --list                List the skills available to install.
  --skills-dir <dir>    Use a local skills collection instead of the default.
  --ref <ref>           Branch or tag to download when running remotely
                        (default: ${DEFAULT_REF}).
  -h, --help            Show this help.

Agents and the project directory each one reads:
EOF
  local agent
  for agent in $SUPPORTED_AGENTS; do
    printf '  %-13s %-16s %s/<skill>/\n' "$agent" "$(agent_label "$agent")" "$(agent_skills_dir "$agent")"
  done
  cat <<EOF

When run from a clone of vibe.md, skills come from that clone. When run on its
own (for example piped from curl), the collection is downloaded from
${REPO_URL}.

Shared skills (including the vibe router) are included with every installation.
The installer only copies files. It never runs a skill's scripts, never needs
sudo, and never writes outside the target project.
EOF
}

# Print the description from a SKILL.md frontmatter (best effort, for --list).
read_description() {
  awk '
    NR == 1 { if ($0 !~ /^---[[:space:]]*$/) exit; next }
    /^---[[:space:]]*$/ { exit }
    folding {
      if ($0 ~ /^[[:space:]]+[^[:space:]]/) {
        sub(/^[[:space:]]+/, "")
        text = text (text == "" ? "" : " ") $0
        next
      }
      exit
    }
    /^description:/ {
      value = $0
      sub(/^description:[[:space:]]*/, "", value)
      if (value ~ /^[>|][-+0-9]*[[:space:]]*$/) { folding = 1; next }
      gsub(/^["\047]|["\047][[:space:]]*$/, "", value)
      text = value
      exit
    }
    END { print text }
  ' "$1"
}

is_valid_skill_name() {
  [ "${#1}" -le 64 ] && [[ "$1" =~ $NAME_REGEX ]]
}

# ---------------------------------------------------------------------------
# Locating the skills collection
# ---------------------------------------------------------------------------
download_collection() {
  local ref="$1" url archive top count entry
  command -v curl >/dev/null 2>&1 || die "curl is required to download vibe.md." \
    "Install curl, or clone ${REPO_URL} and run scripts/install.sh from the clone."
  command -v tar >/dev/null 2>&1 || die "tar is required to unpack the vibe.md download."

  url="${VIBE_MD_ARCHIVE_URL:-${REPO_URL}/archive/${ref}.tar.gz}"
  DOWNLOAD_DIR="$(mktemp -d "${TMPDIR:-/tmp}/vibe-md.XXXXXX")" ||
    die "could not create a temporary directory."
  archive="$DOWNLOAD_DIR/vibe-md.tar.gz"

  printf 'Downloading vibe.md (%s)...\n' "$ref" >&2
  curl -fsSL --retry 2 --connect-timeout 15 -o "$archive" "$url" ||
    die "could not download ${url}" \
      "Check your network connection and that the ref '${ref}' exists."
  mkdir "$DOWNLOAD_DIR/src"
  tar -xzf "$archive" -C "$DOWNLOAD_DIR/src" 2>/dev/null ||
    die "the downloaded archive could not be unpacked. Please try again."

  count=0
  for entry in "$DOWNLOAD_DIR/src"/*; do
    [ -e "$entry" ] || continue
    count=$((count + 1))
    top="$entry"
  done
  if [ "$count" -ne 1 ] || [ ! -d "$top/skills" ]; then
    die "the downloaded archive does not look like the vibe.md repository."
  fi
  SKILLS_DIR="$top/skills"
}

resolve_skills_dir() {
  local script_path script_dir
  if [ -n "$SKILLS_DIR" ]; then
    [ -d "$SKILLS_DIR" ] || die "skills directory not found: $SKILLS_DIR"
    SKILLS_DIR="$(cd "$SKILLS_DIR" && pwd -P)"
    return
  fi
  script_path="${BASH_SOURCE[0]:-}"
  if [ -n "$script_path" ] && [ -f "$script_path" ]; then
    script_dir="$(cd "$(dirname "$script_path")" && pwd -P)"
    if [ -d "$script_dir/../skills" ]; then
      SKILLS_DIR="$(cd "$script_dir/../skills" && pwd -P)"
      return
    fi
  fi
  download_collection "$REF"
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
# Standalone skills and one level of groups share a flat installed namespace.
# _shared contains common skills installed with every selection.
discover_skills() {
  SOURCES=()
  local dir child source name
  for dir in "$SKILLS_DIR"/*; do
    [ -d "$dir" ] || continue
    [ ! -L "$dir" ] || die "symbolic links are not allowed in the skills collection: $dir"
    if [ -f "$dir/SKILL.md" ]; then
      SOURCES+=("$dir")
    else
      for child in "$dir"/*; do
        [ -f "$child/SKILL.md" ] || continue
        [ ! -L "$child" ] || die "symbolic links are not allowed in the skills collection: $child"
        SOURCES+=("$child")
      done
    fi
  done
  local names=" "
  for source in "${SOURCES[@]:-}"; do
    [ -n "$source" ] || continue
    name="$(basename "$source")"
    is_valid_skill_name "$name" || die "invalid skill name '$name' in the collection."
    case "$names" in
      *" $name "*) die "duplicate skill name '$name'. Installed skill names must be unique across groups." ;;
    esac
    names="$names$name "
  done
}

list_skills() {
  local source name description group count=0
  for source in "${SOURCES[@]:-}"; do
    [ -n "$source" ] || continue
    name="$(basename "$source")"
    group="$(basename "$(dirname "$source")")"
    [ "$(dirname "$source")" != "$SKILLS_DIR" ] || group="standalone"
    [ "$group" != "_shared" ] || group="shared"
    if [ "$count" -eq 0 ]; then printf 'Available skills (group):\n\n'; fi
    count=$((count + 1))
    description="$(read_description "$source/SKILL.md")"
    if [ "${#description}" -gt 100 ]; then description="${description:0:97}..."; fi
    printf '  %-28s [%-10s] %s\n' "$name" "$group" "$description"
  done

  if [ "$count" -eq 0 ]; then
    echo "No skills are available yet."
    echo "The collection is ready for its first contributions:"
    echo "${REPO_URL}/blob/main/CONTRIBUTING.md"
  else
    printf '\nInstall with --skill <name> or --group <group>, plus --agent <agent>.\n'
    echo "Shared skills are included automatically."
  fi
}

select_skills() {
  SELECTED=()
  local source
  for source in "${SOURCES[@]:-}"; do
    [ -n "$source" ] || continue
    if { [ -n "$SKILL" ] && [ "$(basename "$source")" = "$SKILL" ]; } ||
       { [ -n "$GROUP" ] && [ "$(dirname "$source")" = "$SKILLS_DIR/$GROUP" ]; }; then
      SELECTED+=("$source")
    fi
  done
  if [ "${#SELECTED[@]}" -eq 0 ]; then
    if [ -n "$GROUP" ]; then
      die "group '$GROUP' was not found." "Run 'install.sh --list' to see the available groups."
    fi
    die "skill '$SKILL' was not found." "Run 'install.sh --list' to see the available skills."
  fi
  for source in "${SOURCES[@]:-}"; do
    [ -n "$source" ] || continue
    if [ "$(dirname "$source")" = "$SKILLS_DIR/_shared" ] &&
       [ "$(basename "$source")" != "$SKILL" ]; then
      SELECTED+=("$source")
    fi
  done
}

# Keep skills directly discoverable while installing group documents only once.
# Source links ../FILE become ../<group>/FILE in the flat installed layout.
prepare_selection() {
  local source name group_dir group file candidate original
  local prepared=()
  ENTRY_SKILL="$(basename "${SELECTED[0]}")"
  PREPARE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/vibe-md-prepare.XXXXXX")" ||
    die "could not create a temporary directory for the installation layout."
  for source in "${SELECTED[@]}"; do
    name="$(basename "$source")"
    group_dir="$(dirname "$source")"
    group="$(basename "$group_dir")"
    if [ -n "$(find "$source" -type l 2>/dev/null | head -n 1)" ]; then
      die "skill '$name' contains symbolic links and cannot be installed safely."
    fi
    cp -R "$source" "$PREPARE_DIR/$name" || die "could not prepare skill '$name'. Nothing was installed."
    prepared+=("$PREPARE_DIR/$name")
    if [ "$group_dir" = "$SKILLS_DIR/_shared" ]; then
      ENTRY_SKILL="$name"
    elif [ "$group_dir" != "$SKILLS_DIR" ]; then
      is_valid_skill_name "$group" || die "invalid group name '$group'."
      if [ ! -d "$PREPARE_DIR/$group" ] || [ -f "$PREPARE_DIR/$group/SKILL.md" ]; then
        for file in "$group_dir"/*.md "$group_dir/LICENSE"; do
          [ ! -L "$file" ] || die "group '$group' contains symbolic links and cannot be installed safely."
          [ -f "$file" ] || continue
          if [ -f "$PREPARE_DIR/$group/SKILL.md" ]; then
            die "group resources '$group' conflict with a skill of the same name."
          fi
          if [ ! -d "$PREPARE_DIR/$group" ]; then
            for candidate in "${SOURCES[@]}"; do
              [ "$(basename "$candidate")" != "$group" ] ||
                die "group resources '$group' conflict with a skill of the same name."
            done
            mkdir "$PREPARE_DIR/$group"
          fi
          cp "$file" "$PREPARE_DIR/$group/" || die "could not prepare group resources for '$group'."
        done
      fi
      original="$PREPARE_DIR/$name/SKILL.md"
      sed -E "s|(\]\([[:blank:]]*<?)\.\./|\1../$group/|g" "$original" > "$PREPARE_DIR/skill.tmp" ||
        die "could not resolve resource links for '$name'."
      cp "$PREPARE_DIR/skill.tmp" "$original"
    fi
  done
  rm -f "$PREPARE_DIR/skill.tmp"
  # A group is selected at most once; include its common documents as one unit.
  for source in "${SELECTED[@]}"; do
    group_dir="$(dirname "$source")"
    group="$(basename "$group_dir")"
    if [ "$group_dir" != "$SKILLS_DIR" ] && [ "$group_dir" != "$SKILLS_DIR/_shared" ] &&
       [ -d "$PREPARE_DIR/$group" ]; then
      prepared+=("$PREPARE_DIR/$group")
      break
    fi
  done
  SELECTED=("${prepared[@]}")
}

# Fail if any existing part of the destination resolves outside the project,
# for example because .claude is a symlink to another directory.
check_destination_inside_project() {
  local project="$1" rest="$2/" current="$1" part real
  while [ -n "$rest" ]; do
    part="${rest%%/*}"
    rest="${rest#*/}"
    current="$current/$part"
    if [ -L "$current" ] || [ -e "$current" ]; then
      [ -d "$current" ] || die "'$current' exists but is not a directory." \
        "Move it out of the way and run the installer again."
      real="$(cd "$current" && pwd -P)"
      case "$real/" in
        "$project"/*) ;;
        *) die "'$current' resolves to '$real', which is outside the project." \
          "The installer only writes inside the target project." ;;
      esac
    else
      break
    fi
  done
}

# Restore every destination already changed if a later move fails.
rollback_install() {
  local skills_root="$1" name failed=0 recovery="$STAGE_DIR"
  for name in "${CHANGED[@]:-}"; do
    [ -n "$name" ] || continue
    if ! rm -rf -- "${skills_root:?}/${name:?}"; then
      failed=1
      continue
    fi
    if [ -e "$STAGE_DIR/previous/$name" ] || [ -L "$STAGE_DIR/previous/$name" ]; then
      mv "$STAGE_DIR/previous/$name" "$skills_root/$name" || failed=1
    fi
  done
  if [ "$failed" = "1" ]; then
    STAGE_DIR=""  # Preserve backups if automatic recovery could not finish.
    die "installation failed and recovery is incomplete. Backups are preserved in '$recovery'."
  fi
  die "installation failed. Previous copies were restored; no new skills remain installed."
}

install_skills() {
  local source name label rel project skills_root dest action parent entry i
  local actions=() changes=0
  CHANGED=()
  label="$(agent_label "$AGENT")"
  rel="$(agent_skills_dir "$AGENT")"
  [ -d "$PROJECT" ] || die "project directory not found: $PROJECT"
  project="$(cd "$PROJECT" && pwd -P)"
  skills_root="$project/$rel"
  check_destination_inside_project "$project" "$rel"

  # Inspect every selected source and destination before creating anything.
  for source in "${SELECTED[@]}"; do
    name="$(basename "$source")"
    if [ -n "$(find "$source" -type l 2>/dev/null | head -n 1)" ]; then
      die "skill '$name' contains symbolic links and cannot be installed safely."
    fi
    dest="$skills_root/$name"
    action="install"
    if [ -L "$dest" ] || [ -e "$dest" ]; then
      if [ -d "$dest" ] && [ ! -L "$dest" ] && diff -r -q "$source" "$dest" >/dev/null 2>&1; then
        action="skip"
      elif [ "$FORCE" = "1" ]; then
        action="replace"
      else
        die "'$dest' already exists and differs from the vibe.md version of '$name'." \
          "Nothing was changed. Re-run with --force to replace it, or move it away first."
      fi
    fi
    actions+=("$action")
    if [ "$action" != "skip" ]; then changes=$((changes + 1)); fi
  done

  if [ "$DRY_RUN" = "1" ]; then
    echo "Dry run: nothing will be written."
    for ((i=0; i<${#SELECTED[@]}; i++)); do
      source="${SELECTED[$i]}"
      name="$(basename "$source")"
      printf '  Directory: %s\n  Agent: %s\n  Destination: %s\n  Action: %s\n' \
        "$name" "$label" "$skills_root/$name" "${actions[$i]}"
      (cd "$source" && find . -type f | sed 's|^\./|    |' | LC_ALL=C sort)
    done
    return 0
  fi

  if [ "$changes" -gt 0 ]; then
    mkdir -p "$skills_root" || die "could not create '$skills_root'."
    # Stage the whole selection outside the discovery directory before changing it.
    parent="$(dirname "$skills_root")"
    STAGE_DIR="$(mktemp -d "$parent/.vibe-md-install.XXXXXX")" ||
      die "could not create a temporary directory in '$parent'."
    mkdir "$STAGE_DIR/new" "$STAGE_DIR/previous"
    for ((i=0; i<${#SELECTED[@]}; i++)); do
      [ "${actions[$i]}" != "skip" ] || continue
      source="${SELECTED[$i]}"
      name="$(basename "$source")"
      cp -R "$source" "$STAGE_DIR/new/$name" ||
        die "copying '$name' failed. Nothing was installed."
      diff -r -q "$source" "$STAGE_DIR/new/$name" >/dev/null 2>&1 ||
        die "the copied files do not match the source. Nothing was installed."
    done
    for ((i=0; i<${#SELECTED[@]}; i++)); do
      [ "${actions[$i]}" != "skip" ] || continue
      name="$(basename "${SELECTED[$i]}")"
      dest="$skills_root/$name"
      if [ "${actions[$i]}" = "replace" ]; then
        mv "$dest" "$STAGE_DIR/previous/$name" || rollback_install "$skills_root"
      fi
      CHANGED+=("$name")
      mv "$STAGE_DIR/new/$name" "$dest" || rollback_install "$skills_root"
    done
  fi

  entry="$ENTRY_SKILL"
  for ((i=0; i<${#SELECTED[@]}; i++)); do
    source="${SELECTED[$i]}"
    name="$(basename "$source")"
    case "${actions[$i]}" in
      skip) echo "'$name' is already installed for $label and up to date: $skills_root/$name" ;;
      replace) echo "Replaced '$name' for $label: $skills_root/$name" ;;
      install) echo "Installed '$name' for $label: $skills_root/$name" ;;
    esac
  done
  echo
  agent_next_steps "$AGENT" "$entry"
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
main() {
  SKILL=""
  GROUP=""
  AGENT=""
  PROJECT=""
  SKILLS_DIR=""
  REF="$DEFAULT_REF"
  DRY_RUN=0
  FORCE=0
  local list=0 opt value

  while [ $# -gt 0 ]; do
    opt="$1"
    value=""
    case "$opt" in
      --*=*)
        value="${opt#*=}"
        opt="${opt%%=*}"
        ;;
    esac
    case "$opt" in
      --skill | --group | --agent | --project | --skills-dir | --ref)
        if [ -z "$value" ]; then
          [ $# -ge 2 ] || usage_error "$opt needs a value."
          value="$2"
          shift
        fi
        [ -n "$value" ] || usage_error "$opt needs a value."
        case "$opt" in
          --skill) SKILL="$value" ;;
          --group) GROUP="$value" ;;
          --agent) AGENT="$value" ;;
          --project) PROJECT="$value" ;;
          --skills-dir) SKILLS_DIR="$value" ;;
          --ref) REF="$value" ;;
        esac
        ;;
      --list) list=1 ;;
      --dry-run) DRY_RUN=1 ;;
      --force) FORCE=1 ;;
      -h | --help)
        usage
        exit 0
        ;;
      *) usage_error "unknown option: $1" ;;
    esac
    shift
  done

  if ! [[ "$REF" =~ $REF_REGEX ]] || [[ "$REF" == *..* ]]; then
    usage_error "invalid --ref: $REF"
  fi

  if [ "$list" = "1" ]; then
    resolve_skills_dir
    discover_skills
    list_skills
    exit 0
  fi

  [ -z "$SKILL" ] || [ -z "$GROUP" ] || usage_error "choose --skill or --group, not both."
  [ -n "$SKILL$GROUP" ] || usage_error "missing --skill or --group. Use --list to see the available skills."
  [ -n "$AGENT" ] || usage_error "missing --agent. Choose one of: ${SUPPORTED_AGENTS// /, }."
  if [ -n "$SKILL" ]; then
    is_valid_skill_name "$SKILL" || usage_error "invalid skill name '$SKILL'. Use lowercase letters, digits and hyphens."
  else
    is_valid_skill_name "$GROUP" || usage_error "invalid group name '$GROUP'. Use lowercase letters, digits and hyphens."
  fi
  agent_skills_dir "$AGENT" >/dev/null ||
    usage_error "unknown agent '$AGENT'. Choose one of: ${SUPPORTED_AGENTS// /, }."
  PROJECT="${PROJECT:-$PWD}"

  resolve_skills_dir
  discover_skills
  select_skills
  prepare_selection
  install_skills
}

main "$@"
