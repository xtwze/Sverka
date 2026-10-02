#!/bin/sh
set -eu
# Выполнять только в выделенном контейнере с новым /var/lib/1c/review.
cd /workspace
platform=/opt/1cv8t/x86_64/8.3.27.1508
database=/var/lib/1c/review
logs=/var/lib/1c/review-logs

xvfb-run -a python3 -m scripts.onec_demo \
  --platform "$platform/1cv8t" --database "$database"
xvfb-run -a "$platform/1cv8t" ENTERPRISE /F "$database" \
  /C "demo-access|$logs/access.json" /Out "$logs/access.log" \
  /DisableStartupDialogs /DisableStartupMessages
python3 -c 'import json; r=json.load(open("/var/lib/1c/review-logs/access.json", encoding="utf-8-sig")); assert r["status"] == "PASS", r; print(r)'
xvfb-run -a "$platform/1cv8ct" ENTERPRISE /F "$database" /N APIReader \
  /C "demo-readonly|$logs/readonly.json" /Out "$logs/readonly.log" \
  /DisableStartupDialogs /DisableStartupMessages
python3 -c 'import json; r=json.load(open("/var/lib/1c/review-logs/readonly.json", encoding="utf-8-sig")); assert r["status"] == "PASS", r; assert len(r["write_checks"]) == 3; print(r)'
