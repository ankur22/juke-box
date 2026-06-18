# Raspberry Pi Toddler Music Player — Project Handover

## 1. Project summary

The project is a physical music player for families with babies and toddlers. The existing prototype is a **Raspberry Pi Zero-based device connected to a 16-button pad**. Each button corresponds to a Spotify playlist. At the moment, pressing a button starts the relevant Spotify playlist on an **Alexa device**.

The intended next version is a portable, self-contained device with:

1. A battery
2. Built-in speaker
3. Offline playback
4. A purpose-built 3D-printed case

The user is considering whether this could become a small sellable product after testing several units with families and receiving positive feedback.

---

## 2. Current prototype

### Current hardware

- Raspberry Pi Zero
- 16-button pad / button grid
- Existing enclosure that fits the buttons but is not purpose-built for the Pi Zero
- Alexa device used as the actual audio output

### Current behaviour

- Each button maps to a Spotify playlist
- The Pi triggers playback of that playlist
- Playback happens on an Alexa device, not locally on the Pi
- Device is currently not battery-powered
- Device currently has no built-in speaker
- Device currently relies on internet access and Spotify/Alexa availability

---

## 3. Desired product direction

The next iteration should behave more like a toddler-friendly standalone jukebox:

- Child presses one of 16 physical buttons
- A corresponding playlist starts immediately
- Device can be carried around the house
- Device does not require a phone during normal use
- Device has its own speaker
- Device has a battery
- It should ideally work offline, at least for some playlists
- Case should be purpose-built, robust, and 3D printed

The target audience is **families with babies and toddlers**.

---

## 4. Important Spotify / Amazon Music / Mighty-style offline conclusion

A key discussion point was whether the device could support Spotify or Amazon Music offline playback like the Mighty player.

### Conclusion

A DIY Raspberry Pi device **cannot realistically or legally replicate Mighty-style Spotify/Amazon offline playback**.

Mighty-style offline playback works because Mighty is an approved partner device. It uses official embedded clients, DRM handling, encrypted offline caches, device-bound keys, subscription validation, and periodic licence check-ins.

For a hobby or small product build:

- Spotify downloaded tracks cannot simply be copied from a phone to another device
- Spotify offline files are encrypted and tied to the official app/device
- Amazon Music offline works similarly with DRM and account/device controls
- Unofficial Spotify/Amazon downloader tools should be avoided
- A sellable product cannot rely on hobby Spotify libraries for commercial hardware functionality

### Practical design implication

The viable architecture is:

- **Online mode:** Spotify Connect / Spotify Web API / existing Alexa integration
- **Offline mode:** local DRM-free audio files stored on the Pi, played directly from local storage

In other words:

- Spotify/Amazon can be used for online streaming/control
- Offline playback should use owned/ripped/purchased DRM-free MP3/FLAC/AAC files
- Local offline playlists can mirror the Spotify playlists conceptually, but not by copying Spotify downloads

---

## 5. Hardware used (as built)

| Category | Part |
|---|---|
| Pi | Raspberry Pi Zero 2 W (aarch64) |
| Battery / UPS | PiSugar 3 |
| Audio amp | MAX98357A I²S mono DAC + amp |
| Speaker | Mono speaker, 4Ω / 3W |
| Buttons | Adafruit NeoTrellis 4×4 (I²C, 0x2e) |

---

## 6. Suggested wiring for mono audio

For a Raspberry Pi Zero 2 W connected to a MAX98357A I²S mono amp:

| Pi pin / GPIO | MAX98357A pin |
|---|---|
| 5V | VIN |
| GND | GND |
| GPIO18 / physical pin 12 | BCLK |
| GPIO19 / physical pin 35 | LRCLK / LRC |
| GPIO21 / physical pin 40 | DIN |

Speaker connects to the amp's `SPK+` and `SPK-` outputs.

If the amp board exposes `SD` or `EN`, it can usually be tied high or left in its default enabled state, depending on the breakout board.

Practical notes:

- Keep speaker wires short
- Twist speaker wires together if possible
- Place speaker in a small sealed chamber in the case for better sound
- Avoid placing the speaker directly against loose internal wires or the battery

---

## 7. Software architecture

### Recommended modes

The device should support two playback modes:

#### Online mode

Use Spotify/Alexa integration when the device has internet.

Possible online approaches:

1. Keep current model: buttons trigger Spotify playlists on an Alexa device
2. Move playback onto the Pi using Spotify Connect, e.g. `raspotify` / `librespot`
3. Use Spotify Web API to start playlists on the chosen playback target

