#!/bin/bash
set -euo pipefail

########################################################################
# Apptainer Installation Script
#
# Installs Apptainer from source along with dependencies
# following the official installation guide:
# https://github.com/apptainer/apptainer/blob/main/INSTALL.md
#
# Required flag:
#   --sif yes|no   Install squashfuse (needed for running .sif files directly)
########################################################################

APPTAINER_VERSION="v1.3.2"
INSTALL_SQUASHFUSE=false

# Parse args
if [[ $# -ne 2 || "$1" != "--sif" ]]; then
    echo "::error::Missing or invalid arguments."
    echo "Usage: $0 --sif yes|no"
    exit 1
fi

case "$2" in
    yes)
        INSTALL_SQUASHFUSE=true
        ;;
    no)
        INSTALL_SQUASHFUSE=false
        ;;
    *)
        echo "::error::Invalid value for --sif: $2"
        echo "Usage: $0 --sif yes|no"
        exit 1
        ;;
esac

echo
echo "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓"
echo "┃                                                                           ┃"
_ECHO_HEADER="┃               Apptainer Install Utility — WIPAC Developers                ┃"
echo "$_ECHO_HEADER"
echo "┃                                                                           ┃"
echo "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫"
echo "┃  Host System Info:                                                        ┃"
echo "┃    - Host:      $(printf '%-58s' "$(hostname)")┃"
echo "┃    - User:      $(printf '%-58s' "$(whoami)")┃"
echo "┃    - Kernel:    $(printf '%-58s' "$(uname -r)")┃"
echo "┃    - Platform:  $(printf '%-58s' "$(uname -s) $(uname -m)")┃"
echo "┃    - OS:        $(printf '%-58s' "$(lsb_release -ds 2>/dev/null || echo 'Unknown OS')")┃"
echo "┃    - Timestamp: $(printf '%-58s' "$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")")┃"
echo "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫"
echo "┃  This script will:                                                        ┃"
echo "┃   - Install all required Apptainer build dependencies                     ┃"
echo "┃   - Clone Apptainer from GitHub and build version $(printf '%-24s' "$APPTAINER_VERSION")┃"
if [[ "$INSTALL_SQUASHFUSE" == true ]]; then
    echo "┃   - Install squashfuse for running .sif files (--sif yes)                 ┃"
else
    echo "┃   - Skip squashfuse installation (--sif no)                               ┃"
fi
echo "┃   - Install AppArmor profile (Ubuntu 23.10+ only)                         ┃"
echo "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
echo

set -x

########################################################################
# Install Apptainer build dependencies
########################################################################
if [[ $(sudo find /var/lib/apt/lists -type f -mtime -1 | wc -l) -eq 0 ]]; then
    sudo apt-get update
fi
sudo apt-get install -y \
    build-essential \
    libseccomp-dev \
    pkg-config \
    uidmap \
    squashfs-tools \
    fakeroot \
    cryptsetup \
    tzdata \
    dh-apparmor \
    curl wget git

########################################################################
# Clone and build Apptainer
########################################################################
git clone https://github.com/apptainer/apptainer.git
cd apptainer
git checkout "$APPTAINER_VERSION"
./mconfig
cd $(/bin/pwd)/builddir
make
sudo make install
apptainer --version

########################################################################
# Add AppArmor profile (Ubuntu 23.10+)
########################################################################
sudo tee /etc/apparmor.d/apptainer << 'EOF'
# Permit unprivileged user namespace creation for apptainer starter
abi <abi/4.0>,
include <tunables/global>
profile apptainer /usr/local/libexec/apptainer/bin/starter{,-suid}
    flags=(unconfined) {
        userns,
        # Site-specific additions and overrides. See local/README for details.
        include if exists <local/apptainer>
    }
EOF
sudo systemctl reload apparmor

########################################################################
# Optionally install squashfuse (required for running .sif directly)
########################################################################
if [[ "$INSTALL_SQUASHFUSE" == true ]]; then
    sudo apt-get install -y squashfuse
fi

set +x
echo
echo "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓"
echo "$_ECHO_HEADER"
echo "┃                            Installation Done.                             ┃"
echo "┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫"
echo "┃  Version:    $(printf '%-61s' "$(apptainer --version 2>/dev/null || echo 'installed')")┃"
echo "┃  Location:   $(printf '%-61s' "$(command -v apptainer 2>/dev/null || echo '/usr/local/bin/apptainer')")┃"
if [[ "$INSTALL_SQUASHFUSE" == true ]]; then
    echo "┃  squashfuse: $(printf '%-61s' "installed (--sif yes)")┃"
else
    echo "┃  squashfuse: $(printf '%-61s' "skipped (--sif no)")┃"
fi
echo "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
