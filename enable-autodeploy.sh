#!/usr/bin/env bash
# =====================================================================
# Run ONCE on the Google Cloud VM to enable push-to-deploy from GitHub.
# Generates a deploy SSH key, authorizes it, and prints the three GitHub
# secrets to add. After that, every push to main auto-deploys here (via
# .github/workflows/deploy-gcp.yml).
#
#   bash enable-autodeploy.sh
# =====================================================================
set -euo pipefail

KEY="$HOME/.ssh/gh_deploy"
mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
[ -f "$KEY" ] || ssh-keygen -t ed25519 -f "$KEY" -N "" -C "github-actions-deploy" >/dev/null

touch "$HOME/.ssh/authorized_keys" && chmod 600 "$HOME/.ssh/authorized_keys"
grep -qxF "$(cat "$KEY.pub")" "$HOME/.ssh/authorized_keys" \
  || cat "$KEY.pub" >> "$HOME/.ssh/authorized_keys"

IP="$(curl -fsS -H 'Metadata-Flavor: Google' \
  http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip 2>/dev/null || true)"

cat <<EOF

============================================================
הוסף ב-GitHub → Settings → Secrets and variables → Actions
→ New repository secret (שלושה סודות):

  GCP_VM_HOST   = ${IP:-<ה-IP החיצוני של ה-VM מהקונסולה של גוגל>}
  GCP_VM_USER   = $(whoami)
  GCP_VM_SSH_KEY = הדבק את כל הבלוק הבא (כולל שורות BEGIN/END):
------------------------------------------------------------
$(cat "$KEY")
------------------------------------------------------------

מעכשיו: כל \`git push\` ל-main יפרוס אוטומטית ל-VM הזה.
(ודא שחומת האש של GCP מאפשרת SSH על פורט 22 — ברירת המחדל כן.)
============================================================
EOF
