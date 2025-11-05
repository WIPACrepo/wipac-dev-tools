#!/bin/bash
set -euo pipefail

########################################################################
# Apptainer Installation Script
#
# Installs Apptainer from source along with dependencies
# following the official installation guide:
# https://github.com/apptainer/apptainer/blob/main/INSTALL.md
########################################################################

APPTAINER_VERSION="v1.3.2"

echo
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                           ║"
_ECHO_HEADER="║               Apptainer Install Utility — WIPAC Developers                ║"
echo "$_ECHO_HEADER"
echo "║                                                                           ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Host System Info:                                                        ║"
echo "║    - Host:      $(printf '%-58s' "$(hostname)")║"
echo "║    - User:      $(printf '%-58s' "$(whoami)")║"
echo "║    - Kernel:    $(printf '%-58s' "$(uname -r)")║"
echo "║    - Platform:  $(printf '%-58s' "$(uname -s) $(uname -m)")║"
echo "║    - OS:        $(printf '%-58s' "$(lsb_release -ds 2>/dev/null || echo 'Unknown OS')")║"
echo "║    - Timestamp: $(printf '%-58s' "$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")")║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  This script will:                                                        ║"
echo "║   - Install all required Apptainer build dependencies                     ║"
echo "║   - Clone Apptainer from GitHub and build version $(printf '%-24s' "$APPTAINER_VERSION")║"
echo "║   - Install AppArmor profile (Ubuntu 23.10+ only)                         ║"
echo "║   - Install squashfuse for running .sif files                             ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo

set -x

########################################################################
# Install Apptainer build dependencies
########################################################################
sudo apt-get update
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
# Install squashfuse (required for running .sif directly)
########################################################################
sudo apt-get update
sudo apt-get install -y squashfuse

set +x
echo
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "$_ECHO_HEADER"
echo "║                            Installation Done.                             ║"
echo "╠═══════════════════════════════════════════════════════════════════════════╣"
echo "║  Version:   $(printf '%-62s' "$(apptainer --version 2>/dev/null || echo 'installed')")║"
echo "║  Location:  $(printf '%-62s' "$(command -v apptainer 2>/dev/null || echo '/usr/local/bin/apptainer')")║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
