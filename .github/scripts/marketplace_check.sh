#!/usr/bin/env bash
# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt
#
# Marketplace publishability check for off_invoice_rebates.
# Runs in CI on every push/PR and locally when verifying release readiness.
set -euo pipefail

ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
APP_PKG="$ROOT/off_invoice_rebates"

FAIL=0

fail() {
	echo "FAIL: $1"
	FAIL=1
}
warn() {
	echo "WARN: $1"
}

echo "Running marketplace publishability check from $ROOT..."

# 1. No edits to standard apps inside this repo.
if [ -d "$ROOT/apps/frappe" ] || [ -d "$ROOT/apps/erpnext" ]; then
	fail "Found apps/frappe or apps/erpnext in repo - the rebate app must NOT contain standard apps."
fi

# 2. license.txt must exist and contain GPLv3.
if [ ! -f "$ROOT/license.txt" ]; then
	fail "license.txt missing."
elif ! grep -q "GNU GENERAL PUBLIC LICENSE" "$ROOT/license.txt"; then
	fail "license.txt does not contain GPLv3 text."
fi

# 3. pyproject.toml metadata.
if [ ! -f "$ROOT/pyproject.toml" ]; then
	fail "pyproject.toml missing."
else
	grep -q "authors" "$ROOT/pyproject.toml" || fail "pyproject.toml missing authors."
	grep -q "description" "$ROOT/pyproject.toml" || fail "pyproject.toml missing description."
fi

# 4. hooks.py must declare required_apps and app_license=gpl-3.0.
if [ ! -f "$APP_PKG/hooks.py" ]; then
	fail "hooks.py missing under $APP_PKG."
else
	grep -q "required_apps" "$APP_PKG/hooks.py" \
		|| fail "hooks.py must declare required_apps = [\"erpnext\"]."
	grep -q "app_license" "$APP_PKG/hooks.py" \
		|| fail "hooks.py must declare app_license."
fi

# 5. No print() statements in production code (tests are allowed).
# Tab-indented and space-indented patterns both excluded.
if grep -r --include="*.py" \
		--exclude-dir=tests \
		--exclude-dir=__pycache__ \
		-E '^[[:space:]]*print\(' "$APP_PKG" 2>/dev/null \
		| grep -v "# debug-ok" >/dev/null; then
	fail "Found print() statements outside tests."
fi

# 6. No hardcoded credentials.
if grep -rE --include="*.py" \
		--exclude-dir=tests \
		--exclude-dir=__pycache__ \
		"(password|secret|api_key)[[:space:]]*=[[:space:]]*['\"][^'\"]+['\"]" \
		"$APP_PKG" 2>/dev/null \
		| grep -v "# noqa-secret" >/dev/null; then
	warn "Possible hardcoded credential found."
fi

# 7. README has English and Italian sections.
if [ -f "$ROOT/README.md" ]; then
	grep -q -E "English|🇬🇧" "$ROOT/README.md" || warn "README missing English section header."
	grep -q -E "Italiano|🇮🇹" "$ROOT/README.md" || warn "README missing Italian section header."
else
	warn "README.md missing at repo root."
fi

# 8. Fixtures declared in hooks.py.
grep -q "fixtures" "$APP_PKG/hooks.py" || warn "hooks.py does not export fixtures."

if [ "$FAIL" -eq 0 ]; then
	echo "Marketplace publishability check passed."
	exit 0
fi
echo "Marketplace publishability check FAILED."
exit 1
