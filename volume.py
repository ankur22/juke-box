import spotipy

_channel = None
_last_volume = -1
_DEADBAND = 3      # minimum % change before calling the Spotify API
_VDD = 3.3         # pot supply voltage


def init():
    global _channel
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    _channel = AnalogIn(ads, 0)  # 0 = A0
    print("volume: ADS1115 ready on I2C 0x48")


def _read_percent():
    volts = max(0.0, min(_VDD, _channel.voltage))
    return int(volts / _VDD * 100)


def update(sp):
    global _last_volume
    if _channel is None:
        return
    try:
        vol = _read_percent()
    except Exception as e:
        print(f"volume: ADC read failed: {e}")
        return
    if abs(vol - _last_volume) < _DEADBAND:
        return
    try:
        sp.volume(vol)
        _last_volume = vol
        print(f"volume: {vol}%")
    except spotipy.exceptions.SpotifyException as e:
        print(f"volume: Spotify API error: {e}")
