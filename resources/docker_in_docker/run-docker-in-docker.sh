#!/bin/bash
set -euo pipefail

########################################################################
#
# Docker-in-Docker helper — see echo-block below for details
#
########################################################################

echo
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                           ║"
_ECHO_HEADER="║                Docker-in-Docker Utility — WIPAC Developers                ║"
echo "$_ECHO_HEADER"
echo "║                                                                           ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Purpose:     Launch a privileged outer Docker container that hosts an    ║"
echo "║               inner Docker daemon.                                        ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Details:                                                                 ║"
echo "║   - Accepts a SPACE-SEPARATED list via DIND_INNER_IMAGES_TO_FORWARD of:   ║"
echo "║       • Docker image refs (e.g., repo/name:tag)                           ║"
echo "║       • Or absolute paths to existing .tar files                          ║"
echo "║   - For images, saves (no compression) to a shared cache as .tar          ║"
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
    echo "║    - $(printf '%-69s' "${var}")║"
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
    echo "║        $(printf '%-67s' "$desc")║"
    if [[ "$is_required" == "true" ]]; then
        echo "║    $(printf '%-67s' "${var} [required]")║"
    else
        echo "║    $(printf '%-67s' "${var} [optional]")║"
    fi
}

# Required
print_env_var DIND_OUTER_IMAGE                 true  "image to run as the outer (DIND) container"
print_env_var DIND_NETWORK                     true  "docker network name for the outer container"
print_env_var DIND_INNER_IMAGES_TO_FORWARD     true  "space-separated image refs or absolute .tar paths"

# Optional
print_env_var DIND_FORWARD_ENV_PREFIXES        false "space-separated prefixes to forward"
print_env_var DIND_FORWARD_ENV_VARS            false "space-separated exact var names to forward"
print_env_var DIND_BIND_RO_DIRS                false "space-separated host dirs to bind read-only at same path"
print_env_var DIND_BIND_RW_DIRS                false "space-separated host dirs to bind read-write at same path"
print_env_var DIND_OUTER_CMD                   false "command run inside outer container AFTER docker loads (default: bash)"
print_env_var DIND_CACHE_ROOT                  false "path to store auto-saved image tars (default: ~/.cache/dind)"
print_env_var DIND_HOST_BASE                   false "base path for inner Docker storage"
print_env_var DIND_EXTRA_ARGS                  false "extra args appended to docker run"

echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo

########################################################################
# Ensure Sysbox runtime is active (required for Docker-in-Docker)
########################################################################
if ! systemctl is-active --quiet sysbox; then
    echo "::error::Sysbox runtime is required for Docker-in-Docker but is not active."
    echo "Install via: https://github.com/nestybox/sysbox"
    exit 1
else
    echo "Sysbox runtime (required for Docker-in-Docker) is active."
fi

########################################################################
# Defaults
########################################################################
if [[ -z "${DIND_CACHE_ROOT:-}" ]]; then
    DIND_CACHE_ROOT="$HOME/.cache/dind"
fi
mkdir -p "$DIND_CACHE_ROOT/saved-images"
saved_images_dir="$DIND_CACHE_ROOT/saved-images"

if [[ -z "${DIND_OUTER_CMD:-}" ]]; then
    DIND_OUTER_CMD="bash"
fi

########################################################################
# Resolve images/files into a list of absolute tar paths
########################################################################
_realpath() {
    # portable realpath
    if command -v realpath >/dev/null 2>&1; then
        realpath "$1"
    else
        # best-effort fallback
        python3 - <<'PY'
import os, sys
print(os.path.abspath(sys.argv[1]))
PY
    fi
}

to_save_list=()
absolute_tar_list=()

# Tokenize respecting simple spaces (user supplies space-separated entries)
for token in ${DIND_INNER_IMAGES_TO_FORWARD}; do
    if [[ -f "$token" ]]; then
        # An existing tar file
        absolute_tar_list+=( "$(_realpath "$token")" )
    else
        # Assume docker image ref; will save as .tar into cache
        to_save_list+=( "$token" )
    fi
done

