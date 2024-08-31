import spotipy
from spotipy.oauth2 import SpotifyOAuth
from sys import platform
import distro


print(distro.id())

scope = "user-follow-read," \
        "user-library-read," \
        "user-library-modify," \
        "user-modify-playback-state," \
        "user-read-playback-state," \
        "user-read-currently-playing," \
        "app-remote-control," \
        "playlist-read-private," \
        "playlist-read-collaborative," \
        "playlist-modify-public," \
        "playlist-modify-private," \
        "streaming"

from dotenv import load_dotenv
import os

load_dotenv()
clientID = os.getenv("clientID")
clientSecret = os.getenv("clientSecret")
redirectURI = os.getenv("redirectURI")

# spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        scope=scope, 
        client_id=clientID, client_secret=clientSecret, redirect_uri=redirectURI))

d = sp.devices()
results = sp.current_user_saved_tracks(limit=50, offset=0)
print(d)
