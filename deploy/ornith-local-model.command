#!/bin/bash
set -euo pipefail

PROJECT_ROOT="${ORNITH_PROJECT_ROOT:-/Users/wilsonxu/Models/ornith-256k}"
LAUNCH_DOMAIN="gui/$(id -u)"

LLAMA_LABEL="local.llamacpp.ornith-256k"
LLAMA_PLIST="${HOME}/Library/LaunchAgents/${LLAMA_LABEL}.plist"
LLAMA_URL="http://127.0.0.1:7871"
LLAMA_HEALTH_URL="${LLAMA_URL}/health"
LLAMA_LOG="${PROJECT_ROOT}/runtime/logs/llama-server.log"

BRIDGE_LABEL="local.ornith.gemini-bridge"
BRIDGE_PLIST="${HOME}/Library/LaunchAgents/${BRIDGE_LABEL}.plist"
BRIDGE_URL="http://127.0.0.1:7872"
BRIDGE_MODELS_URL="${BRIDGE_URL}/v1beta/models"
BRIDGE_LOG="${PROJECT_ROOT}/runtime/logs/gemini-openai-bridge.log"
BRIDGE_ERROR_LOG="${PROJECT_ROOT}/runtime/logs/gemini-openai-bridge.error.log"
BRIDGE_TEST="${PROJECT_ROOT}/runtime/test-gemini-openai-bridge.mjs"
NODE_BIN="${ORNITH_NODE_BIN:-/Users/wilsonxu/.nvm/versions/node/v24.11.1/bin/node}"

DRY_RUN=0
MENU_MODE=0

print_command() {
    printf '+'
    printf ' %q' "$@"
    printf '\n'
}

run_command() {
    if ((DRY_RUN)); then
        print_command "$@"
    else
        "$@"
    fi
}

service_target() {
    printf '%s/%s' "$LAUNCH_DOMAIN" "$1"
}

service_loaded() {
    launchctl print "$(service_target "$1")" >/dev/null 2>&1
}

port_listening() {
    lsof -nP -iTCP:"$1" -sTCP:LISTEN -t >/dev/null 2>&1
}

http_status() {
    local response
    if response="$(curl --noproxy '*' --connect-timeout 2 --max-time 4 -sS -o /dev/null -w '%{http_code}' "$1" 2>/dev/null)"; then
        printf '%s' "$response"
    fi
}

wait_for_url() {
    local url="$1"
    local expected_status="$2"
    local attempts="$3"
    local status

    for ((attempt = 1; attempt <= attempts; attempt++)); do
        status="$(http_status "$url")"
        if [[ "$status" == "$expected_status" ]]; then
            return 0
        fi
        sleep 1
    done
    return 1
}

wait_for_stopped() {
    local label="$1"
    local port="$2"

    for ((attempt = 1; attempt <= 20; attempt++)); do
        if ! service_loaded "$label" && ! port_listening "$port"; then
            return 0
        fi
        sleep 1
    done
    return 1
}

enable_service() {
    local label="$1"
    local plist="$2"

    run_command launchctl enable "$(service_target "$label")"
    if ! service_loaded "$label"; then
        run_command launchctl bootstrap "$LAUNCH_DOMAIN" "$plist"
    elif [[ "$(service_state "$label")" != "running" ]]; then
        run_command launchctl kickstart -k "$(service_target "$label")"
    fi
}

stop_service() {
    local label="$1"

    run_command launchctl disable "$(service_target "$label")"
    if ((DRY_RUN)) || service_loaded "$label"; then
        run_command launchctl bootout "$(service_target "$label")"
    fi
}

service_state() {
    local label="$1"
    if ! service_loaded "$label"; then
        printf 'unloaded'
        return
    fi
    launchctl print "$(service_target "$label")" 2>/dev/null \
        | awk -F'= ' '/^[[:space:]]*state = / { print $2; exit }' \
        || printf 'loaded'
}

status() {
    local llama_state bridge_state llama_http bridge_http
    llama_state="$(service_state "$LLAMA_LABEL")"
    bridge_state="$(service_state "$BRIDGE_LABEL")"
    llama_http="$(http_status "$LLAMA_HEALTH_URL")"
    bridge_http="$(http_status "$BRIDGE_MODELS_URL")"

    printf 'Ornith local model\n'
    printf '  llama.cpp  : %-9s port 7871  health HTTP %s\n' "$llama_state" "${llama_http:-down}"
    printf '  Gemini     : %-9s port 7872  models HTTP %s\n' "$bridge_state" "${bridge_http:-down}"

    if [[ "$llama_http" == "200" && "$bridge_http" == "401" ]]; then
        printf '  overall    : ready\n'
    elif [[ "$llama_state" != "unloaded" || "$bridge_state" != "unloaded" || -n "$llama_http" || -n "$bridge_http" ]]; then
        printf '  overall    : starting or partially available\n'
    else
        printf '  overall    : stopped\n'
    fi
}

