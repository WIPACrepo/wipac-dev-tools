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
echo "║   - Mounts host dirs for inner Docker (/var/lib/docker and temp)          ║"
echo "║   - Forwards selected env vars into the outer container                   ║"
echo "║   - Mounts specified RO/RW paths                                          ║"
echo "║   - Accepts a SPACE-SEPARATED list via DIND_INNER_IMAGES_TO_FORWARD of:   ║"
echo "║       • Docker image refs (e.g., repo/name:tag)                           ║"
echo "║       • Or absolute paths to existing .tar files                          ║"
echo "║   - For images, saves (no compression) to a shared cache as .tar          ║"
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
print_env_var DIND_OUTER_IMAGE                 true  "image to run as the outer (DIND) container"
print_env_var DIND_NETWORK                     true  "docker network name for the outer container"

# Optional
echo "║  [Optional]                                                               ║"
print_env_var DIND_INNER_IMAGES_TO_FORWARD     false "space-separated image refs (or absolute .tar paths to mv)"
print_env_var DIND_FORWARD_ENV_PREFIXES        false "space-separated prefixes to forward"
print_env_var DIND_FORWARD_ENV_VARS            false "space-separated exact var names to forward"
print_env_var DIND_BIND_RO_DIRS                false "space-separated host dirs to bind read-only at same path"
print_env_var DIND_BIND_RW_DIRS                false "space-separated host dirs to bind read-write at same path"
print_env_var DIND_CACHE_ROOT                  false "path to store auto-saved image tars (default: ~/.cache/dind)"
print_env_var DIND_HOST_BASE                   false "base path for inner Docker storage"
print_env_var DIND_EXTRA_ARGS                  false "extra args appended to docker run"

# Conditionally Required
echo "║  [Conditionally Required — only if 'DIND_INNER_IMAGES_TO_FORWARD' is set] ║"
print_env_var DIND_OUTER_CMD                   false "command run inside outer container AFTER docker loads"

echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo

# Policy: images → require command; otherwise run image defaults
if [[ -n "${DIND_INNER_IMAGES_TO_FORWARD:-}" && -z "${DIND_OUTER_CMD:-}" ]]; then
    echo "::error::When DIND_INNER_IMAGES_TO_FORWARD is set, you must also set DIND_OUTER_CMD (the command to run after images are loaded)."
    exit 1
fi

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
saved_images_dir="$DIND_CACHE_ROOT/saved-images"
mkdir -p "$saved_images_dir"

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
# inner images: resolve tokens → stage/save into single cache dir
# - All files end up directly under $saved_images_dir
# - If a file with the same name already exists there → ERROR
########################################################################

stage_tar_file() {
    local src="$1"
    local dest
    local lockfile
    local tmp

    dest="$saved_images_dir/$(basename "$src")"
    lockfile="${dest}.lock"
    tmp="${dest}.part.$$"

    echo "Staging tar '$src' to '$dest'..."

    # Exclusive lock for this basename — multiproc safe
    exec {lockfd}> "$lockfile"
    flock "$lockfd"
    if [[ -e "$dest" ]]; then
        echo "::error::basename conflict: '$dest' already exists; cannot stage '$src'"
        flock -u "$lockfd"
        rm -f "$lockfile" || true
        exit 1
    else
        # Atomic finalize — mv it!
        mv -f "$tmp" "$dest"
        flock -u "$lockfd"
        rm -f "$lockfile" || true
    fi
}


