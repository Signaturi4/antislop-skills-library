"""Shared helpers for doc-cleanup-index scripts (stdlib only)."""
import os, re

DOC_EXT = (".md", ".html", ".htm", ".pdf")
PRUNE = {"node_modules", ".git", ".venv", "venv", "env", "dist", "build", ".next", "out-tsc", "__pycache__",
         "raw", "archive", "7-archive", "vendor", "site-packages", ".cache", "coverage"}
SECRET = re.compile(r"(^|/)(\.env[^/]*|[^/]*\.env|[^/]*secret[^/]*|id_rsa[^/]*|[^/]*\.pem|[^/]*\.key)$", re.I)


def is_repo(p):
    return os.path.exists(os.path.join(p, ".git"))


def repo_of(path, root):
    """Closest git repo containing path (stops at root), or None."""
    p = os.path.abspath(path if os.path.isdir(path) else os.path.dirname(path))
    root = os.path.abspath(root)
    while p.startswith(root):
        if is_repo(p):
            return p
        if p == root:
            break
        p = os.path.dirname(p)
    return None


def walk_docs(root, extra_prune=()):
    prune = PRUNE | set(extra_prune)
    for r, ds, fs in os.walk(root):
        ds[:] = sorted(d for d in ds if d not in prune and not d.startswith(".") and "offline" not in d.lower())
        for f in sorted(fs):
            p = os.path.join(r, f)
            if f.lower().endswith(DOC_EXT) and not SECRET.search(p) and not os.path.islink(p):
                yield p


def trash_dir():
    mac = os.path.expanduser("~/.Trash")
    return mac if os.path.isdir(mac) else os.path.expanduser("~/.local/share/Trash/files")