start() {
    if ((DRY_RUN)); then
        printf 'Dry run: start Ornith services in dependency order\n'
        print_command launchctl enable "$(service_target "$LLAMA_LABEL")"
        print_command launchctl bootstrap "$LAUNCH_DOMAIN" "$LLAMA_PLIST"
        printf 'wait for %s\n' "$LLAMA_HEALTH_URL"
        print_command launchctl enable "$(service_target "$BRIDGE_LABEL")"
        print_command launchctl bootstrap "$LAUNCH_DOMAIN" "$BRIDGE_PLIST"
        printf 'wait for %s\n' "$BRIDGE_MODELS_URL"
        return 0
    fi

    [[ -f "$LLAMA_PLIST" ]] || { printf 'Missing plist: %s\n' "$LLAMA_PLIST" >&2; return 1; }
    [[ -f "$BRIDGE_PLIST" ]] || { printf 'Missing plist: %s\n' "$BRIDGE_PLIST" >&2; return 1; }

    printf 'Starting llama.cpp service...\n'
    enable_service "$LLAMA_LABEL" "$LLAMA_PLIST"
    if ! wait_for_url "$LLAMA_HEALTH_URL" 200 180; then
        printf 'llama.cpp did not become healthy; bridge was not started.\n' >&2
        status
        return 1
    fi

    printf 'Starting Gemini compatibility bridge...\n'
    enable_service "$BRIDGE_LABEL" "$BRIDGE_PLIST"
    if ! wait_for_url "$BRIDGE_MODELS_URL" 401 30; then
        printf 'Gemini bridge did not answer on port 7872.\n' >&2
        status
        return 1
    fi

    status
}

stop() {
    if ((DRY_RUN)); then
        printf 'Dry run: stop Ornith services in reverse dependency order\n'
        print_command launchctl disable "$(service_target "$BRIDGE_LABEL")"
        print_command launchctl bootout "$(service_target "$BRIDGE_LABEL")"
        print_command launchctl disable "$(service_target "$LLAMA_LABEL")"
        print_command launchctl bootout "$(service_target "$LLAMA_LABEL")"
        return 0
    fi

    printf 'Stopping Gemini compatibility bridge...\n'
    stop_service "$BRIDGE_LABEL"
    if ! wait_for_stopped "$BRIDGE_LABEL" 7872; then
        printf 'Gemini bridge did not fully stop.\n' >&2
        status
        return 1
    fi
    printf 'Stopping llama.cpp service...\n'
    stop_service "$LLAMA_LABEL"
    if ! wait_for_stopped "$LLAMA_LABEL" 7871; then
        printf 'llama.cpp did not fully stop.\n' >&2
        status
        return 1
    fi
    status
}

restart() {
    stop
    start
}

logs() {
    local log_file
    for log_file in "$LLAMA_LOG" "$BRIDGE_LOG" "$BRIDGE_ERROR_LOG"; do
        printf '\n--- %s ---\n' "$log_file"
        if [[ -f "$log_file" ]]; then
            tail -n 80 "$log_file"
        else
            printf 'not found\n'
        fi
    done
}

test_api() {
    if ((DRY_RUN)); then
        print_command "$NODE_BIN" "$BRIDGE_TEST"
        return 0
    fi

    [[ -x "$NODE_BIN" ]] || { printf 'Node executable not found: %s\n' "$NODE_BIN" >&2; return 1; }
    [[ -f "$BRIDGE_TEST" ]] || { printf 'Bridge test not found: %s\n' "$BRIDGE_TEST" >&2; return 1; }
    "$NODE_BIN" "$BRIDGE_TEST"
}

usage() {
    cat <<EOF
Usage: $(basename "$0") [--dry-run] <start|stop|restart|status|test|logs>

Controls the local Ornith model from its two LaunchAgents:
  OpenAI-compatible llama.cpp API: ${LLAMA_URL}/v1
  Gemini-compatible bridge:        ${BRIDGE_URL}/v1beta

With no command, shows a small menu suitable for double-clicking in Finder.
EOF
}

if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=1
    shift
fi

if [[ "$#" -eq 0 ]]; then
    MENU_MODE=1
    printf 'Ornith local model\n\n'
    printf '1) start\n2) stop\n3) restart\n4) status\n5) test\n6) logs\nq) quit\n\n'
    read -r -p 'Choose an action: ' choice
    case "$choice" in
        1|start) set -- start ;;
        2|stop) set -- stop ;;
        3|restart) set -- restart ;;
        4|status) set -- status ;;
        5|test) set -- test ;;
        6|logs) set -- logs ;;
        q|Q) exit 0 ;;
        *) printf 'Unknown choice: %s\n' "$choice" >&2; exit 2 ;;
    esac
fi

case "$1" in
    start) start ;;
    stop) stop ;;
    restart) restart ;;
    status) status ;;
    test) test_api ;;
    logs) logs ;;
    -h|--help|help) usage ;;
    *) usage; exit 2 ;;
esac

if ((MENU_MODE)); then
    printf '\nPress Return to close...'
    read -r
fi
