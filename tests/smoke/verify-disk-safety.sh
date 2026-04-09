#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
UDEV_RULE="${ROOT_DIR}/config/live-build/includes.chroot/etc/udev/rules.d/61-nmos-ignore-internal-disks.rules"
MEDIA_CONF="${ROOT_DIR}/config/live-build/includes.chroot/etc/dconf/db/local.d/00-media-handling"

grep -q 'ENV{UDISKS_IGNORE}="1"' "${UDEV_RULE}" || {
    echo "internal-disk UDisks ignore rule is missing." >&2
    exit 1
}

grep -q '^automount=false$' "${MEDIA_CONF}" || {
    echo "GNOME automount disable flag is missing." >&2
    exit 1
}

grep -q '^automount-open=false$' "${MEDIA_CONF}" || {
    echo "GNOME automount-open disable flag is missing." >&2
    exit 1
}

echo "Disk safety defaults look configured."

