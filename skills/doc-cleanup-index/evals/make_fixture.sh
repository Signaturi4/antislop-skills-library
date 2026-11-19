#!/usr/bin/env bash
# Tiny workspace: root docs, a git repo with technical + non-technical docs, html, pdf, a secret file, 8 folders.
set -e; W="$(mkdir -p "$1" && cd "$1" && pwd)"; mkdir -p "$W"; cd "$W"
mkdir -p company research/notes "projects" hobbies a b c d e f g
printf "Aquarium fish care, water temperature and filters.\n" > hobbies/aquarium.md
printf '# Strategy\nGoals, positioning and pricing decisions for the company.\nSee [research](../research/notes/personas.md).\n' > company/strategy.md
printf '# Personas\nCustomer research: personas and ICP segments from interviews.\n' > research/notes/personas.md
printf '<html><body><h1>Offer</h1><p>Proposal and pricing offer for a client.</p><a href="../company/strategy.md">s</a><a href="missing.md">x</a></body></html>' > company/offer.html
printf 'API_KEY=sk-test-123\n' > .env
mkdir -p projects/shop-app && cd projects/shop-app && git init -q && git config user.email t@t && git config user.name t
mkdir -p docs notes/deep/plan
printf '# API reference\nBackend API endpoints, database schema, integrations.\n' > docs/api.md
printf '# Marketing plan\nMarketing content plan: social posts and brand.\nAPI: [api](../../../docs/api.md)\nPath: `notes/deep/plan/marketing-plan.md`\n' > notes/deep/plan/marketing-plan.md
git add -A && git commit -qm init && cd "$W"
python3 - <<'PY'
# minimal one-page PDF with text "Research findings report"
c=b"BT /F1 12 Tf 20 100 Td (Research findings report on customer personas) Tj ET"
objs=[b"<</Type/Catalog/Pages 2 0 R>>",b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 200]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
b"<</Length %d>>stream\n"%len(c)+c+b"\nendstream",b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"]
out=b"%PDF-1.4\n";offs=[]
for i,o in enumerate(objs,1): offs.append(len(out)); out+=b"%d 0 obj\n"%i+o+b"\nendobj\n"
x=len(out);out+=b"xref\n0 %d\n0000000000 65535 f \n"%(len(objs)+1)+b"".join(b"%010d 00000 n \n"%o for o in offs)
out+=b"trailer<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF"%(len(objs)+1,x)
open("research/findings.pdf","wb").write(out)
PY