tarify_image_then_stage() {
    local img="$1"
    local safe_name tar_path lockfile tmp_out
    safe_name="$(echo "$img" | tr '/:' '--')"
    tar_path="$saved_images_dir/${safe_name}.tar"
    lockfile="$tar_path.lock"

    echo "Saving image '$img' to '$tar_path'..."

    if [[ -e "$tar_path" ]]; then
        echo "::error::basename conflict: '$tar_path' already exists; cannot save image '$img'"
        exit 1
    fi

    exec {lockfd}> "$lockfile"
    flock "$lockfd"
    if [[ ! -s "$tar_path" ]]; then

        # Verify image exists before trying to save
        if ! docker image inspect "$img" >/dev/null 2>&1; then
            echo "::error::'$img' is not a valid local image (docker image inspect failed)"
            flock -u "$lockfd"
            rm -f "$lockfile" || true
            exit 1
        fi

        tmp_out="$(mktemp "$tar_path.XXXXXX")"
        if ! docker save -o "$tmp_out" "$img" >/dev/null 2>&1; then
            echo "::error::Failed to save image '$img' to tarball."
            rm -f "$tmp_out" "$lockfile" || true
            flock -u "$lockfd"
            exit 1
        fi

        [[ -s "$tmp_out" ]] || { echo "::error::empty tar produced for $img"; rm -f "$tmp_out" "$lockfile"; flock -u "$lockfd"; exit 1; }
        mv -f "$tmp_out" "$tar_path"
    else
        echo "> ok: image '$img' already exists at '$tar_path'."
    fi
    flock -u "$lockfd"
    rm -f "$lockfile" || true
}

if [[ -n "${DIND_INNER_IMAGES_TO_FORWARD:-}" ]]; then
    for token in ${DIND_INNER_IMAGES_TO_FORWARD}; do
        if [[ -f "$token" ]]; then
            # file must be a .tar file
            if [[ "$token" != *.tar ]]; then
                echo "::error::'$token' (file from 'DIND_INNER_IMAGES_TO_FORWARD') must be either a .tar file or docker image."
                exit 1
            else
                time stage_tar_file "$(realpath "$token")"
            fi
        else
            # assume this is a docker image
            time tarify_image_then_stage "$token"
        fi
    done
fi

# Build the in-container loader command — only if forwarding was requested
if [[ -n "${DIND_INNER_IMAGES_TO_FORWARD:-}" ]]; then
    if find "$saved_images_dir" -maxdepth 1 -type f -name "*.tar" -print -quit | grep -q .; then
        DIND_INNER_LOAD_CMD='for f in /saved-images/*.tar; do [[ -e "$f" ]] || break; echo "Loading: $f"; time docker load -i "$f"; done'
    else
        DIND_INNER_LOAD_CMD=""
    fi
else
    DIND_INNER_LOAD_CMD=""
fi

########################################################################
# Sanity: ensure outer image exists locally (clear error early)
########################################################################
if ! docker image inspect "$DIND_OUTER_IMAGE" >/dev/null 2>&1; then
    echo "::error::Outer image '$DIND_OUTER_IMAGE' not found locally."
    exit 1
fi

########################################################################
# Run outer container: load images (if any), then exec user command
########################################################################

_CMD=""
if [[ -n "${DIND_INNER_LOAD_CMD:-}" ]]; then
    # loader requires a user command per policy
    if [[ -z "${DIND_OUTER_CMD:-}" ]]; then
        # this was technically check on script start up by 'DIND_INNER_IMAGES_TO_FORWARD' but just in case...
        echo "::error::Images were staged to load, but DIND_OUTER_CMD is empty."
        exit 2
    else
        _CMD="/bin/bash -c 'set -euo pipefail; ${DIND_INNER_LOAD_CMD}; exec ${DIND_OUTER_CMD}'"
    fi
elif [[ -n "${DIND_OUTER_CMD:-}" ]]; then
    # only custom command
    _CMD="/bin/bash -c 'set -euo pipefail; exec ${DIND_OUTER_CMD}'"
else
    # no loader, no user command → let Docker run the image default
    _CMD=""
fi


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
    \
    -v "$inner_docker_root:/var/lib/docker" \
    -v "$inner_docker_tmp:$inner_docker_tmp" \
    -e DOCKER_TMPDIR="$inner_docker_tmp" \
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
    "$DIND_OUTER_IMAGE" ${_CMD}

set +x
echo
echo "╔═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═ ═╗"
echo "$_ECHO_HEADER"
echo "║                                                                           ║"
echo "║                 The 'docker run' command (outer container)                ║"
echo "║                      and this utility have concluded.                     ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
