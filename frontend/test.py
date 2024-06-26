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

<<<<<<< HEAD
clientid = "ab89fb3e5529467c91a245ce5b69067c"
clientsecret = "b123ce33e1d04bfaafeefbcad9529414"
redirectURI = "http://localhost:8080/"
=======
from dotenv import load_dotenv
import os

load_dotenv()
clientID = os.getenv("clientID")
clientSecret = os.getenv("clientSecret")
redirectURI = os.getenv("redirectURI")

>>>>>>> d271692d5a9383a3407fa7448905fd0e0ae01d34
# spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        scope=scope, 
        client_id=clientid, client_secret=clientsecret, redirect_uri=redirectURI))

results = sp.current_user_saved_tracks(limit=50, offset=0)
print(results)
