#!/bin/bash
set -euo pipefail

########################################################################
#
# Docker-outside-of-Docker (DooD) helper — see echo-block below for details
#
########################################################################

echo
echo "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓"
echo "┃                                                                           ┃"
_ECHO_HEADER="┃         Docker-outside-of-Docker (DooD) Utility — WIPAC Developers        ┃"
echo "$_ECHO_HEADER"
echo "┃                                                                           ┃"
echo "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫"
echo "┃  Purpose:     Run a container that talks to the *host* Docker daemon      ┃"
echo "┃               via the mounted socket.                                     ┃"
echo "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫"
echo "┃  Details:                                                                 ┃"
echo "┃   - Shares host daemon with: -v /var/run/docker.sock:/var/run/docker.sock ┃"
echo "┃   - No '--privileged', no Sysbox, no '/var/lib/docker' bind               ┃"
echo "┃   - Forwards selected env vars into the container                         ┃"
echo "┃   - Mounts specified RO/RW host paths at *same paths inside*              ┃"
echo "┃   - If no command is provided, image ENTRYPOINT/CMD is used               ┃"
echo "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫"
echo "┃  Host System Info:                                                        ┃"
echo "┃    - Host:      $(printf '%-58s' "$(hostname)")┃"
echo "┃    - User:      $(printf '%-58s' "$(whoami)")┃"
echo "┃    - Kernel:    $(printf '%-58s' "$(uname -r)")┃"
echo "┃    - Platform:  $(printf '%-58s' "$(uname -s) $(uname -m)")┃"
echo "┃    - Timestamp: $(printf '%-58s' "$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")")┃"
echo "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫"
echo "┃  Environment Variables:                                                   ┃"

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
    echo "┃    - $(printf '%-69s' "${var}")┃"
    # value
    if [[ -n "$val" ]]; then
        # strip ANSI codes for length comparison
        local clean
        clean="$(echo -e "$val" | sed 's/\x1b\[[0-9;]*m//g')"
        if (( ${#clean} > 67 )); then
            # if too long, print raw (no right border)
            echo "┃        \"$val\""
        else
            echo "┃        $(printf '%-67s' "\"$val\"")┃"
        fi
    else
        echo "┃        $(printf '%-67s' "<unset>")┃"
    fi
    # desc
    echo "┃        $(printf '%-67s' "$desc")┃"
}

# Required
echo "┃  [Required]                                                               ┃"
print_env_var DOOD_OUTER_IMAGE                 true  "image to run"

# Optional
echo "┃  [Optional]                                                               ┃"
print_env_var DOOD_OUTER_CMD                   false "command to run inside; if empty, image default is used"
print_env_var DOOD_NETWORK                     false "docker network"
print_env_var DOOD_SOCKET                      false "docker socket path (default: /var/run/docker.sock)"
print_env_var DOOD_FORWARD_ENV_PREFIXES        false "space-separated prefixes to forward"
print_env_var DOOD_FORWARD_ENV_VARS            false "space-separated exact var names to forward"
print_env_var DOOD_BIND_RO_DIRS                false "space-separated host dirs to bind read-only at same path"
print_env_var DOOD_BIND_RW_DIRS                false "space-separated host dirs to bind read-write at same path"
print_env_var DOOD_EXTRA_ARGS                  false "extra args appended to docker run"

echo "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
echo

# validate to-be-mounted directories (host side)
for d in ${DOOD_BIND_RO_DIRS:-} ${DOOD_BIND_RW_DIRS:-}; do
    if [[ "${d:0:1}" != "/" ]]; then
        echo "::error::Bind source must be an absolute path on the host: $d"
        exit 2
    fi
    if [[ ! -d "$d" ]]; then
        echo "::error::Bind source directory does not exist on host: $d"
        exit 2
    fi
done

########################################################################
# Run container using host daemon
########################################################################

echo
echo "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓"
echo "$_ECHO_HEADER"
echo "┃                                                                           ┃"
echo "┃                          Executing 'docker run'.                          ┃"
echo "┃           The next lines are the live command trace (set -x)...           ┃"
echo "┗━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━┛"
echo

set -x  # begin live trace of the docker run command

docker run --rm \
    \
    $( [[ -n "${DOOD_NETWORK:-}" ]] && echo "--network=$DOOD_NETWORK" ) \
    \
    -v "${DOOD_SOCKET:-"/var/run/docker.sock"}:/var/run/docker.sock" \
    -e DOCKER_HOST="unix:///var/run/docker.sock" \
    \
    $( \
        for d in ${DOOD_BIND_RO_DIRS:-}; do
            printf -- " -v %q" "${d}:${d}:ro"
        done \
    ) \
    $( \
        for d in ${DOOD_BIND_RW_DIRS:-}; do
            printf -- " -v %q" "${d}:${d}"
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
    "$DOOD_OUTER_IMAGE" \
    $( [[ -n "${DOOD_OUTER_CMD:-}" ]] && echo "${DOOD_OUTER_CMD}" )

set +x  # end live trace

echo
echo "┏━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━┓"
echo "$_ECHO_HEADER"
echo "┃                                                                           ┃"
echo "┃  The 'docker run' command has finished for image:                         ┃"
echo "┃    $(printf '%-71s' "'$(hostname)'")┃"
echo "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
