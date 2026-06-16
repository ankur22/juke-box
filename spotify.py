import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import random
import urllib.request
import json
from prometheus_client import Counter
from datetime import datetime

interaction_total_counter = Counter('raspberrypi_jukebox_total', 'The total number of times juke box has been interacted with', ['method', 'id'])

market = "GB"
start = datetime.fromtimestamp(0)
_LIBRESPOT_ZEROCONF_PORT = 34987

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


def _get_local_device_id():
    try:
        url = f"http://127.0.0.1:{_LIBRESPOT_ZEROCONF_PORT}/?action=getInfo"
        with urllib.request.urlopen(url, timeout=2) as r:
            return json.loads(r.read()).get("deviceID")
    except Exception as e:
        print(f"Could not reach local librespot: {e}")
        return None


def play(sp, song: Song):
    print(f"play() called: '{song.name}'")
    if __is_disabled() is False:
        interaction_total_counter.labels('ignored', song.uri).inc()
        print("play() ignored: within 5 second cooldown")
        return

    global market

    device_name = os.environ['LIVING_ROOM_DEVICE_NAME']
    devices = sp.devices()
    print(f"Spotify devices: {[d['name'] for d in devices['devices']]}")
    device = next((d for d in devices["devices"] if d["name"] == device_name), None)
    if device is None:
        print(f"'{device_name}' not in Spotify device list — trying local librespot device ID")
        local_id = _get_local_device_id()
        if local_id is None:
            print(f"Could not get local device ID. Is raspotify running? Select '{device_name}' in Spotify app to activate it.")
            return
        print(f"Using local device ID: {local_id}")
        device = {"id": local_id, "name": device_name}

    offset = 0
    if song.playlist and song.random:
        playlist = sp.playlist(playlist_id=song.uri, market=market)
        playlist_songs = playlist["tracks"]["items"]
        offset = random.randint(0, len(playlist_songs)-1)

    interaction_total_counter.labels('play', song.uri).inc()
    try:
        if song.playlist:
            sp.start_playback(device_id=device["id"], context_uri=song.uri, offset={"position": offset})
        else:
            sp.start_playback(device_id=device["id"], uris=[song.uri])
    except spotipy.exceptions.SpotifyException as e:
        print(f"Spotify API error: {e}")
        print(f"Device '{device_name}' may not be active yet — open Spotify and select it from the Connect menu first.")
        return
    print(f"play: '{song.name}' on '{device_name}'")

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