For a product-minded prototype, playing directly on the Pi is cleaner because the device becomes self-contained.

#### Offline mode

Use local files stored on the Pi.

Possible stack:

- MPD for local playback
- `mpc` command-line tool for control
- Local `.m3u` playlists corresponding to button mappings
- Files stored under something like `/music`

Button behaviour:

- If internet is available: play the Spotify playlist
- If internet is unavailable: load and play the local playlist

---

## 8. Example button daemon concept

A Python service can run on boot and listen for button presses.

High-level logic:

```text
on button press:
  determine button index
  check internet availability
  if online:
    start matching Spotify playlist on selected playback device
  else:
    stop MPD
    clear MPD queue
    load matching local playlist
    play
```

This should be installed as a `systemd` service so the device boots straight into jukebox mode without manual intervention.

---

## 9. Raspberry Pi audio setup

For I²S audio, add this to `/boot/config.txt`:

```text
dtparam=audio=off
dtoverlay=hifiberry-dac
```

Then reboot and check the audio device with:

```bash
aplay -l
```

Test mono output with:

```bash
speaker-test -c 1 -t sine -f 440
```

If needed, set the I²S DAC as default in `/etc/asound.conf`:

```text
pcm.!default {
  type plug
  slave.pcm "hw:0,0"
}

ctl.!default {
  type hw
  card 0
}
```

Card numbers may need adjusting depending on what `aplay -l` reports.

---

## 10. Battery / PiSugar notes

PiSugar is a good next step because it avoids having to design custom LiPo charging and power-path circuitry immediately.

Recommended behaviour:

- Enable safe shutdown
- Configure long-press power behaviour
- Configure low-battery shutdown threshold if supported
- Expose the power button through the case
- Leave access to the charging port

Rough battery expectation:

- Pi Zero 2 W with Wi-Fi and audio: roughly 250–350 mA typical
- Mono amp can add peaks depending on volume
- A 5000 mAh battery may give roughly 6–8 hours of moderate playback, but this should be tested with the actual speaker, volume, Wi-Fi mode, and PiSugar battery

---

## 11. 3D printed case direction

A first proper case should include:

- 4×4 button grid on the top/front face
- Speaker grille
- Speaker chamber or pocket
- Pi Zero / PiSugar mount
- Battery space
- Access to charging port
- Access to power button
- Internal wire channels
- Screw-together design using heat-set inserts if possible
- Rounded edges for child/family use
- Strong enough walls for repeated handling

Suggested material:

- PETG for toughness and heat resistance
- PLA is okay for early fit prototypes but less ideal for a product-like device

A starter OpenSCAD file was created earlier:

- `jukebox_mono_case.scad`

A starter BOM CSV was also created:

- `jukebox_bom.csv`

These files are starter artefacts only. The case is not a finished enclosure and will need measurement updates based on the exact speaker, PiSugar version, buttons, and battery.

---

## 12. Product / company / compliance discussion

The user asked whether they should open a company before scaling into a sellable product.

### Practical conclusion

For handing out a few prototypes informally to trusted families for feedback, a company is not strictly required.

Before selling or widely distributing a battery-powered Wi-Fi/Bluetooth consumer device, especially for families with young children, it is sensible to form a company and treat it as a real product.

### Reasons to form a company before scaling

- Limit personal liability
- Hold IP and product assets cleanly
- Sign contracts with suppliers, labs, insurers, or partners
- Obtain product liability insurance
- Look credible to retailers, test labs, and future partners
- Separate business finances from personal finances

### Product risk areas

Because the product is intended around babies/toddlers/families, pay special attention to:

- Battery safety
- Small parts
- Button durability
- Speaker grille safety
- Sharp edges
- Drop resistance
- Charging safety
- Choking hazards
- Cable/cord hazards
- Labelling and instructions

### UK compliance areas likely to matter

For a sellable version in the UK, likely areas include:

- UKCA marking
- Radio Equipment Regulations, because of Wi-Fi/Bluetooth
- EMC testing
- Electrical safety, likely EN 62368-1 style considerations
- RoHS
- WEEE
- Battery producer obligations
- Lithium battery transport requirements, including UN 38.3 documentation from the battery supplier
- Product liability insurance
- Privacy policy / ICO fee if collecting customer data through an app/site

This is not legal advice, but it is a strong signal that selling even a small batch should not be treated like casually selling a 3D print on Etsy.

---

