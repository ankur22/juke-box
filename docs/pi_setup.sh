#!/bin/bash
# Jukebox Pi Zero 2 W setup script.
# Tested on Raspberry Pi OS (64-bit, aarch64) on Pi Zero 2 W.
# Safe to run multiple times.
#
# Before running:
#   1. Place secrets, songs, .cache, and Python files into ~/juke-box/
#   2. Place authorized_keys into ~/.ssh/authorized_keys
#   3. Ensure WiFi is connected

set -e
export DEBIAN_FRONTEND=noninteractive

JUKEBOX_DIR="/home/${USER}/juke-box"
BOOT_CONFIG="/boot/firmware/config.txt"

echo "=== 1. Update package lists ==="
sudo apt update

echo "=== 2. I2C (NeoTrellis + PiSugar) ==="
sudo apt install -y i2c-tools
grep -qF "dtparam=i2c_arm=on" "${BOOT_CONFIG}" || echo "dtparam=i2c_arm=on" | sudo tee -a "${BOOT_CONFIG}"
# Verify after reboot: i2cdetect -y 1
# Expected: 0x2e (NeoTrellis), 0x57 (PiSugar battery), 0x68 (PiSugar RTC)

echo "=== 3. I2S audio (MAX98357A) ==="
if ! grep -qF "dtoverlay=hifiberry-dac" "${BOOT_CONFIG}"; then
    sudo sed -i 's/dtparam=audio=on/dtparam=audio=off/' "${BOOT_CONFIG}" || true
    grep -qF "dtparam=audio=off" "${BOOT_CONFIG}" || echo "dtparam=audio=off" | sudo tee -a "${BOOT_CONFIG}"
    echo "dtoverlay=hifiberry-dac" | sudo tee -a "${BOOT_CONFIG}"
fi
# After reboot: aplay -l  (card 0 = HifiBerry DAC)
# Test:         speaker-test -c 1 -t sine -f 440

echo "=== 4. PiSugar server ==="
if ! command -v pisugar-server &>/dev/null; then
    PISUGAR_VERSION="2.3.2"
    PISUGAR_TMP=$(mktemp -d)
    wget -qO "${PISUGAR_TMP}/pisugar.tar.gz" \
        "https://github.com/PiSugar/pisugar-power-manager-rs/releases/download/v${PISUGAR_VERSION}/pisugar_aarch64-unknown-linux-musl.tar.gz"
    tar -xzf "${PISUGAR_TMP}/pisugar.tar.gz" -C "${PISUGAR_TMP}/"
    cd "${PISUGAR_TMP}/aarch64-unknown-linux-musl"
    sudo bash install.sh -m "PiSugar 3" server
    cd -
    rm -rf "${PISUGAR_TMP}"
fi
sudo systemctl enable pisugar-server
sudo systemctl start pisugar-server
# Web UI: ssh -L 8421:localhost:8421 <user>@<pi-ip> → http://localhost:8421
# Safe shutdown: echo "set safe_shutdown_level 10" | nc -q 1 -U /tmp/pisugar-server.sock
# Shutdown delay: echo "set safe_shutdown_delay 30"  | nc -q 1 -U /tmp/pisugar-server.sock

echo "=== 5. Jukebox Python app ==="
sudo apt install -y python3-venv python3-pip

if [ ! -d "${JUKEBOX_DIR}/env" ]; then
    python3 -m venv "${JUKEBOX_DIR}/env"
fi
"${JUKEBOX_DIR}/env/bin/pip" install --upgrade pip
"${JUKEBOX_DIR}/env/bin/pip" install \
    spotipy \
    prometheus-client \
    adafruit-circuitpython-neotrellis \
    Adafruit-Blinka

sudo tee /etc/systemd/system/juke-box.service > /dev/null <<EOF
[Unit]
Description=Jukebox app (NeoTrellis + Spotify)
After=multi-user.target network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=${JUKEBOX_DIR}
Type=simple
Restart=always
Environment=PYTHONUNBUFFERED=1
ExecStart=${JUKEBOX_DIR}/env/bin/python3 ${JUKEBOX_DIR}/main.py

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable juke-box.service
sudo systemctl restart juke-box.service

echo "=== 6. Raspotify ==="
if ! dpkg -l raspotify &>/dev/null; then
    curl -sL https://dtcooper.github.io/raspotify/install.sh | sh
fi

sudo tee /etc/raspotify/conf > /dev/null <<'EOF'
LIBRESPOT_NAME="Jukebox"
LIBRESPOT_BITRATE="160"
LIBRESPOT_AUTOPLAY="off"
LIBRESPOT_ZEROCONF_PORT="34987"
LIBRESPOT_INITIAL_VOLUME="30"
EOF

sudo systemctl enable raspotify
sudo systemctl restart raspotify

