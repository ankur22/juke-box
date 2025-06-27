import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os

market = "GB"

with open("secrets") as file:
    for line in file:
        line = line.rstrip()
        ev = line.split("=")
        os.environ[ev[0]] = ev[1]

scope = "user-read-playback-state user-modify-playback-state"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

# Validate that devices are found

living_room_device_name = os.environ['LIVING_ROOM_DEVICE_NAME']

devices = sp.devices()
for d in devices["devices"]:
    if d["name"] != living_room_device_name:
        continue
    living_room_device = d
    break

# Validate that the playlist is found

playlist_id = "spotify:playlist:6MYruyWvm5yqiqyvIwnEAa"

playlist = sp.playlist(playlist_id=playlist_id)
print(playlist['name'])
