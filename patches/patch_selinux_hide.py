#!/usr/bin/env python3
"""Anchor-based fix for BakaSU's kernel/feature/selinux_hide.c.

BakaSU already has native support for SUSFS static SELinux hooks:
kernel/tools/susfs_compat.mk defines KSU_COMPAT_HAS_SUSFS_FEATURE_SELINUX_HIDE
when security/selinux/hooks.c contains ksu_selinux_hide_running (which the
SUSFS kernel patch injects).  With that macro set, ksu_selinux_hide_enable()
skips all runtime ksu_patch_text() calls and returns 0 -- no fixmap writes,
so EL2-protected devices (Xiaomi XRING O1) never fault/reboot.

The one remaining defect is a state-ordering bug in
selinux_hide_feature_set(): ksu_selinux_hide_enabled is assigned BEFORE
ksu_selinux_hide_enable() runs.  If enable() ever fails, the manager shows
"on" while ksu_selinux_hide_running stays false and every SUSFS static hook
is gated off.  Publish the flag only after enable() succeeds.

This script uses structural anchors (not line-number context) because CI
pulls BakaSU's rolling main branch.  Every replacement asserts exactly one
match, so an incompatible upstream layout fails the build loudly instead
of silently producing a broken kernel.

Usage: python3 patches/patch_selinux_hide.py <path/to/selinux_hide.c>
"""
import pathlib
import sys

RULES = [
    (
        "feature_set: do not publish flag before enable()",
        """    mutex_lock(&selinux_hide_mutex);
    ksu_selinux_hide_enabled = enable;
    if (enable) {""",
        """    mutex_lock(&selinux_hide_mutex);
    if (enable) {""",
    ),
    (
        "feature_set: publish enabled after enable() succeeded",
        """            if (!ret) {
                ksu_selinux_hide_running = true;
            }
        }
    } else {""",
        """            if (!ret) {
                ksu_selinux_hide_running = true;
            }
        }
        /* publish only after enable() succeeded, so get_handler and the
         * SUSFS static hooks never see "on" while the feature is down */
        if (ksu_selinux_hide_running)
            ksu_selinux_hide_enabled = true;
    } else {""",
    ),
    (
        "feature_set: clear enabled on disable",
        """            ksu_selinux_hide_running = false;
        }
    }
    mutex_unlock(&selinux_hide_mutex);""",
        """            ksu_selinux_hide_running = false;
        }
        ksu_selinux_hide_enabled = false;
    }
    mutex_unlock(&selinux_hide_mutex);""",
    ),
]


def main(path):
    p = pathlib.Path(path)
    src = p.read_text(encoding="utf-8")
    if "publish only after enable() succeeded" in src:
        print("already patched, skip")
        return 0
    for label, old, new in RULES:
        n = src.count(old)
        if n != 1:
            print(f"::error::[{label}] expected 1 match, found {n}")
            return 1
        src = src.replace(old, new, 1)
        print(f"  applied: {label}")
    p.write_bytes(src.encode("utf-8"))
    print("PATCH OK")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: patch_selinux_hide.py <selinux_hide.c>")
    sys.exit(main(sys.argv[1]))
