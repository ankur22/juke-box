import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import random
from prometheus_client import Counter
from datetime import datetime

interaction_total_counter = Counter('raspberrypi_jukebox_total', 'The total number of times juke box has been interacted with', ['method', 'id'])

market = "GB"
is_playing = False
start = datetime.fromtimestamp(0)
living_room_device = None

def init():
    with open("secrets") as file:
        for line in file:
            line = line.rstrip()
            ev = line.split("=")
            os.environ[ev[0]] = ev[1]

    scope = "user-read-playback-state user-modify-playback-state"

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

    global living_room_device

    living_room_device_name = os.environ['LIVING_ROOM_DEVICE_NAME']

    devices = sp.devices()
    for d in devices["devices"]:
        if d["name"] != living_room_device_name:
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

    global market

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
    global market

    cp = sp.current_playback(market=market)

    if "playlist" in current_uri:
        playlist = sp.playlist(playlist_id=current_uri, market=market)
        playlist_songs = playlist["tracks"]["items"]
        index = random.randint(0, len(playlist_songs))
        __control_player(sp, cp, playlist_songs[index]["track"]["uri"])
    else:
        __control_player(sp, cp, current_uri)


def __control_player(sp, cp, current_uri):
    global is_playing
    global living_room_device

    if cp is None or cp["is_playing"] is None:
        if __can_play(is_playing, True) is False:
            interaction_total_counter.labels('ignored', current_uri).inc()
            return
        print("play")
        interaction_total_counter.labels('play', current_uri).inc()
        sp.start_playback(device_id=living_room_device["id"], uris=[current_uri])
        is_playing = True
        return

    same = cp["item"] is not None and cp["item"]["uri"] is not None and cp["item"]["uri"] == current_uri
    if same:
        print("same")
        interaction_total_counter.labels('same', current_uri).inc()
        return

    if __can_play(is_playing, True) is False:
        interaction_total_counter.labels('ignored', current_uri).inc()
        return
    print("play")
    interaction_total_counter.labels('play', current_uri).inc()
    sp.start_playback(device_id=living_room_device["id"], uris=[current_uri])
    is_playing = True


def __can_play(play_is_current_action, want_to_play):
    global start
    global is_playing

    now = datetime.now()
    difference = now - start
    if play_is_current_action is True and want_to_play is True and difference.seconds < 5:
        print("5 secs not passed")
        return False
    
    start = datetime.now()

    return True
