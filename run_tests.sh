#!/usr/bin/env bash
#
# Run the Django test suite locally on SQLite (no .env / database needed).
#
#   ./run_tests.sh            # run everything
#   ./run_tests.sh finance    # run just the finance app
#
# Django's test runner automatically uses an in-memory email backend and a
# throwaway test database, so no real emails are sent and your data is untouched.
set -euo pipefail

cd "$(dirname "$0")/property_management"

# Isolated virtualenv so we don't touch your system Python.
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip >/dev/null
pip install -r requirements.txt

# Force the local SQLite fallback regardless of any ambient env vars.
export ENV=development
export USE_SQLITE=1

echo "── Checking for missing migrations ──"
python manage.py makemigrations --check --dry-run || {
  echo "WARNING: model changes without a migration detected (see above).";
}

echo "── Running tests ──"
python manage.py test "$@"
