#!/usr/bin/env bash
# Installs the skill-gate hooks into ~/.claude and merges the hook config into ~/.claude/settings.json
# (the old file is kept as settings.json.bak). Run it from anywhere: bash install.sh
# The skill itself (SKILL.md) is installed by linking or copying this folder to ~/.claude/skills/skill-gate;
# if that is not done yet, this script copies SKILL.md there.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME/.claude/hooks/skill-gate" "$HOME/.claude/scripts"
cp "$HERE"/hooks/*.py "$HOME/.claude/hooks/skill-gate/"
cp "$HERE"/scripts/skill_usage_report.py "$HOME/.claude/scripts/"
chmod +x "$HOME"/.claude/hooks/skill-gate/*.py "$HOME/.claude/scripts/skill_usage_report.py"

SKILL_DIR="$HOME/.claude/skills/skill-gate"
if [ ! -e "$SKILL_DIR/SKILL.md" ]; then
  mkdir -p "$SKILL_DIR"
  cp "$HERE/SKILL.md" "$SKILL_DIR/"
fi

SETTINGS="$HOME/.claude/settings.json"
if [ -f "$SETTINGS" ]; then cp "$SETTINGS" "$SETTINGS.bak"; else echo '{}' > "$SETTINGS"; fi
python3 - "$SETTINGS" "$HERE/settings.hooks.json" <<'PY'
import json, sys
dst, src = sys.argv[1], sys.argv[2]
cur = json.load(open(dst)); new = json.load(open(src))
hooks = cur.setdefault("hooks", {})
for ev, entries in new["hooks"].items():
    lst = hooks.setdefault(ev, [])
    for e in entries:
        if not any(json.dumps(x, sort_keys=True) == json.dumps(e, sort_keys=True) for x in lst):
            lst.append(e)
json.dump(cur, open(dst, "w"), indent=2)
PY
echo "skill-gate installed. Restart Claude Code (or open /hooks) so the hooks load."
echo "Usage report: python3 ~/.claude/scripts/skill_usage_report.py"
