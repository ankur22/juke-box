# Jukebox — Next Steps

Six planned improvements, roughly in order of complexity.

---

## 1. Stop / resume toggle

**Behaviour:**
- Button press while that button's song is playing → pause
- Button press again → resume from where it left off
- Button press while a *different* song is playing → start new song from beginning

**Approach:**

Track state in `spotify.py`:

```python
current_button = None   # which button is active
is_playing = False      # playing or paused
```

In `play()`:
1. Call `sp.current_playback()` to get the actual playback state from Spotify.
2. If the same button is pressed and playback is active → `sp.pause_playback(device_id=...)`
3. If the same button is pressed and playback is paused → `sp.start_playback(device_id=...)` (no `uris`/`context_uri` = resume)
4. If a different button is pressed → `sp.start_playback(device_id=..., ...)` as today

**LED feedback:** dim the active button's LED while paused, full brightness while playing. The NeoTrellis allows setting any pixel colour at any time.

**Complexity:** Low — pure Python, no hardware changes.

---

## 2. Hardware volume control (potentiometer)

**Approach:**

The Pi Zero 2 W has no ADC pins, so a dedicated ADC chip is needed.

| Option | Interface | Notes |
|---|---|---|
| ADS1115 | I²C | Preferred — already on the I²C bus; 16-bit, 4-channel |
| MCP3008 | SPI | Requires 4 extra GPIO pins |

**Wiring (ADS1115):**

```
Pi 3.3V  → ADS1115 VDD
Pi GND   → ADS1115 GND
Pi SDA   → ADS1115 SDA   (shared with NeoTrellis + PiSugar)
Pi SCL   → ADS1115 SCL   (shared with NeoTrellis + PiSugar)
Pi 3.3V  → pot end 1
Pi GND   → pot end 2
pot wiper → ADS1115 A0
```

Default I²C address is 0x48 — no conflict with existing devices (0x2e, 0x57, 0x68).

**Python:**

```python
# pip install adafruit-circuitpython-ads1x15
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
chan = AnalogIn(ads, ADS.P0)

def read_volume():
    # 0–65535 → 0–100
    return int(chan.value / 65535 * 100)
```

Poll in the main loop alongside `trellis.sync()`. Apply a dead-band (e.g. only update if value changes by ≥ 2) to prevent noisy ADC readings causing constant Spotify API calls.

Set volume via:
```python
sp.volume(volume_percent, device_id=device_id)
```

**Complexity:** Low–Medium. Hardware change (one I²C chip + pot + 5 wires) + small Python addition.

---

## 3. Small display

**Use cases:**
- Show current song name and artist
- Show playback state (playing / paused)
- Show IP address at boot (useful for connecting to the setup UI — see §4)
- Show "Connecting to Spotify…" during startup

**Recommended display:**

**SSD1306 OLED, 128×64, I²C** — cheap, simple, no extra power rail, shares the existing I²C bus. Typical address: 0x3C.

**Python:**

```bash
pip install luma.oled pillow
```

```python
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont

serial = i2c(port=1, address=0x3C)
device = ssd1306(serial)

def display_now_playing(song_name, artist):
    with canvas(device) as draw:
        draw.text((0, 0),  song_name[:20], fill="white")
        draw.text((0, 16), artist[:20],    fill="white")
```

Update the display from `play()` after a successful `start_playback` call, and from a background poller that calls `sp.current_playback()` every ~5 seconds to keep the display in sync.

**Complexity:** Low–Medium. Hardware change (one I²C chip + 4 wires) + moderate Python addition.

---

## 4. Easy setup (web UI on the Pi)

**Goal:** a parent can set up the jukebox without SSH, by visiting a local web page.

**Recommended approach: Pi-hosted web UI (Flask)**

Accessible at `http://jukebox.local:8080` once the Pi is on WiFi.

**Pages / features:**

| Page | Purpose |
|---|---|
| `/` | Status: connected device, current song, Spotify account |
| `/spotify` | Spotify OAuth: link/unlink account; shows current auth status |
| `/buttons` | Grid of 16 buttons; assign a Spotify playlist or track to each one |
| `/volume` | Set default volume |
| `/system` | Restart service, view logs, firmware version |

**Spotify OAuth flow:**

