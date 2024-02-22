import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import random
from prometheus_client import Counter
from datetime import datetime

interaction_total_counter = Counter('raspberrypi_jukebox_total', 'The total number of times juke box has been interacted with', ['method', 'id'])

market = "GB"
start = datetime.fromtimestamp(0)
living_room_device = None

class Song:
  def __init__(self, name, random, uri, playlist):
    self.name = name
    self.random = random
    self.uri = uri
    self.playlist = playlist

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
            ran = ss[1] == "random"
            pl = "playlist" in ss[2]
            songs.append(Song(ss[0], ran, ss[2], pl))

    global market

    for s in songs:
        if s.playlist:
            playlist = sp.playlist(playlist_id=s.uri, market=market)
            print(playlist["name"])
        else:
            track = sp.track(track_id=s.uri)
            print(track["name"])
            for a in track["artists"]:
                print(a["name"])
        print("")
    
    return songs


def play(sp, song: Song):
    if __is_disabled() is False:
        interaction_total_counter.labels('ignored', song.uri).inc()
        return
    
    global market

    offset = 0
    if song.playlist and song.random:
        playlist = sp.playlist(playlist_id=song.uri, market=market)
        playlist_songs = playlist["tracks"]["items"]
        offset = random.randint(0, len(playlist_songs)-1)

    # This doesn't work but left in for now incase we can get it to work again.
    # same = cp["item"] is not None and cp["item"]["uri"] is not None and cp["item"]["uri"] == current_uri
    # if same:
    #     print("same")
    #     interaction_total_counter.labels('same', song.uri).inc()
    #     return

    global living_room_device

    interaction_total_counter.labels('play', song.uri).inc()
    if song.playlist:
        sp.start_playback(device_id=living_room_device["id"], context_uri=song.uri, offset={ "position": offset})
    else:
        sp.start_playback(device_id=living_room_device["id"], uris=[song.uri])
    print("play")

    return


def __is_disabled():
    global start

    now = datetime.now()
    difference = now - start
    if difference.seconds < 5:
        print("5 secs not passed")
        return False
    
    start = datetime.now()

    return True
