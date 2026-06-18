import time
import threading
import board
from adafruit_neotrellis.neotrellis import NeoTrellis
import spotify
import volume
from prometheus_client import start_http_server
import signal
import sys

i2c_bus = board.I2C()
trellis = NeoTrellis(i2c_bus)
trellis.brightness = 0.1

OFF = (0, 0, 0)

colors = [
    (255, 0, 0),    (255, 85, 0),   (255, 170, 0),  (255, 255, 0),
    (170, 255, 0),  (85, 255, 0),   (0, 255, 0),    (0, 255, 85),
    (0, 255, 170),  (0, 255, 255),  (0, 170, 255),  (0, 85, 255),
    (0, 0, 255),    (85, 0, 255),   (170, 0, 255),  (255, 0, 255),
]

sp = None
songs = []
is_init = True
volume_enabled = False
_VOLUME_POLL_INTERVAL = 0.5
_last_volume_poll = 0.0
_VOLUME_DISPLAY_DURATION = 1.5
_led_volume_until = 0.0
_active_button = None
_is_paused = False

# Clockwise border indices on the 4×4 grid used for the loading spinner.
_SPINNER_BORDER = [0, 1, 2, 3, 7, 11, 15, 14, 13, 12, 8, 4]


def _spinner_loop(stop_event):
    frame = 0
    n = len(_SPINNER_BORDER)
    while not stop_event.is_set():
        for i in range(16):
            trellis.pixels[i] = OFF
        trellis.pixels[_SPINNER_BORDER[frame % n]]       = (255, 255, 255)
        trellis.pixels[_SPINNER_BORDER[(frame - 1) % n]] = (100, 100, 100)
        trellis.pixels[_SPINNER_BORDER[(frame - 2) % n]] = (40, 40, 40)
        frame += 1
        time.sleep(0.1)
    for i in range(16):
        trellis.pixels[i] = OFF


def _dim(color):
    return tuple(max(1, c // 5) for c in color)


def _refresh_leds():
    now = time.monotonic()
    if now < _led_volume_until:
        vol = volume.last_volume()
        lit = round(vol / 100 * 16)
        for i in range(16):
            trellis.pixels[i] = (255, 160, 0) if i < lit else OFF
    else:
        for i in range(16):
            if i == _active_button and not _is_paused:
                trellis.pixels[i] = _dim(colors[i])
            else:
                trellis.pixels[i] = OFF


def blink(event):
    global _active_button, _is_paused
    if event.edge == NeoTrellis.EDGE_RISING:
        trellis.pixels[event.number] = colors[event.number]
    elif event.edge == NeoTrellis.EDGE_FALLING:
        trellis.pixels[event.number] = OFF
        if is_init:
            print(f"Button {event.number} released but still initialising")
            return
        print(f"Button {event.number} released, calling play")
        action = spotify.play(sp, songs[event.number], event.number)
        if action == 'started':
            _active_button = event.number
            _is_paused = False
        elif action == 'paused':
            _is_paused = True
        elif action == 'resumed':
            _is_paused = False
        _refresh_leds()


def init():
    for i in range(16):
        trellis.activate_key(i, NeoTrellis.EDGE_RISING)
        trellis.activate_key(i, NeoTrellis.EDGE_FALLING)
        trellis.callbacks[i] = blink
        trellis.pixels[i] = colors[i]
        time.sleep(0.05)
    for i in range(16):
        trellis.pixels[i] = OFF
        time.sleep(0.05)


def stop():
    for i in range(16):
        j = 15 - i
        trellis.activate_key(j, NeoTrellis.EDGE_RISING)
        trellis.activate_key(j, NeoTrellis.EDGE_FALLING)
        trellis.callbacks[j] = blink
        trellis.pixels[j] = colors[j]
        time.sleep(0.05)
    for i in range(16):
        j = 15 - i
        trellis.pixels[j] = OFF
        time.sleep(0.05)


def start():
    global _last_volume_poll, _led_volume_until
    showing_volume = False
    while True:
        trellis.sync()
        now = time.monotonic()
        if volume_enabled and now - _last_volume_poll >= _VOLUME_POLL_INTERVAL:
            new_vol = volume.update(sp)
            if new_vol is not None:
                _led_volume_until = now + _VOLUME_DISPLAY_DURATION
                _refresh_leds()
            _last_volume_poll = now
        is_showing_volume = now < _led_volume_until
        if showing_volume and not is_showing_volume:
            _refresh_leds()
        showing_volume = is_showing_volume
        time.sleep(0.02)


def sigterm_handler(_signo, _stack_frame):
    sys.exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, sigterm_handler)
    try:
        start_http_server(8000)
        try:
            volume.init()
            volume_enabled = True
        except Exception as e:
            print(f"volume: ADS1115 not found, volume knob disabled ({e})")

        spinner_stop = threading.Event()
        spinner_thread = threading.Thread(
            target=_spinner_loop, args=(spinner_stop,), daemon=True
        )
        spinner_thread.start()

        sp = spotify.init()
        songs = spotify.get_songs(sp)

        spinner_stop.set()
        spinner_thread.join()

        init()
        is_init = False
        start()
    finally:
        stop()
        print("shutting down")
