# Juke-Box

Uses NeoTrellis and Spotify to help create a simple Juke-Box.

Create a `secrets` file where the format should look like this:

```
SPOTIPY_CLIENT_ID=<enter client id here>
SPOTIPY_CLIENT_SECRET=<enter client secret here>
SPOTIPY_REDIRECT_URI=<enter redirect url here>
LIVING_ROOM_DEVICE_NAME=<enter the living room device name here>
```

Create a `songs` file where the format should look like this with 16 songs:

```
The Big Ship Sails on the Ally Ally Oh=spotify:track:4yfOLQspU8ELGOjWeck8oN
...
```

## Login

You'll need to login to spotify, or copy the .cache file from an existing install. I did it on a system with a GUI so that when there is no `.cache` file present it will open up chrome to allow you to login.

1. `source env/bin/activate`
2. `pip install spotipy`
3. `python login.py`
4. Login via the web.
5. Now you should have a `.cache` file.

## Dependencies

Needs python 3.10+.

Install all the dependencies that are in requirements.txt when logged in as root.

`pip install -r /path/to/requirements.txt`

### Playlists

They need to be created by someone, not [algorithmically generated](https://community.spotify.com/t5/Spotify-for-Developers/Extension-on-endpoint-quot-Get-Playlist-quot-for-Spotify-owned/td-p/6550856).


## Create a service

```bash
[Unit]
Description=This is the juke box app that works with NeoTrellis
After=multi-user.target

[Service]
WorkingDirectory=/home/<enter-user-name>/
Type=simple
Restart=always
ExecStart=/usr/bin/python3 /home/<enter-user-name>/main.py

[Install]
WantedBy=multi-user.target
```

Enable the service:

```
sudo systemctl enable juke-box.service
```

Start the service:

```
sudo systemctl start juke-box.service
```

## Setup grafana-agent

To be able to scrap the metrics from this running service, add this under `metrics`->`configs`:

```bash
  - name: service
    scrape_configs:
      - job_name: self-scrape
        static_configs:
          - targets: ['localhost:8000']
    remote_write:
    - basic_auth:
        password: <add-password>
        username: <add-username>
      url: <add-prom-remote-url>
```
