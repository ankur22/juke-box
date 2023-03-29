import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import random

market = "GB"

def init():
    with open("secrets") as file:
        for line in file:
            line = line.rstrip()
            ev = line.split("=")
            os.environ[ev[0]] = ev[1]

    scope = "user-read-playback-state user-modify-playback-state"

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

    living_room_device = None

    living_room_device_id = os.environ['LIVING_ROOM_DEVICE_ID']

    devices = sp.devices()
    for d in devices["devices"]:
        if d["id"] != living_room_device_id:
            continue
        living_room_device = d
        break

    if living_room_device is None:
        print("living room device not found with given id")
        exit(1)
    
    return sp


def get_songs(sp):
    songs = []

    with open("songs") as file:
        for line in file:
            line = line.rstrip()
            ss = line.split("=")
            songs.append(ss[1])

    for s in songs:
        if "playlist" in s:
            playlist = sp.playlist(playlist_id=s, market=market)
            print(playlist["name"])
        else:
            track = sp.track(track_id=s)
            print(track["name"])
            for a in track["artists"]:
                print(a["name"])
        print("")
    
    return songs


def play(sp, current_uri):
    cp = sp.current_playback(market=market)

    if "playlist" in current_uri:
        playlist = sp.playlist(playlist_id=current_uri, market=market)
        playlist_songs = playlist["tracks"]["items"]
        index = random.randint(0, len(playlist_songs))
        __control_player(sp, cp, playlist_songs[index]["track"]["uri"])
    else:
        __control_player(sp, cp, current_uri)


def __control_player(sp, cp, current_uri):
    living_room_device_id = os.environ['LIVING_ROOM_DEVICE_ID']

    if cp is None or cp["is_playing"] is None:
        print("playing")
        sp.start_playback(device_id=living_room_device_id, uris=[current_uri])
        return
    
    same = cp["item"] is not None and cp["item"]["uri"] is not None and cp["item"]["uri"] == current_uri

    if cp["is_playing"] is True and same is True:
        print("pausing")
        sp.pause_playback(device_id=living_room_device_id)
        return

    if same:
        print("resuming")
        sp.start_playback(device_id=living_room_device_id, uris=[current_uri], position_ms=cp["progress_ms"])
        return

    print("playing")
    sp.start_playback(device_id=living_room_device_id, uris=[current_uri])

