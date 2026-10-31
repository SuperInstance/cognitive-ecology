#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# bootstrap.sh — create the private GitHub repo and make the first push.
#
# SECURITY MODEL (read before running):
#   * The GitHub PAT comes from the GITHUB_PAT environment variable ONLY.
#     This script never asks for it interactively and never writes it down.
#   * The push uses a temporary GIT_ASKPASS shim: the script file contains
#     only a *reference* to $GITHUB_PAT; the value itself stays in memory.
#     The shim is deleted afterwards (trap).
#   * If anything looks like it would put a credential on disk, it fails
#     loudly instead.
#
# Usage:
#   export GITHUB_PAT=ghp_...        # env-only, never a file
#   ./bootstrap.sh [repo-name] [description]
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_NAME="${1:-cognitive-ecology}"
DESCRIPTION="${2:-A zero-dependency Python kernel for agents that persist like organisms}"
API="https://api.github.com"

die() { echo "bootstrap: $1" >&2; exit 1; }

# --- preflight --------------------------------------------------------------
command -v git  >/dev/null 2>&1 || die "git is required"
command -v curl >/dev/null 2>&1 || die "curl is required"

[ -n "${GITHUB_PAT:-}" ] || die "GITHUB_PAT is not set (export it first; never paste it into files)"
case "$GITHUB_PAT" in
  *$'\n'*) die "GITHUB_PAT contains a newline; refusing" ;;
esac

# refuse to run inside a dirty secrets situation
if [ -f .env ]; then
  grep -qE "=(ghp_|sk-di-|apikey_)" .env && die ".env appears to contain real keys; bootstrap refuses to proceed"
fi

# --- figure out the GitHub username ----------------------------------------
USER_JSON="$(curl -sf -H "Authorization: Bearer $GITHUB_PAT" "$API/user")" \
  || die "could not authenticate against $API — check GITHUB_PAT"
OWNER="$(printf '%s' "$USER_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["login"])')"
echo "bootstrap: authenticated as $OWNER"

# --- create the private repo ------------------------------------------------
echo "bootstrap: creating private repo $OWNER/$REPO_NAME ..."
HTTP_CODE="$(curl -s -o /tmp/repo_create_body.$$ -w '%{http_code}' \
  -X POST -H "Authorization: Bearer $GITHUB_PAT" -H "Accept: application/vnd.github+json" \
  "$API/user/repos" \
  -d "{\"name\":\"$REPO_NAME\",\"description\":\"$DESCRIPTION\",\"private\":true}")"
case "$HTTP_CODE" in
  201) echo "bootstrap: repo created" ;;
  422) echo "bootstrap: repo already exists — continuing (will push to it)" ;;
  *)   python3 -c "print(open('/tmp/repo_create_body.$$').read()[:400])" || true
       rm -f "/tmp/repo_create_body.$$"
       die "repo creation failed (HTTP $HTTP_CODE)" ;;
esac
rm -f "/tmp/repo_create_body.$$"

# --- askpass shim: the PAT transits memory, not disk ------------------------
ASKPASS="$(mktemp)"
trap 'rm -f "$ASKPASS"' EXIT
cat > "$ASKPASS" <<'SHIM'
#!/usr/bin/env bash
# prints the token from the ENVIRONMENT (no value stored on disk)
printf '%s' "$GITHUB_PAT"
SHIM
chmod +x "$ASKPASS"
export GIT_ASKPASS="$ASKPASS"
export GIT_ASKPASS_REQUIRE=force 2>/dev/null || true
export GIT_TERMINAL_PROMPT=0

REMOTE="https://github.com/$OWNER/$REPO_NAME.git"

# --- initialize / verify the working tree ------------------------------------
if [ ! -d .git ]; then
  git init -b main
  git add -A
  # sanity: refuse to commit anything key-shaped
  if git diff --cached | grep -qE "(ghp_[A-Za-z0-9]{20,}|sk-di-[A-Za-z0-9]{20,}|apikey_[A-Za-z0-9]{20,})"; then
    die "staged content contains key-shaped strings — ABORTING before commit"
  fi
  git -c user.name="cognitive-ecology bootstrap" \
      -c user.email="bootstrap@localhost" \
      commit -m "v0.2.0: persistent cognitive ecology kernel — L0-L8, WHY conservation, attention market, docs, examples" \
    || die "nothing to commit?"
else
  echo "bootstrap: existing git repo found — adding a remote and pushing"
fi

# point origin at the new private repo (idempotent)
git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE"

# --- first push ---------------------------------------------------------------
if git ls-remote --heads origin 2>/dev/null | grep -q main; then
  echo "bootstrap: remote already has a main branch; NOT force-pushing."
  echo "bootstrap: to push anyway:  git push origin main"
else
  git push -u origin main
  echo "bootstrap: pushed $OWNER/$REPO_NAME (private)"
fi

echo ""
echo "bootstrap: done."
echo "  repo : $REMOTE"
echo "  next : git push origin main   # subsequent pushes"
echo "  note : the PAT never touched disk (askpass shim, removed)"
