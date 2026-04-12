#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="settings/.env"
VENV_DIR="venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SUPERUSER_EMAIL="admin@example.com"
SUPERUSER_PASSWORD="Admin12345"
SUPERUSER_FIRST_NAME="Admin"
SUPERUSER_LAST_NAME="User"

step() {
  echo "==> $1"
}

fail() {
  echo "Step failed: $1" >&2
  exit 1
}

require_env_var() {
  local name="$1"
  local value
  value=$(grep -E "^${name}=" "$ENV_FILE" | tail -n1 | cut -d '=' -f2- || true)
  if [[ -z "${value// /}" ]]; then
    echo "Missing environment variable: $name"
    exit 1
  fi
}

[[ -f "$ENV_FILE" ]] || fail "settings/.env is missing"

step "Validating environment variables"
for var in BLOG_ENV_ID BLOG_SECRET_KEY BLOG_DEBUG BLOG_ALLOWED_HOSTS BLOG_REDIS_URL; do
  require_env_var "$var"
done

step "Creating virtual environment"
if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR" || fail "creating virtual environment"
fi
source "$VENV_DIR/bin/activate"

step "Installing dependencies"
pip install -r requirements/base.txt || fail "installing dependencies"

step "Running migrations"
python manage.py migrate || fail "running migrations"

step "Collecting static files"
python manage.py collectstatic --noinput || fail "collecting static files"

step "Compiling translation files"
python - <<'PY'
from pathlib import Path
import polib
for po_path in Path('locale').rglob('django.po'):
    mo_path = po_path.with_name('django.mo')
    po = polib.pofile(str(po_path))
    po.save_as_mofile(str(mo_path))
    print(f'Compiled {po_path}')
PY

step "Creating superuser if missing"
python manage.py shell <<PY || fail "creating superuser"
from django.contrib.auth import get_user_model
User = get_user_model()
email = "${SUPERUSER_EMAIL}"
if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(
        email=email,
        password="${SUPERUSER_PASSWORD}",
        first_name="${SUPERUSER_FIRST_NAME}",
        last_name="${SUPERUSER_LAST_NAME}",
    )
    print("Superuser created")
else:
    print("Superuser already exists")
PY

step "Seeding demo data"
python manage.py seed || fail "seeding demo data"

echo
printf 'Project URLs:\n'
printf 'API: http://127.0.0.1:8000/api/\n'
printf 'Swagger UI: http://127.0.0.1:8000/api/docs/\n'
printf 'ReDoc: http://127.0.0.1:8000/api/redoc/\n'
printf 'Admin: http://127.0.0.1:8000/admin/\n'
printf 'Superuser email: %s\n' "$SUPERUSER_EMAIL"
printf 'Superuser password: %s\n' "$SUPERUSER_PASSWORD"
echo

step "Starting development server"
python manage.py runserver 127.0.0.1:8000