# Save any images to cache as .tar (no compression), lock-protected
saved_tar_list=()
for img in "${to_save_list[@]}"; do
    safe_name="$(echo "$img" | tr '/:' '--')"
    tar_path="$saved_images_dir/${safe_name}.tar"
    lockfile="$tar_path.lock"

    if [[ ! -s "$tar_path" ]]; then
        exec {lockfd}> "$lockfile"
        flock "$lockfd"
        if [[ ! -s "$tar_path" ]]; then
            echo "Saving image '$img' to '$tar_path'..."
            tmp_out="$(mktemp "$tar_path.XXXXXX")"
            docker image inspect "$img" >/dev/null
            docker save -o "$tmp_out" "$img"
            mv -f "$tmp_out" "$tar_path"
        fi
        flock -u "$lockfd"
        rm -f "$lockfile" || true
    fi
    saved_tar_list+=( "$tar_path" )
done

########################################################################
# Prepare host dirs for inner Docker writable layers & temp
########################################################################
if [[ -z "${DIND_HOST_BASE:-}" ]]; then
    if [[ -n "${RUNNER_TEMP:-}" ]]; then
        DIND_HOST_BASE="$RUNNER_TEMP/dind-$(uuidgen)"
    else
        DIND_HOST_BASE="/tmp/dind-$(uuidgen)"
    fi
fi
inner_docker_root="$DIND_HOST_BASE/lib"
inner_docker_tmp="$DIND_HOST_BASE/tmp"
mkdir -p "$inner_docker_root" "$inner_docker_tmp"

########################################################################
# Compute container-visible tar paths and mounts
########################################################################
# All tars saved to cache will be visible under /saved-images/<basename>
container_tar_paths=()
for p in "${saved_tar_list[@]}"; do
    container_tar_paths+=( "/saved-images/$(basename "$p")" )
done
# Pre-supplied absolute tars must be bind-mounted at the same absolute path
for p in "${absolute_tar_list[@]}"; do
    container_tar_paths+=( "$p" )
done

# Build volume flags for pre-supplied absolute tars
abs_tar_volume_flags=()
for p in "${absolute_tar_list[@]}"; do
    abs_tar_volume_flags+=( "-v" "$p:$p:ro" )
done

# Join container tar paths into a single space-separated string for env
FORWARD_TAR_PATHS="${container_tar_paths[*]}"

########################################################################
# Run outer container: load all tars, then exec DIND_OUTER_CMD
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

# shellcheck disable=SC2046
docker run --rm --privileged \
    --network="$DIND_NETWORK" \
    \
    -v "$saved_images_dir:/saved-images:ro" \
    ${abs_tar_volume_flags[@]+"${abs_tar_volume_flags[@]}"} \
    \
    -v "$inner_docker_root:/var/lib/docker" \
    -v "$inner_docker_tmp:$inner_docker_tmp" \
    -e DOCKER_TMPDIR="$inner_docker_tmp" \
    \
    -e FORWARD_TAR_PATHS="$FORWARD_TAR_PATHS" \
    \
    $( \
        for d in ${DIND_BIND_RO_DIRS:-}; do \
            echo -n " -v $d:$d:ro"; \
        done \
    ) \
    $( \
        for d in ${DIND_BIND_RW_DIRS:-}; do \
            echo -n " -v $d:$d"; \
        done \
    ) \
    \
    $( \
        if [[ -n "${DIND_FORWARD_ENV_PREFIXES:-}" ]]; then \
            regex="$(echo "$DIND_FORWARD_ENV_PREFIXES" | sed 's/ \+/|/g')"; \
            env | grep -E "^(${regex})" | cut -d'=' -f1 | sed 's/^/--env /' | tr '\n' ' '; \
        fi \
    ) \
    \
    $( \
        for k in ${DIND_FORWARD_ENV_VARS:-}; do \
            if env | grep -q "^$k="; then echo -n " --env $k"; fi; \
        done \
    ) \
    \
    $( [[ -n "${DIND_EXTRA_ARGS:-}" ]] && echo "$DIND_EXTRA_ARGS" ) \
    \
    "$DIND_OUTER_IMAGE" /bin/bash -c "\
        set -euo pipefail; \
        if [[ -n \"\${FORWARD_TAR_PATHS:-}\" ]]; then \
            for t in \${FORWARD_TAR_PATHS}; do \
                echo \"Loading: \$t\"; \
                docker load -i \"\$t\"; \
            done; \
        else \
            echo '::warning::No tar paths were provided/resolved.'; \
        fi; \
        exec $DIND_OUTER_CMD \
    "

set +x
echo
echo "╔═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═╗"
echo "$_ECHO_HEADER"
echo "║                                                                           ║"
echo "║                 The 'docker run' command (outer container)                ║"
echo "║                      and this utility have concluded.                     ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
