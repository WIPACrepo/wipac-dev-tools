#!/bin/bash
set -euo pipefail

########################################################################
#
# Docker-outside-of-Docker (DooD) helper — see echo-block below for details
#
########################################################################

echo
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                           ║"
_ECHO_HEADER="║         Docker-outside-of-Docker (DooD) Utility — WIPAC Developers        ║"
echo "$_ECHO_HEADER"
echo "║                                                                           ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Purpose:     Launch a privileged outer Docker container that hosts an    ║"
echo "║               inner Docker daemon.                                        ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Details:                                                                 ║"
echo "║   - Mounts host dirs for inner Docker (/var/lib/docker and temp)          ║"
echo "║   - Forwards selected env vars into the outer container                   ║"
echo "║   - Mounts specified RO/RW paths                                          ║"
echo "║   - Loads ALL requested tars inside the outer container, then runs CMD    ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Host System Info:                                                        ║"
echo "║    - Host:      $(printf '%-58s' "$(hostname)")║"
echo "║    - User:      $(printf '%-58s' "$(whoami)")║"
echo "║    - Kernel:    $(printf '%-58s' "$(uname -r)")║"
echo "║    - Platform:  $(printf '%-58s' "$(uname -s) $(uname -m)")║"
echo "║    - Timestamp: $(printf '%-58s' "$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")")║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Environment Variables:                                                   ║"

print_env_var() {
    local var="$1"
    local is_required="${2:-false}"
    local desc="${3:-}"
    local val="${!var:-}"

    # Fail early for missing required vars
    if [[ "$is_required" == "true" && -z "$val" ]]; then
        echo "::error::'$var' must be set${desc:+ ($desc)}."
        exit 1
    fi

    # Print nicely formatted entry
    # name
    echo "║    - $(printf '%-69s' "${var}")║"
    # value
    if [[ -n "$val" ]]; then
        # strip ANSI codes for length comparison
        local clean
        clean="$(echo -e "$val" | sed 's/\x1b\[[0-9;]*m//g')"
        if (( ${#clean} > 67 )); then
            # if too long, print raw (no right border)
            echo "║        \"$val\""
        else
            echo "║        $(printf '%-67s' "\"$val\"")║"
        fi
    else
        echo "║        $(printf '%-67s' "<unset>")║"
    fi
    # desc
    echo "║        $(printf '%-67s' "$desc")║"
}

# Required
echo "║  [Required]                                                               ║"
print_env_var DOOD_OUTER_IMAGE                 true  "image to run as the outer container"
print_env_var DOOD_NETWORK                     true  "docker network name for the outer container"

# Optional
echo "║  [Optional]                                                               ║"
print_env_var DOOD_FORWARD_ENV_PREFIXES        false "space-separated prefixes to forward"
print_env_var DOOD_FORWARD_ENV_VARS            false "space-separated exact var names to forward"
print_env_var DOOD_BIND_RO_DIRS                false "space-separated host dirs to bind read-only at same path"
print_env_var DOOD_BIND_RW_DIRS                false "space-separated host dirs to bind read-write at same path"
print_env_var DOOD_CACHE_ROOT                  false "path to store auto-saved image tars (default: ~/.cache/dind)"
print_env_var DOOD_HOST_BASE                   false "base path for inner Docker storage"
print_env_var DOOD_EXTRA_ARGS                  false "extra args appended to docker run"

# Conditionally Required
echo "║  [Conditionally Required — only if 'DOOD_INNER_IMAGES_TO_FORWARD' is set] ║"
print_env_var DOOD_OUTER_CMD                   false "command run inside outer container AFTER docker loads"

echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo

########################################################################
# Defaults
########################################################################
if [[ -z "${DOOD_CACHE_ROOT:-}" ]]; then
    DOOD_CACHE_ROOT="$HOME/.cache/dind"
fi
saved_images_dir="$DOOD_CACHE_ROOT/saved-images"
mkdir -p "$saved_images_dir"

########################################################################
# Prepare host dirs for inner Docker writable layers & temp
########################################################################
if [[ -z "${DOOD_HOST_BASE:-}" ]]; then
    _uuid="$(uuidgen 2>/dev/null || date +%s)-$$"
    if [[ -n "${RUNNER_TEMP:-}" ]]; then
        DOOD_HOST_BASE="$RUNNER_TEMP/dind-$_uuid"
    else
        DOOD_HOST_BASE="/tmp/dind-$_uuid"
    fi
fi
inner_docker_root="$DOOD_HOST_BASE/lib"
inner_docker_tmp="$DOOD_HOST_BASE/tmp"
mkdir -p "$inner_docker_root" "$inner_docker_tmp"

########################################################################
# Run outer container
########################################################################

echo
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "$_ECHO_HEADER"
echo "║                                                                           ║"
echo "║                 Executing 'docker run' (outer container).                 ║"
echo "║           The next lines are the live command trace (set -x)...           ║"
echo "╚═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═╝"
echo

set -x  # begin live trace of the docker run command

docker run --rm \
    --network="$DOOD_NETWORK" \
    -v "${DOOD_SOCKET:-"/var/run/docker.sock"}:/var/run/docker.sock" \
    -e DOCKER_HOST="unix:///var/run/docker.sock" \
    \
    $( \
        for d in ${DOOD_BIND_RO_DIRS:-}; do \
            echo -n " -v $d:$d:ro"; \
        done \
    ) \
    $( \
        for d in ${DOOD_BIND_RW_DIRS:-}; do \
            echo -n " -v $d:$d"; \
        done \
    ) \
    \
    $( \
        if [[ -n "${DOOD_FORWARD_ENV_PREFIXES:-}" ]]; then \
            regex="$(echo "$DOOD_FORWARD_ENV_PREFIXES" | sed 's/ \+/|/g')"; \
            env | grep -E "^(${regex})" | cut -d'=' -f1 | sed 's/^/--env /' | tr '\n' ' '; \
        fi \
    ) \
    \
    $( \
        for k in ${DOOD_FORWARD_ENV_VARS:-}; do \
            if env | grep -q "^$k="; then echo -n " --env $k"; fi; \
        done \
    ) \
    \
    $( [[ -n "${DOOD_EXTRA_ARGS:-}" ]] && echo "$DOOD_EXTRA_ARGS" ) \
    \
    "$DOOD_OUTER_IMAGE" $( [[ -n "${DOOD_OUTER_CMD:-}" ]] && echo "${DOOD_OUTER_CMD}" )

set +x

echo
echo "╔═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═╗"
echo "$_ECHO_HEADER"
echo "║                                                                           ║"
echo "║                 The 'docker run' command (outer container)                ║"
echo "║                      and this utility have concluded.                     ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