The Pi's web server handles the redirect URI directly:
1. User visits `/spotify/login` → redirected to `https://accounts.spotify.com/authorize?...&redirect_uri=http://jukebox.local:8080/spotify/callback`
2. User approves in Spotify
3. Spotify redirects to `http://jukebox.local:8080/spotify/callback?code=...`
4. Pi exchanges code for token, writes `.cache`, restarts juke-box.service

This requires the `redirect_uri` in the Spotify developer dashboard to be set to `http://jukebox.local:8080/spotify/callback` (or `http://127.0.0.1:8080/spotify/callback` as a fallback).

**Button assignment:**

The web UI reads/writes the `songs` file. A search box calls the Spotify API to look up playlists by name and fill in the URI automatically.

**WiFi provisioning** is harder (the Pi needs to be on WiFi first to serve the page). Recommended approach for first setup: use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to pre-configure WiFi credentials before flashing the SD card. Subsequent WiFi changes can be done via the web UI once connected.

**Complexity:** High. Requires building a small web application. Could be a standalone project.

---

## 5. Local disk playback

**Goal:** the jukebox works without internet and without Spotify, using MP3/FLAC files stored on the Pi's SD card.

**Recommended approach: MPD (Music Player Daemon)**

MPD is a well-tested background audio player with a simple command-line client (`mpc`).

```bash
sudo apt install mpd mpc
```

Store tracks under `/music/<button-name>/`:
```
/music/01-ants-go-marching/
/music/02-baby-shark/
...
```

Create an `.m3u` playlist per button.

**Python integration:**

```python
import subprocess

def play_local(button_index):
    playlist = f"/music/playlists/{button_index:02d}.m3u"
    subprocess.run(["mpc", "clear"])
    subprocess.run(["mpc", "load", playlist])
    subprocess.run(["mpc", "play"])

def stop_local():
    subprocess.run(["mpc", "stop"])
```

Or use the `python-mpd2` library for a cleaner API.

**Mode selection:**

```python
def play(sp, song, button_index):
    if is_online():
        play_spotify(sp, song)
    else:
        play_local(button_index)
```

`is_online()` can ping a known host (`8.8.8.8`) with a short timeout.

**File management:** load music files via `scp` or through the setup web UI (§4).

**Complexity:** Medium. MPD is straightforward; the main effort is deciding on the file organisation and populating the music library.

---

## 6. Enclosure

**Requirements:**

- 4×4 button grid flush on top face (NeoTrellis is 66×66 mm)
- Speaker grille (speaker ~40–50 mm diameter)
- Screen window (SSD1306 is ~25×13 mm visible area)
- Volume knob cutout
- PiSugar 3 charging port access (USB-C or micro-USB depending on model)
- Power button access (PiSugar 3 physical button)
- Ventilation (Pi Zero 2 W runs warm under load)
- Screw-together or snap-fit design — no exposed fasteners facing the child
- Rounded external edges

**Rough internal stack height:**
- Pi Zero 2 W: 1 mm PCB + 11 mm component clearance
- PiSugar 3: ~8 mm
- NeoTrellis (below buttons): ~12 mm
- Speaker + chamber depth: ~25–35 mm
- Total: allow at least 50–60 mm internal depth

**Recommended material:** PETG for toughness and mild heat resistance (better than PLA for a device left on a shelf in sunlight).

**Starting point:** a parametric OpenSCAD model lets you adjust dimensions as the final speaker, screen, and pot are chosen. Key parameters: `button_grid_size`, `speaker_dia`, `screen_cutout`, `wall_thickness`, `internal_height`.

**Suggested print order:**
1. Lid only (no electronics) — check button grid fit and tolerances
2. Base only — check Pi/PiSugar stack height and port alignment
3. Full assembly — check it feels right in a hand

**Complexity:** Medium–High, depending on how polished the result needs to be. At least 3–4 print iterations expected.

---

## Suggested order of work

| Priority | Item | Why |
|---|---|---|
| 1 | Stop/resume toggle (§1) | Quick win, improves UX immediately |
| 2 | Volume potentiometer (§2) | Low hardware cost, resolves the "no physical volume control" gap |
| 3 | Small display (§3) | Useful for §4 setup flow and everyday "what's playing" feedback |
| 4 | Local disk playback (§5) | Offline fallback; pairs well with §4 |
| 5 | Setup web UI (§4) | Bigger effort; unblocked once §3 and §5 are done |
| 6 | Enclosure (§6) | Do last — finalise hardware first so dimensions are stable |
