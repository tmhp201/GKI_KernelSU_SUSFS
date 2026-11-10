#!/usr/bin/env python3
"""Anchor-based kernel-side fix for BakaSU's selinux_hide.c.

Two independent changes, both applied to kernel/feature/selinux_hide.c:

1) (previous) state-flag ordering in selinux_hide_feature_set():
   ksu_selinux_hide_enabled was published before ksu_selinux_hide_enable()
   ran, so a failed enable left the manager showing "on" while
   ksu_selinux_hide_running stayed false and every SUSFS static hook was
   gated off.

2) (new) sensitive-type filtering in my_write_access() / my_write_context():
   The SUSFS wrappers (handle_sel_write_access / handle_sel_write_context)
   only gate on uid >= 10000 and ksu_selinux_hide_running.  They then call
   my_write_access(), which computes the answer against backup_sepolicy --
   a full copy of the *real* policy including ksu_file, lsposed_file,
   magisk and vendor domains.  So an app querying
   "untrusted_app -> ksu_file file read" via raw selinuxfs gets a genuine
   allow/deny answer instead of EINVAL, which is exactly what the
   Chunqiu detector reports as
   "untrusted_app -> ksu_file read / lsposed_file read".

   Fix: before computing anything, scan scon/tcon for the root-related
   type names.  If present, return -EINVAL, i.e. behave as if the type
   does not exist in the policy.  Types come from a small watch list and
   are matched as whole identifiers, not substrings.

Both changes are guarded so a kernel without CONFIG_KSU_SUSFS keeps the
original runtime-patch path untouched.

Usage: python3 patches/patch_selinux_hide.py <path/to/selinux_hide.c>
"""
import pathlib
import sys

RULES = []


def rule(label, old, new):
    RULES.append((label, old, new))


# ---------------------------------------------------------------- part 1
rule(
    "feature_set: do not publish flag before enable()",
    """    mutex_lock(&selinux_hide_mutex);
    ksu_selinux_hide_enabled = enable;
    if (enable) {""",
    """    mutex_lock(&selinux_hide_mutex);
    if (enable) {""",
)

rule(
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
)

rule(
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
)


# ---------------------------------------------------------------- part 2
# Helper inserted before my_write_context().  Whole-token match so that e.g.
# "not_ksu_file" or "magisk_like" never match.
rule(
    "add sensitive type filter helper",
    """__maybe_static ssize_t my_write_context(struct file *file, char *buf, size_t size)
{""",
    """/*
 * Root-related SELinux types that must look nonexistent to app queries.
 * backup_sepolicy is a full copy of the live policy, so without this filter
 * an app asking about ksu_file / lsposed_file gets a real answer and can
 * enumerate the root implementation's domains and types.
 */
static const char *const slh_sensitive_types[] = {
    "ksu",
    "ksu_file",
    "ksu_domain",
    "lsposed_file",
    "magisk",
    "magisk_file",
    "apatch",
    "droidspacesd",
    "droidspacesd_exec",
    NULL,
};

/*
 * Return true when the space separated context string contains one of the
 * sensitive type names as a whole token.  Contexts look like
 * "u:r:ksu:s0" or "u:object_r:ksu_file:s0", so the type sits between the
 * second and third colon; we simply match the whole token between seps.
 */
static bool slh_context_has_sensitive_type(const char *context)
{
    const char *p = context;
    int i;

    while (*p) {
        const char *start, *end;
        size_t len;

        while (*p == ' ' || *p == '\\n' || *p == '\\t')
            p++;
        if (!*p)
            break;
        start = p;
        while (*p && *p != ' ' && *p != '\\n' && *p != '\\t')
            p++;
        end = p;
        len = (size_t)(end - start);
        if (!len)
            break;

        for (i = 0; slh_sensitive_types[i]; i++) {
            const char *t = slh_sensitive_types[i];
            size_t tlen = strlen(t);
            const char *c;

            /* the field is "u:role:type[:level]"; walk the colons */
            c = start;
            while (c < end) {
                const char *field = c;
                const char *field_end;

                while (c < end && *c != ':')
                    c++;
                field_end = c;
                if ((size_t)(field_end - field) == tlen &&
                    !strncmp(field, t, tlen))
                    return true;
                if (c < end)
                    c++; /* skip ':' */
            }
        }
    }
    return false;
}

__maybe_static ssize_t my_write_context(struct file *file, char *buf, size_t size)
{""",
)

rule(
    "my_write_context: reject sensitive types",
    """    char *canon = NULL;
    u32 sid, len;
    ssize_t length;

    length =
        ksu_avc_has_perm_compat(current_sid(), SECINITSID_SECURITY, SECCLASS_SECURITY, SECURITY__CHECK_CONTEXT, NULL);""",
    """    char *canon = NULL;
    u32 sid, len;
    ssize_t length;

    /* present a policy in which the root implementation's types do not
     * exist; a detector asking about ksu_file must get EINVAL */
    if (size > 0 && slh_context_has_sensitive_type(buf))
        return -EINVAL;

    length =
        ksu_avc_has_perm_compat(current_sid(), SECINITSID_SECURITY, SECCLASS_SECURITY, SECURITY__CHECK_CONTEXT, NULL);""",
)

rule(
    "my_write_access: reject sensitive types",
    """    u16 tclass;
    struct av_decision avd;
    ssize_t length;

    length = ksu_avc_has_perm_compat(current_sid(), SECINITSID_SECURITY, SECCLASS_SECURITY, SECURITY__COMPUTE_AV, NULL);""",
    """    u16 tclass;
    struct av_decision avd;
    ssize_t length;

    /* see my_write_context: hide the root types entirely */
    if (size > 0 &&
        (slh_context_has_sensitive_type(buf)))
        return -EINVAL;

    length = ksu_avc_has_perm_compat(current_sid(), SECINITSID_SECURITY, SECCLASS_SECURITY, SECURITY__COMPUTE_AV, NULL);""",
)


def main(path):
    p = pathlib.Path(path)
    src = p.read_text(encoding="utf-8")
    if "slh_context_has_sensitive_type" in src:
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
