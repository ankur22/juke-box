# PiSugar Setup Notes

## Hardware

- **Model:** PiSugar 3
- **I²C addresses detected:**
  - `0x2e` — NeoTrellis
  - `0x57` — PiSugar battery IC (IP5209)
  - `0x68` — PiSugar RTC (DS3231)

---

## Installation

Running on Pi Zero 2 W (aarch64, Raspberry Pi OS Lite 64-bit). The `pi_setup.sh` script
handles this automatically. To install manually:

```bash
# Download the aarch64 release
PISUGAR_VERSION="2.3.2"
wget https://github.com/PiSugar/pisugar-power-manager-rs/releases/download/v${PISUGAR_VERSION}/pisugar_aarch64-unknown-linux-musl.tar.gz -O /tmp/pisugar.tar.gz
mkdir -p /tmp/pisugar && tar -xzf /tmp/pisugar.tar.gz -C /tmp/pisugar/

# Install (run from the extracted directory, -m avoids interactive prompt)
cd /tmp/pisugar/aarch64-unknown-linux-musl/
sudo bash install.sh -m "PiSugar 3" server

# Enable and start
sudo systemctl enable pisugar-server
sudo systemctl start pisugar-server
```

---

## Interacting via terminal

The server listens on a Unix socket at `/tmp/pisugar-server.sock`.

```bash
# Battery status
echo "get battery" | nc -q 1 -U /tmp/pisugar-server.sock
echo "get battery_v" | nc -q 1 -U /tmp/pisugar-server.sock
echo "get battery_i" | nc -q 1 -U /tmp/pisugar-server.sock
echo "get battery_charging" | nc -q 1 -U /tmp/pisugar-server.sock

# Model
echo "get model" | nc -q 1 -U /tmp/pisugar-server.sock

# Safe shutdown
echo "get safe_shutdown_level" | nc -q 1 -U /tmp/pisugar-server.sock
echo "get safe_shutdown_delay" | nc -q 1 -U /tmp/pisugar-server.sock

# Power button
echo "get button_enable long" | nc -q 1 -U /tmp/pisugar-server.sock
```

The `pisugar-server-conf` CLI tool can also be used:

```bash
pisugar-server-conf -c 'get battery'
pisugar-server-conf --help
```

---

## Web UI

The web UI runs on port `8421`. To access it from your Mac via SSH port forwarding:

```bash
ssh -L 8421:localhost:8421 rpi0jukebox@<pi-ip>
```

Then open `http://localhost:8421` in a browser. The tunnel stays open for the duration of the SSH session.
