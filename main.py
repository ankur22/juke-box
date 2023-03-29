import time
import board
from adafruit_neotrellis.neotrellis import NeoTrellis
import spotify
from prometheus_client import start_http_server
import signal
import sys

# create the i2c object for the trellis
i2c_bus = board.I2C()  # uses board.SCL and board.SDA
#i2c_bus = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

# create the trellis
trellis = NeoTrellis(i2c_bus)

# Set the brightness value (0 to 1.0)
trellis.brightness = 0.1

# Light off
OFF = (0, 0, 0)

colors = [
    (255, 0, 0),       # Red
    (255, 85, 0),      # Orange
    (255, 170, 0),     # Yellow-Orange
    (255, 255, 0),     # Yellow
    (170, 255, 0),     # Yellow-Green
    (85, 255, 0),      # Green
    (0, 255, 0),       # Pure Green
    (0, 255, 85),      # Cyan-Green
    (0, 255, 170),     # Cyan
    (0, 255, 255),     # Pure Cyan
    (0, 170, 255),     # Light Blue
    (0, 85, 255),      # Blue
    (0, 0, 255),       # Pure Blue
    (85, 0, 255),      # Violet
    (170, 0, 255),     # Purple
    (255, 0, 255),     # Magenta
]

sp = spotify.init()
songs = spotify.get_songs(sp)

is_init = True

# this will be called when button events are received
def blink(event):
    # turn the LED on when a rising edge is detected
    if event.edge == NeoTrellis.EDGE_RISING:
        trellis.pixels[event.number] = colors[event.number]
    # turn the LED off when a falling edge is detected
    elif event.edge == NeoTrellis.EDGE_FALLING:
        trellis.pixels[event.number] = OFF
        if is_init == False:
            spotify.play(sp, songs[event.number])


def init():
    for i in range(16):
        # activate rising edge events on all keys
        trellis.activate_key(i, NeoTrellis.EDGE_RISING)
        # activate falling edge events on all keys
        trellis.activate_key(i, NeoTrellis.EDGE_FALLING)
        # set all keys to trigger the blink callback
        trellis.callbacks[i] = blink

        # cycle the LEDs on startup
        trellis.pixels[i] = colors[i]
        time.sleep(0.05)

    for i in range(16):
        trellis.pixels[i] = OFF
        time.sleep(0.05)

def stop():
    for i in range(16):
        j = 15-i
        # activate rising edge events on all keys
        trellis.activate_key(j, NeoTrellis.EDGE_RISING)
        # activate falling edge events on all keys
        trellis.activate_key(j, NeoTrellis.EDGE_FALLING)
        # set all keys to trigger the blink callback
        trellis.callbacks[j] = blink

        # cycle the LEDs on startup
        trellis.pixels[j] = colors[j]
        time.sleep(0.05)

    for i in range(16):
        j = 15-i
        trellis.pixels[j] = OFF
        time.sleep(0.05)

def start():
    while True:
        # call the sync function call any triggered callbacks
        trellis.sync()
        # the trellis can only be read every 17 millisecons or so
        time.sleep(0.02)


def sigterm_handler(_signo, _stack_frame):
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGTERM, sigterm_handler)
    try:
        start_http_server(8000)
        init()
        is_init = False
        start()
    finally:
        stop()
        print("shutting down")