echo "=== 7. Firewall rules ==="
# Flush and rebuild — idempotent.
# Policies stay ACCEPT while rules are added; explicit DROP at the end of each
# chain acts as the default deny. This matches the old Pi's approach and avoids
# locking out the current SSH session mid-rebuild.
sudo iptables -F
sudo iptables -X
sudo iptables -P INPUT   ACCEPT
sudo iptables -P FORWARD ACCEPT
sudo iptables -P OUTPUT  ACCEPT

# INPUT
sudo iptables -A INPUT -i lo -j ACCEPT
sudo iptables -A INPUT -i wlan0 -p udp --sport 53  -m state --state ESTABLISHED -j ACCEPT
sudo iptables -A INPUT -i wlan0 -p tcp --sport 53  -m state --state ESTABLISHED -j ACCEPT
sudo iptables -A INPUT -i wlan0 -p udp --sport 123 -m state --state ESTABLISHED -j ACCEPT
sudo iptables -A INPUT -i wlan0 -p tcp -m multiport --dports 80,443 -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT
sudo iptables -A INPUT -i wlan0 -p tcp -m multiport --sports 80,443 -m conntrack --ctstate ESTABLISHED     -j ACCEPT
sudo iptables -A INPUT -i wlan0 -p icmp -m state --state RELATED,ESTABLISHED -j ACCEPT
sudo iptables -A INPUT -s 192.168.1.0/24 -p tcp --dport 22 -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT
sudo iptables -A INPUT -i wlan0 -p tcp --dport 34987 -j ACCEPT                                    # raspotify Zeroconf
sudo iptables -A INPUT -i wlan0 -p tcp --sport 4070  -m conntrack --ctstate ESTABLISHED -j ACCEPT  # Spotify AP responses
sudo iptables -A INPUT -i wlan0 -p udp --dport 5353  -j ACCEPT                                    # mDNS queries in
sudo iptables -A INPUT -i wlan0 -p udp --sport 5353  -j ACCEPT                                    # mDNS responses
sudo iptables -A INPUT -j DROP

# FORWARD
sudo iptables -A FORWARD -j DROP

# OUTPUT
sudo iptables -A OUTPUT -o lo -j ACCEPT
sudo iptables -A OUTPUT -o wlan0 -p udp --dport 53  -m state --state NEW,ESTABLISHED -j ACCEPT
sudo iptables -A OUTPUT -o wlan0 -p tcp --dport 53  -m state --state NEW,ESTABLISHED -j ACCEPT
sudo iptables -A OUTPUT -o wlan0 -p udp --dport 123 -m state --state NEW,ESTABLISHED -j ACCEPT
sudo iptables -A OUTPUT -o wlan0 -p tcp -m multiport --dports 80,443 -m conntrack --ctstate NEW,ESTABLISHED -j ACCEPT
sudo iptables -A OUTPUT -o wlan0 -p tcp -m multiport --sports 80,443 -m conntrack --ctstate ESTABLISHED     -j ACCEPT
sudo iptables -A OUTPUT -o wlan0 -p icmp -m state --state NEW,RELATED,ESTABLISHED -j ACCEPT
sudo iptables -A OUTPUT -p tcp --sport 22   -m conntrack --ctstate ESTABLISHED -j ACCEPT
sudo iptables -A OUTPUT -p tcp --sport 34987 -m conntrack --ctstate ESTABLISHED -j ACCEPT  # Zeroconf responses
sudo iptables -A OUTPUT -o wlan0 -p tcp --dport 4070 -m state --state NEW,ESTABLISHED -j ACCEPT  # Spotify AP
sudo iptables -A OUTPUT -o wlan0 -p udp --dport 5353 -j ACCEPT  # mDNS (Spotify Connect)
sudo iptables -A OUTPUT -j DROP

sudo iptables-save | sudo tee /etc/iptables.rules

if [ ! -f /etc/systemd/system/iptables-restore.service ]; then
    sudo tee /etc/systemd/system/iptables-restore.service > /dev/null <<'EOF'
[Unit]
Description=Restore iptables rules
Before=network-pre.target
Wants=network-pre.target

[Service]
Type=oneshot
ExecStart=/sbin/iptables-restore /etc/iptables.rules
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl enable iptables-restore.service
fi

echo ""
echo "=== Setup complete — reboot to apply audio and I2C changes ==="
echo ""
echo "Manual steps remaining:"
echo "  1. Reboot, then verify I2C:  i2cdetect -y 1"
echo "  2. Verify audio:             aplay -l && speaker-test -c 1 -t sine -f 440"
echo "  3. Spotify auth (if needed): cd ${JUKEBOX_DIR} && env/bin/python3 login.py"
echo "  4. Check jukebox service:    sudo systemctl status juke-box.service"
echo "  5. Check raspotify:          sudo systemctl status raspotify"
echo "  6. Set LIVING_ROOM_DEVICE_NAME in ${JUKEBOX_DIR}/secrets:"
echo "     'Jukebox' for local speaker, or Alexa device name for Alexa"
