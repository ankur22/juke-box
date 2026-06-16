# Juke-Box

A Raspberry Pi Zero 2 W toddler music player. Pressing one of 16 NeoTrellis buttons starts the corresponding Spotify playlist through a built-in speaker via Spotify Connect.

## Hardware

| Component | Part |
|---|---|
| SBC | Raspberry Pi Zero 2 W |
| Buttons | Adafruit NeoTrellis 4×4 (I²C, 0x2e) |
| Battery / UPS | PiSugar 3 |
| Amp | MAX98357A I²S mono amp (GPIO18/19/21) |
| Speaker | Mono speaker, 4Ω / 3W |

## Pi setup

Run `docs/pi_setup.sh` on a fresh **Raspberry Pi OS Lite 64-bit** (aarch64) install. The script is idempotent and configures:

- I²C (NeoTrellis + PiSugar)
- I²S audio (`hifiberry-dac` overlay for MAX98357A)
- PiSugar 3 server
- Python virtualenv + dependencies
- `juke-box.service` (systemd)
- `raspotify` (Spotify Connect via librespot)
- Firewall rules (iptables, persisted via `iptables-restore.service`)

**Before running the script:**
1. Place `secrets`, `songs`, and `.cache` into `~/juke-box/`
2. Place your SSH public key into `~/.ssh/authorized_keys`
3. Ensure WiFi is connected

## Configuration

### `secrets` file

```
SPOTIPY_CLIENT_ID=<from Spotify developer dashboard>
SPOTIPY_CLIENT_SECRET=<from Spotify developer dashboard>
SPOTIPY_REDIRECT_URI=<redirect URI registered in dashboard>
LIVING_ROOM_DEVICE_NAME=Jukebox
```

`LIVING_ROOM_DEVICE_NAME` must match the `LIBRESPOT_NAME` set in `/etc/raspotify/conf` (default: `Jukebox`). Set it to an Alexa device name to route audio there instead.

### `songs` file

16 lines, one per button (button 0 = line 1, button 15 = line 16). Format:

```
Label=random=spotify:playlist:<id>
Label=sequence=spotify:track:<id>
```

`random` shuffles the playlist to a random offset on each press; `sequence` plays from the beginning.

## First-time Spotify Connect setup

> **Critical: raspotify and the Python app must use the same Spotify account.**
>
> If raspotify authenticates with a different account than the one in `.cache`, the device will
> never appear in `sp.devices()` and button presses will silently fail.

1. Clear any cached credentials from a previous or wrong account:
   ```bash
   sudo rm -f /var/lib/raspotify/credentials.json
   sudo systemctl restart raspotify
   ```
2. Open the Spotify app **logged in as the same account used to generate `.cache`**.
3. Tap the Connect / speaker icon → select **Jukebox**.
4. Play any track briefly. librespot will save credentials for this account to `/var/lib/raspotify/credentials.json`.
5. From this point, raspotify auto-connects on boot and `Jukebox` appears in the Spotify API device list immediately.

If a button press logs `'Jukebox' not in Spotify device list`, the accounts are mismatched or librespot hasn't connected yet — repeat from step 1.

## Generating the `.cache` file (first time only)

The OAuth flow requires a browser. Do this on a machine with a GUI, then copy `.cache` to the Pi.

```bash
source env/bin/activate
python login.py
# Browser opens for OAuth. After login, .cache is written.
# scp .cache rpi0jukebox@<pi-ip>:~/juke-box/.cache
```

## Service management

```bash
sudo systemctl status juke-box.service
sudo journalctl -u juke-box.service -f
sudo systemctl restart juke-box.service
```

## Prometheus metrics

The service exposes metrics on port `8000`. Add to your Grafana Agent config under `metrics → configs`:

```yaml
- name: jukebox
  scrape_configs:
    - job_name: jukebox
      static_configs:
        - targets: ['<pi-ip>:8000']
  remote_write:
    - url: <prom-remote-url>
      basic_auth:
        username: <username>
        password: <password>
```
