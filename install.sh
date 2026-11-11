#!/bin/bash
# Install shell integration from this checkout. No sudo or Cisco changes.

set -euo pipefail

BEGIN_MARKER='# >>> Cisco Secure Client toggle >>>'
END_MARKER='# <<< Cisco Secure Client toggle <<<'
MODE=install
DRY_RUN=0
RC_FILE=''

usage() {
    cat <<'HELP'
Usage: ./install.sh [--rc-file PATH] [--dry-run] [--uninstall]

Installs shell functions from this checkout into your shell startup file.
Default: $ZDOTDIR/.zshrc or ~/.zshrc for Zsh; ~/.bash_profile for Bash.
Use --rc-file ~/.bashrc for a Bash shell that reads that file instead.

--rc-file PATH  Select a startup file explicitly (Bash or Zsh).
--dry-run       Show the action without writing any files.
--uninstall     Remove the managed startup block; keep Cisco and the checkout.
HELP
}

fail() { printf 'install.sh: %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --rc-file)
            [[ $# -ge 2 && -n "$2" ]] || fail '--rc-file requires a path.'
            RC_FILE=$2
            shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        --uninstall) MODE=uninstall; shift ;;
        --help|-h) usage; exit 0 ;;
        *) fail "Unknown argument: $1 (see --help)." ;;
    esac
done

[[ $EUID != 0 ]] || fail 'Run this installer as your desktop user, without sudo.'
REPO_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
[[ -f "$REPO_DIR/cisco.aliases" && -f "$REPO_DIR/cisco-client" ]] || fail 'Keep install.sh in the repository.'

if [[ -z "$RC_FILE" ]]; then
    INSTALL_SHELL=${SHELL:-}
    case "${INSTALL_SHELL##*/}" in
        zsh) RC_FILE="${ZDOTDIR:-$HOME}/.zshrc" ;;
        bash) RC_FILE="$HOME/.bash_profile" ;;
        *) fail 'Set --rc-file to a Bash or Zsh startup file.' ;;
    esac
fi

# Follow file symlinks so replacing the startup file preserves the user's link.
[[ "$RC_FILE" == /* ]] || RC_FILE="$PWD/$RC_FILE"
RC_TARGET=$RC_FILE
LINK_COUNT=0
while [[ -L "$RC_TARGET" ]]; do
    LINK_COUNT=$((LINK_COUNT + 1))
    [[ $LINK_COUNT -le 40 ]] || fail 'Startup-file symlink loop.'
    LINK_TARGET=$(/usr/bin/readlink "$RC_TARGET")
    if [[ "$LINK_TARGET" == /* ]]; then
        RC_TARGET=$LINK_TARGET
    else
        RC_TARGET="$(dirname -- "$RC_TARGET")/$LINK_TARGET"
    fi
done
[[ ! -e "$RC_TARGET" || -f "$RC_TARGET" ]] || fail 'Startup path must be a regular file.'

if [[ $DRY_RUN == 1 ]]; then
    printf 'Would %s shell integration in: %s\n' "$MODE" "$RC_FILE"
    printf 'Startup file target: %s\n' "$RC_TARGET"
    printf 'Checkout: %s\n' "$REPO_DIR"
    exit 0
fi

if [[ $MODE == uninstall && ! -e "$RC_TARGET" ]]; then
    printf 'No shell integration found in: %s\n' "$RC_FILE"
    exit 0
fi

mkdir -p -- "$(dirname -- "$RC_TARGET")"
SNAPSHOT=$(/usr/bin/mktemp "${RC_TARGET}.cisco-toggle-original.XXXXXX")
UPDATED=''
cleanup() {
    /bin/rm -f -- "$SNAPSHOT"
    [[ -z "$UPDATED" ]] || /bin/rm -f -- "$UPDATED"
    return 0
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

EXISTED=0
if [[ -e "$RC_TARGET" ]]; then
    EXISTED=1
    /bin/cp -p -- "$RC_TARGET" "$SNAPSHOT"
fi
UPDATED=$(/usr/bin/mktemp "${RC_TARGET}.cisco-toggle-updated.XXXXXX")
/bin/cp -p -- "$SNAPSHOT" "$UPDATED"

# Refuse malformed or duplicated markers rather than deleting ambiguous content.
if ! /usr/bin/awk -v begin="$BEGIN_MARKER" -v end="$END_MARKER" '
    $0 == begin { if (inside || blocks) exit 2; inside=1; blocks++; next }
    $0 == end   { if (!inside) exit 2; inside=0; next }
    !inside     { print }
    END         { if (inside) exit 2 }
' "$SNAPSHOT" > "$UPDATED"; then
    fail 'Startup markers are malformed or duplicated; file was not changed.'
fi

if [[ $MODE == uninstall ]] && ! /usr/bin/grep -Fqx -- "$BEGIN_MARKER" "$SNAPSHOT"; then
    printf 'No shell integration found in: %s\n' "$RC_FILE"
    exit 0
fi

if [[ $MODE == install ]]; then
    printf -v SOURCE_PATH '%q' "$REPO_DIR/cisco.aliases"
    {
        printf '%s\n' "$BEGIN_MARKER"
        printf 'if [[ -r %s ]]; then\n' "$SOURCE_PATH"
        printf '    source %s\n' "$SOURCE_PATH"
        printf 'fi\n%s\n' "$END_MARKER"
    } >> "$UPDATED"
fi

if /usr/bin/cmp -s -- "$SNAPSHOT" "$UPDATED"; then
    printf 'Shell integration already up to date: %s\n' "$RC_FILE"
    exit 0
fi

# Check for a concurrent edit before replacing the file.
if [[ $EXISTED == 1 ]]; then
    /usr/bin/cmp -s -- "$SNAPSHOT" "$RC_TARGET" || fail 'Startup file changed during installation; retry.'
    BACKUP=$(/usr/bin/mktemp "${RC_TARGET}.cisco-toggle-backup.XXXXXX")
    /bin/cp -p -- "$SNAPSHOT" "$BACKUP"
    printf 'Backup: %s\n' "$BACKUP"
else
    [[ ! -e "$RC_TARGET" && ! -L "$RC_TARGET" ]] || fail 'Startup file appeared during installation; retry.'
fi
/bin/mv -f -- "$UPDATED" "$RC_TARGET"
UPDATED=''

if [[ $MODE == install ]]; then
    printf 'Installed shell integration in: %s\n' "$RC_FILE"
    printf 'Open a new terminal, or run:\n  source %s\n' "$SOURCE_PATH"
    printf 'Keep this checkout at its current path; rerun install.sh after moving it.\n'
else
    printf 'Removed shell integration from: %s\n' "$RC_FILE"
    printf 'Open a new terminal to drop the functions. Cisco service state was not changed.\n'
fi