## 13. Suggested staged roadmap

### Stage 1 — Portable technical prototype

Goal: prove that the current jukebox works as a self-contained battery speaker device.

Tasks:

1. Move to Pi Zero 2 W if possible
2. Add PiSugar
3. Add MAX98357A mono amp and speaker
4. Confirm local audio output
5. Keep current button handling
6. Decide whether online playback still targets Alexa or moves to Pi as Spotify Connect target

### Stage 2 — Offline fallback

Goal: prove local offline playback works well.

Tasks:

1. Install MPD
2. Add DRM-free local tracks
3. Create `.m3u` playlists
4. Map each button to local playlist fallback
5. Add internet check
6. Test airplane-mode / no-Wi-Fi behaviour

### Stage 3 — Case prototype

Goal: make it feel like a real object, not a dev board.

Tasks:

1. Measure exact speaker, buttons, PiSugar stack height, charging port location
2. Update OpenSCAD parameters
3. Print rough case in PLA for fit
4. Revise button feel, speaker grille, charging port access
5. Print stronger version in PETG

### Stage 4 — Family testing

Goal: validate whether families actually use it.

Suggested test questions:

- Do toddlers understand the buttons?
- Do parents find it easier than using a phone/Alexa?
- Which playlists/buttons get used most?
- Is the speaker loud enough?
- Is battery life good enough?
- Is charging annoying?
- Is the device robust enough?
- Do parents care about offline playback?
- Would they pay for this?
- What price feels reasonable?

### Stage 5 — Productisation decision

Only after positive testing:

1. Decide whether this is a hobby product, kit, or polished consumer device
2. Decide if Spotify/Alexa is required or optional
3. Decide whether offline local audio is enough
4. Form a company before selling at meaningful scale
5. Start compliance and insurance work
6. Explore manufacturing options beyond hand-built Pi devices

---

## 14. Design questions — answered

1. **PiSugar model:** PiSugar 3.
2. **Pi model:** Pi Zero 2 W (aarch64).
3. **Button pad:** Adafruit NeoTrellis 4×4 (I²C, address 0x2e).
4. **Button wiring:** I²C via NeoTrellis library (not a raw matrix).
5. **Playback target:** Pi itself via raspotify (Spotify Connect). Alexa still works by changing `LIVING_ROOM_DEVICE_NAME` in `secrets`.
6. **Mono vs stereo:** Mono is sufficient for now.
7. **Speaker:** Small mono speaker, 4Ω / 3W.
8. **Battery life:** ~1.5 hours measured (Pi Zero 2 W + PiSugar 3 + NeoTrellis + MAX98357A amp + speaker, WiFi on, Spotify Connect streaming). Tested 2026-06-16.
9. **Offline playback:** Deferred — online Spotify Connect works well enough for now.
10. **Music files:** Playlists configured per-device in the `songs` file.
11. **Product form:** Prototype / hobby project for now.
12. **Price point:** Not yet determined.

## 15. Known operational notes

- **Spotify account must match across raspotify and the Python app.** librespot (raspotify) caches credentials for whichever Spotify account first connects to it via the Spotify app. If those credentials are for a different account than the `.cache` OAuth token used by the Python app, `sp.devices()` will never return the Jukebox device. Fix: `sudo rm /var/lib/raspotify/credentials.json && sudo systemctl restart raspotify`, then reconnect from the Spotify app using the correct account.

- **librespot Zeroconf mode:** The device appears in the Spotify app's Connect menu via mDNS immediately, but only registers with Spotify's cloud API after a client connects. Once credentials are cached in `/var/lib/raspotify/credentials.json`, raspotify auto-connects on every boot.

- **LRCLK wire on MAX98357A:** A faulty or intermittent LRC/LRCLK jumper wire causes the amp to lose sync and output white noise. This is the first thing to check if audio sounds distorted.

---

## 15. Recommended next action

The next concrete build step is:

1. Assemble PiSugar + Pi Zero + MAX98357A + one speaker outside the case
2. Confirm battery-powered local audio playback
3. Keep the current button/Spotify/Alexa logic working
4. Add MPD local playback fallback
5. Only then invest time in a polished case

This avoids spending time on enclosure design before the electronics and playback model are proven.

---

## 16. Existing artefacts from this discussion

Two starter files were previously created:

- `jukebox_bom.csv` — starter bill of materials
- `jukebox_mono_case.scad` — parametric OpenSCAD starter case

This Markdown file is intended as the main handover document for a new agent.
