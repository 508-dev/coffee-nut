#!/usr/bin/env bash
# bash, not sh: `wait -n` (exit as soon as either service dies) is not POSIX and
# is unsupported by dash. Every other script in scripts/ stays POSIX sh.
set -eu

cd "$(dirname "$0")/.."
WORKTREE_ROOT="$(pwd -P)"

usage() {
  cat >&2 <<'USAGE'
usage: dev.sh [--reclaim-ports]

Starts Compose infrastructure plus both host app services:
  - Django  on API_PORT
  - Vite    on WEB_PORT

Ports are derived from the worktree path, so sibling worktrees run together
without editing .env. See ./scripts/worktree-ports.sh env.

Options:
  --reclaim-ports      Stop this worktree's own leftover api/web process if it
                       still holds its port. Refuses to touch anything else.
  --no-reclaim-ports   Disable even when DEVKIT_RECLAIM_PORTS=1.
  --help               Show this help.
USAGE
}

RECLAIM_PORTS="${DEVKIT_RECLAIM_PORTS:-0}"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --reclaim-ports) RECLAIM_PORTS=1 ;;
    --no-reclaim-ports) RECLAIM_PORTS=0 ;;
    --help|-h) usage; exit 0 ;;
    *) usage; exit 2 ;;
  esac
  shift
done

if [ ! -f .env ]; then
  echo "No .env found; copying .env.example. Review it before deploying anything." >&2
  cp .env.example .env
fi

# Exported port values win over .env: django-environ's read_env uses setdefault,
# so the shell environment takes precedence. That is what keeps worktrees apart.
eval "$(./scripts/worktree-ports.sh export)"
export WEB_HOST="${WEB_HOST:-127.0.0.1}"
export API_HOST="${API_HOST:-127.0.0.1}"

port_listener_pids() {
  port="$1"
  if ! command -v lsof >/dev/null 2>&1; then
    echo "dev.sh --reclaim-ports requires lsof to inspect port owners." >&2
    return 1
  fi
  lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | sort -u
}

process_cwd() {
  pid="$1"
  lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | sed -n '1p'
}

process_command() {
  pid="$1"
  ps -p "$pid" -o command= 2>/dev/null || true
}

process_parent_pid() {
  pid="$1"
  ps -p "$pid" -o ppid= 2>/dev/null | tr -d ' ' || true
}

is_inside_worktree() {
  path="$1"
  case "$path" in
    "$WORKTREE_ROOT"|"$WORKTREE_ROOT"/*) return 0 ;;
    *) return 1 ;;
  esac
}

is_expected_service_command() {
  service_name="$1"
  command_line="$2"

  case "$service_name" in
    web)
      is_expected_web_dev_command "$command_line"
      ;;
    api)
      is_expected_api_dev_command "$command_line"
      ;;
    *)
      return 1
      ;;
  esac
}

is_expected_api_dev_command() {
  command_line="$1"
  case "$command_line" in
    *manage.py\ runserver*|*django-admin*|*gunicorn*|*uvicorn*|\
    *" uv run"*|uv\ run*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_expected_web_dev_command() {
  command_line="$1"
  case "$command_line" in
    next\ dev*|*" next dev"*|*next-server*|\
    vite\ *|*" vite "*|\
    astro\ dev*|*" astro dev"*|\
    remix\ vite:dev*|*" remix vite:dev"*|\
    webpack\ serve*|*" webpack serve"*|\
    rspack\ serve*|*" rspack serve"*|\
    rsbuild\ dev*|*" rsbuild dev"*|\
    parcel\ serve*|*" parcel serve"*|\
    tanstack\ start*|*" tanstack start"*|\
    tsc\ --noEmit\ --watch*|*" tsc --noEmit --watch"*|\
    bun\ run*|*" bun run"*|\
    pnpm\ *|*" pnpm "*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_expected_service_process() {
  service_name="$1"
  pid="$2"
  depth=0

  while [ -n "$pid" ] && [ "$pid" -gt 1 ] 2>/dev/null && [ "$depth" -lt 8 ]; do
    command_line="$(process_command "$pid")"
    cwd="$(process_cwd "$pid")"

    if [ -n "$cwd" ] && is_inside_worktree "$cwd" && is_expected_service_command "$service_name" "$command_line"; then
      return 0
    fi

    pid="$(process_parent_pid "$pid")"
    depth=$((depth + 1))
  done

  return 1
}

wait_for_port_release() {
  port="$1"
  attempts=0
  while [ "$attempts" -lt 20 ]; do
    if [ -z "$(port_listener_pids "$port")" ]; then
      return 0
    fi
    attempts=$((attempts + 1))
    sleep 0.1
  done
  return 1
}

reclaim_service_port() {
  service_name="$1"
  port="$2"
  pids="$(port_listener_pids "$port")"
  if [ -z "$pids" ]; then
    return 0
  fi

  reclaim_pids=""
  for pid in $pids; do
    if ! is_expected_service_process "$service_name" "$pid"; then
      command_line="$(process_command "$pid")"
      cwd="$(process_cwd "$pid")"
      echo "Refusing to reclaim ${service_name} port ${port}; pid ${pid} does not look like this worktree's ${service_name} process." >&2
      echo "  cwd: ${cwd:-unknown}" >&2
      echo "  cmd: ${command_line:-unknown}" >&2
      return 1
    fi

    reclaim_pids="${reclaim_pids}${pid} "
  done

  for pid in $reclaim_pids; do
    echo "Reclaiming ${service_name} port ${port} from pid ${pid}"
    kill "$pid" 2>/dev/null || true
  done

  if wait_for_port_release "$port"; then
    return 0
  fi

  echo "${service_name} port ${port} is still in use after SIGTERM; refusing to force-kill it." >&2
  return 1
}

if [ "$RECLAIM_PORTS" = "1" ]; then
  reclaim_service_port api "$API_PORT" || true
  reclaim_service_port web "$WEB_PORT" || true
fi

API_PID=""
WEB_PID=""

cleanup() {
  # Kill children on the way out so Ctrl-C does not leave a port bound.
  [ -n "$API_PID" ] && kill "$API_PID" 2>/dev/null || true
  [ -n "$WEB_PID" ] && kill "$WEB_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

wait_for_postgres() {
  attempts=0
  while [ "$attempts" -lt 60 ]; do
    if ./scripts/docker-compose.sh exec -T postgres \
        pg_isready -U "${POSTGRES_USER:-app}" -d "${POSTGRES_DB:-app}" >/dev/null 2>&1; then
      return 0
    fi
    attempts=$((attempts + 1))
    sleep 0.5
  done
  echo "Postgres did not become ready within 30s." >&2
  return 1
}

echo "coffee-nut local stack"
echo
echo "==> infrastructure"
./scripts/docker-compose.sh up -d postgres redis
wait_for_postgres

echo "==> migrations"
uv run python apps/api/manage.py migrate --noinput

echo
echo "  API       http://${API_HOST}:${API_PORT}  (schema at /api/docs/)"
echo "  Web       ${WEB_URL}"
echo "  Postgres  127.0.0.1:${POSTGRES_HOST_PORT}"
echo "  Redis     127.0.0.1:${REDIS_HOST_PORT}"
echo

uv run python apps/api/manage.py runserver "${API_HOST}:${API_PORT}" &
API_PID=$!

bun run --cwd apps/web dev &
WEB_PID=$!

# Surface a crash immediately rather than pretending the stack is still up.
wait -n "$API_PID" "$WEB_PID"
echo "A dev service exited; shutting the other one down." >&2
