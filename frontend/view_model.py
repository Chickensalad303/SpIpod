import spotify_manager
import re as re
from functools import lru_cache 

MENU_PAGE_SIZE = 6

# Screen render types
MENU_RENDER_TYPE = 0
NOW_PLAYING_RENDER = 1
SEARCH_RENDER = 2
SETTINGS_RENDER = 3
CONTEXTMENU_RENDER = 4

# Menu line item types
LINE_NORMAL = 0
LINE_HIGHLIGHT = 1
LINE_TITLE = 2

SPOTIPY_ERROR = None
try:
    spotify_manager.refresh_devices()
    # spotify_manager.refresh_data()
except Exception as e:
    print(e)
    msg = e.error
    if "no healthy upstream" in msg.strip():
        print("this error is commonly caused due to spotify's servers being down (or smth similair)")
        # now run class to show error message in the gui
        SPOTIPY_ERROR = msg
    else:
        print("spotipy api error occured:\n", msg)
        SPOTIPY_ERROR = msg


class LineItem():
    def __init__(self, title = "", line_type = LINE_NORMAL, show_arrow = False):
        self.title = title
        self.line_type = line_type
        self.show_arrow = show_arrow

class Rendering():
    def __init__(self, type):
        self.type = type

    def unsubscribe(self):
        pass

class MenuRendering(Rendering):
    def __init__(self, header = "", lines = [], page_start = 0, total_count = 0, checkbox=False):
        super().__init__(MENU_RENDER_TYPE)
        self.lines = lines
        self.header = header
        self.page_start = page_start
        self.total_count = total_count
        self.now_playing = spotify_manager.DATASTORE.now_playing
        self.has_internet = spotify_manager.has_internet
        
        self.checkbox = checkbox


class NowPlayingRendering(Rendering):
    def __init__(self):
        super().__init__(NOW_PLAYING_RENDER)
        self.callback = None
        self.after_id = None

    def subscribe(self, app, callback):
        if callback == self.callback:
            return
        new_callback = self.callback is None
        self.callback = callback
        self.app = app
        if new_callback:
            self.refresh()

    def refresh(self):
        if not self.callback:
            return
        if self.after_id:
            self.app.after_cancel(self.after_id)
        self.callback(spotify_manager.DATASTORE.now_playing)
        self.after_id = self.app.after(500, lambda: self.refresh())

    def unsubscribe(self):
        super().unsubscribe()
        self.callback = None
        self.app = None

class NowPlayingCommand():
    def __init__(self, runnable = lambda:()):
        self.has_run = False
        self.runnable = runnable
    
    def run(self):
        self.has_run = True
        self.runnable()

class SearchRendering(Rendering):
    def __init__(self, query, active_char):
        super().__init__(SEARCH_RENDER)
        self.query = query
        self.active_char = active_char
        self.loading = False
        self.callback = None
        self.results = None

    def get_active_char(self):
        return ' ' if self.active_char == 26 else chr(self.active_char + ord('a'))

    def subscribe(self, app, callback):
        if (callback == self.callback):
            return
        new_callback = self.callback is None
        self.callback = callback
        self.app = app
        if new_callback:
            self.refresh()

    def refresh(self):
        if not self.callback:
            return
        self.callback(self.query, self.get_active_char(), self.loading, self.results)
        self.results = None

    def unsubscribe(self):
        super().unsubscribe()
        self.callback = None
        self.app = None

class SearchPage():
    def __init__(self, previous_page):
        self.header = "Search"
        self.has_sub_page = True
        self.previous_page = previous_page
        self.live_render = SearchRendering("", 0)
        self.is_title = False

    def nav_prev(self):
        self.live_render.query = self.live_render.query[0:-1]
        self.live_render.refresh()

    def nav_next(self):
        if len(self.live_render.query) > 15:
            return
        active_char = ' ' if self.live_render.active_char == 26 \
          else chr(self.live_render.active_char + ord('a')) 
        self.live_render.query += active_char
        self.live_render.refresh()

    def nav_play(self):
        pass

    def nav_up(self):
        self.live_render.active_char += 1
        if (self.live_render.active_char > 26):
            self.live_render.active_char = 0
        self.live_render.refresh()

    def nav_down(self):
        self.live_render.active_char -= 1
        if (self.live_render.active_char < 0):
            self.live_render.active_char = 26
        self.live_render.refresh()

    def run_search(self, query):
        self.live_render.loading = True
        self.live_render.refresh()
        self.live_render.results = spotify_manager.search(query)
        self.live_render.loading = False
        self.live_render.refresh()

    def nav_select(self):
        spotify_manager.run_async(lambda: self.run_search(self.live_render.query))
        return self

    def nav_back(self):
        return self.previous_page

    def render(self):
        return self.live_render

class NowPlayingPage():
    def __init__(self, previous_page, header, command):
        self.has_sub_page = False
        self.previous_page = previous_page
        self.command = command
        self.header = header
        self.live_render = NowPlayingRendering()
        self.is_title = False
        
    
    # this makes it so contextmenu can be openened when nowplayingpage is open
    def nav_context(self):
        playing = spotify_manager.DATASTORE.now_playing
        track = spotify_manager.UserTrack(playing["name"], playing["artist"], playing["album"], playing["track_uri"])
        
        return ContextMenuPage(self, track)
    
    def play_previous(self):
        spotify_manager.play_previous()
        self.live_render.refresh()

    def play_next(self):
        spotify_manager.play_next()
        self.live_render.refresh()

    def toggle_play(self):
        spotify_manager.toggle_play()
        self.live_render.refresh()

    def nav_prev(self):
        spotify_manager.run_async(lambda: self.play_previous()) 

    def nav_next(self):
        spotify_manager.run_async(lambda: self.play_next()) 

    def nav_play(self):
        spotify_manager.run_async(lambda: self.toggle_play()) 

    def nav_up(self):
        pass

    def nav_down(self):
        pass

    def nav_select(self):
        return self

    def nav_back(self):
        return self.previous_page

    def render(self):
        if (not self.command.has_run):
            self.command.run()
        return self.live_render

EMPTY_LINE_ITEM = LineItem()
class MenuPage():
    def __init__(self, header, previous_page, has_sub_page, is_title = False, checkbox=False):
        self.index = 0
        self.page_start = 0
        self.header = header
        self.has_sub_page = has_sub_page
        self.previous_page = previous_page
        self.is_title = is_title
    
        self.checkbox = checkbox

    def switch_page(self, destination, *args):
        if args:
            # print("args",args, "unpacked:", *(args))
            return destination(self.previous_page, *(args))
        return destination(self.previous_page)


    def total_size(self):
        return 0

    def page_at(self, index):
        return None

    def nav_prev(self):
        spotify_manager.run_async(lambda: spotify_manager.play_previous()) 

    def nav_next(self):
        spotify_manager.run_async(lambda: spotify_manager.play_next()) 

    def nav_play(self):
        spotify_manager.run_async(lambda: spotify_manager.toggle_play()) 
    
    def get_index_jump_up(self):
        return 1

    def get_index_jump_down(self):
        return 1

    def nav_up(self):
        jump = self.get_index_jump_up()
        if(self.index >= self.total_size() - jump):
            return
        if (self.index >= self.page_start + MENU_PAGE_SIZE - jump):
            self.page_start = self.page_start + jump
        self.index = self.index + jump

    def nav_down(self):
        jump = self.get_index_jump_down()
        if(self.index <= (jump - 1)):
            return
        if (self.index <= self.page_start + (jump - 1)):
            self.page_start = self.page_start - jump
            if (self.page_start == 1):
                self.page_start = 0
        self.index = self.index - jump

    def nav_select(self):
        return self.page_at(self.index)

    def nav_back(self):
        return self.previous_page

    def render(self):
        lines = []
        total_size = self.total_size()
        for i in range(self.page_start, self.page_start + MENU_PAGE_SIZE):
            if (i < total_size):
                page = self.page_at(i)
                if (page is None) :
                    lines.append(EMPTY_LINE_ITEM)
                else:
                    line_type = LINE_TITLE if page.is_title else \
                        LINE_HIGHLIGHT if i == self.index else LINE_NORMAL
                    lines.append(LineItem(page.header, line_type, page.has_sub_page))
            else:
                lines.append(EMPTY_LINE_ITEM)
        return MenuRendering(lines=lines, header=self.header, page_start=self.index, total_count=total_size, checkbox=self.checkbox)


def get_menu_options_for(data) -> list:
    if data is None:
        return []
    universal_options = [
        {
            "name": "Add to playlist",
            "id": 0
        },
        {
            "name": "Add to queue",
            "id": 1
        },
        {
            "name": "View artist",
            "id": 2
        },
        # {
        #     "name": "Other",
        #     "id":4
        # }
    ]

    if isinstance(data, spotify_manager.UserAlbum):
        # universal_options.append({
        #     "name": "View album",
        #     "id": len(universal_options)
        # })
        universal_options.append({
            "name": "Add to library",
            "id": len(universal_options)
        })

    elif isinstance(data, spotify_manager.UserTrack):
        universal_options.append({
            "name": "View album",
            "id": len(universal_options)
        })
    
    print(len(universal_options), "asas")
    return universal_options

class ContextMenuPage(MenuPage):
    def __init__(self, previous_page, spot_data=None):
        super().__init__(self.get_title(spot_data), previous_page, has_sub_page=True)

        if spot_data is None:
            return
        print("menupage")
        self.spot_data = spot_data
        print(f"{spot_data}\n{spot_data.uri}\n{type(spot_data)}")

        self.context_options = self.get_content()
        self.num_context_options = len(self.context_options)
        # print(self.context_options)

    def get_title(self, data):
        return f"{data}"

    def get_content(self):
        return get_menu_options_for(self.spot_data)


    def total_size(self):
        return self.num_context_options

    def page_at(self, index, spot_data=None):
        # self.spot_data = None
        # if spot_data:
        #     self.spot_data = spot_data
        return SingleContextPage(self.context_options[index], self.spot_data, self)



class SingleContextPage(MenuPage):
    def __init__(self, context, spot_data, previous_page):
        super().__init__(context["name"], previous_page, has_sub_page=False)
        self.current_context = context
        self.current_context_name = self.current_context["name"]
        self.current_context_id = self.current_context["id"]
    
        self.live_render = ContextMenuRendering(item=self.current_context, data=spot_data)
    def render(self):
        # if (not self.command.has_run):
            # self.command.run()
        return self.live_render


class ContextMenuRendering(Rendering):
    def __init__(self, item, data):
        super().__init__(CONTEXTMENU_RENDER)
        self.callback = None
        self.after_id = None
        self.current_page = item
        self.spot_data = data

    def subscribe(self, app, callback):
        if callback == self.callback:
            return
        new_callback = self.callback is None
        self.callback = callback
        self.app = app
        if new_callback:
            self.refresh()
    
    def refresh(self):
        if not self.callback:
            return
        if self.current_page:
            self.callback(self.current_page, self.spot_data)

    def unsubscribe(self):
        super().unsubscribe()
        self.callback = None
        self.app = None


class SettingsPage(MenuPage):
    def __init__(self, previous_page):
        super().__init__(self.get_title(), previous_page, has_sub_page=True)
        self.settings = self.get_content()
        self.num_settings = len(self.settings)

    def get_title(self):
        return "Settings"
    
    def get_content(self):
        return [
                {
                    "name": "Brightness",
                    "id": 0
                },
                {
                    "name": "Restart Raspotify",
                    "id":1
                },
                {
                    "name": "Reboot",
                    "id":2
                },
                {
                    "name": "Poweroff",
                    "id":3
                },
                {
                    "name":"Other",
                    "id":4
                }
            ]
            
    def total_size(self):
        return self.num_settings
    
    def page_at(self, index):
        #command = None
        return SingleSettingPage(self.settings[index], self) #command=command


class SingleSettingPage(MenuPage):
    def __init__(self, setting, previous_page): #command=None
        super().__init__(setting["name"], previous_page, has_sub_page=False)
        self.current_setting = setting
        self.current_setting_name = self.current_setting["name"]
        self.current_setting_id = self.current_setting["id"]

        self.live_render = SettingsRendering(item=self.current_setting)

    def render(self):
        # if (not self.command.has_run):
        #     self.command.run()
        return self.live_render

        


class SettingsRendering(Rendering):
    def __init__(self, item):
        super().__init__(SETTINGS_RENDER)
        self.callback = None
        self.after_id = None
        self.current_page = item
        # print(self.current_page)

    def subscribe(self, app, callback):
        if callback == self.callback:
            return
        new_callback = self.callback is None
        self.callback = callback
        self.app = app
        if new_callback:
            self.refresh()

    def refresh(self):
        if not self.callback:
           return
        if self.current_page:
            self.callback(self.current_page)
        #if self.after_id:
        #    self.app.after_cancel(self.after_id)
        # self.callback(spotify_manager.DATASTORE.now_playing)
        # self.after_id = self.app.after(500, lambda: self.refresh())

    def unsubscribe(self):
        super().unsubscribe()
        self.callback = None
        self.app = None



class ShowsPage(MenuPage):
    def __init__(self, previous_page):
        super().__init__(self.get_title(), previous_page, has_sub_page=True)
        self.shows = self.get_content()
        self.num_shows = len(self.shows)

    def get_title(self):
        return "Podcasts"
    
    def get_content(self):
        return spotify_manager.DATASTORE.getAllSavedShows()

    def total_size(self):
        return self.num_shows

    @lru_cache(maxsize=15)
    def page_at(self, index):
        return SingleShowPage(self.shows[index], self)

class PlaylistsPage(MenuPage):
    def __init__(self, previous_page, checkbox=False, tracks_to_add=[]):
        super().__init__(self.get_title(), previous_page, has_sub_page=True)
        self.playlists = self.get_content()
        self.num_playlists = len(self.playlists)
        
        self.playlists.sort(key=self.get_idx) # sort playlists to keep order as arranged in Spotify library
        
        self.tracks_to_add = []
        if checkbox == True:
            self.checkbox = True
            self.tracks_to_add = tracks_to_add
        
    # this makes it so contextmenu can be openened when this is open
    def nav_context(self):
        print(self.index)
        return ContextMenuPage(self, self.playlists[self.index])
    
    def get_title(self):
        return "Playlists"

    def get_content(self):
        return spotify_manager.DATASTORE.getAllSavedPlaylists()

    def get_idx(self, e): # function to get idx from UserPlaylist for sorting
        if type(e) == spotify_manager.UserPlaylist: # self.playlists also contains albums as it seems and they don't have the idx value
            return e.idx
        else:
            return 0

    def total_size(self):
        return self.num_playlists

    @lru_cache(maxsize=15)
    def page_at(self, index):
        return SinglePlaylistPage(self, self.playlists[index], tracks_to_add=self.tracks_to_add)

class AlbumsPage(PlaylistsPage):
    def __init__(self, previous_page):
        super().__init__(previous_page)

    def get_title(self):
        return "Albums"

    def get_content(self):
        return spotify_manager.DATASTORE.getAllSavedAlbums()

class SearchResultsPage(MenuPage):
    def __init__(self, previous_page, results):
        super().__init__("Search Results", previous_page, has_sub_page=True)
        self.results = results
        tracks, albums, artists = len(results.tracks), len(results.albums), len(results.artists)
        # Add 1 to each count (if > 0) to make room for section header line items 
        self.tracks = tracks + 1 if tracks > 0 else 0
        self.artists = artists + 1 if artists > 0 else 0
        self.albums = albums + 1 if albums > 0 else 0
        self.total_count = self.tracks + self.albums + self.artists
        self.index = 1
        # indices of the section header line items
        self.header_indices = [0, self.tracks, self.artists + self.tracks]

    def total_size(self):
        return self.total_count

    def page_at(self, index):
        if self.tracks > 0 and index == 0:
            return PlaceHolderPage("TRACKS", self, has_sub_page=False, is_title=True)
        elif self.artists > 0 and index == self.header_indices[1]:
            return PlaceHolderPage("ARTISTS", self, has_sub_page=False, is_title=True)
        elif self.albums > 0 and index == self.header_indices[2]:
            return PlaceHolderPage("ALBUMS", self, has_sub_page=False, is_title=True)
        elif self.tracks > 0 and  index < self.header_indices[1]:
            track = self.results.tracks[index - 1]
            command = NowPlayingCommand(lambda: spotify_manager.play_track(track.uri))
            return NowPlayingPage(self, track.title, command)
        elif self.albums > 0 and  index < self.header_indices[2]:
            artist = self.results.artists[index - (self.tracks + 1)]
            command = NowPlayingCommand(lambda: spotify_manager.play_artist(artist.uri))
            return NowPlayingPage(self, artist.name, command)
        else:
            album = self.results.albums[index - (self.artists + self.tracks + 1)]
            tracks = self.results.album_track_map[album.uri]
            return InMemoryPlaylistPage(album, tracks, self)

    def get_index_jump_up(self):
        if self.index + 1 in self.header_indices:
            return 2
        return 1

    def get_index_jump_down(self):
        if self.index - 1 in self.header_indices:
            return 2
        return 1

class NewReleasesPage(PlaylistsPage):
    def __init__(self, previous_page):
        super().__init__(previous_page)

    def get_title(self):
        return "New Releases"

    def get_content(self):
        return spotify_manager.DATASTORE.getAllNewReleases()

class ArtistsPage(MenuPage):
    def __init__(self, previous_page):
        super().__init__("Artists", previous_page, has_sub_page=True)

    def total_size(self):
        return spotify_manager.DATASTORE.getArtistCount()

    def page_at(self, index):
        # play track
        artist = spotify_manager.DATASTORE.getArtist(index)
        command = NowPlayingCommand(lambda: spotify_manager.play_artist(artist.uri))
        return NowPlayingPage(self, artist.name, command)
    
class SingleArtistPage(MenuPage):
    def __init__(self, artistName, previous_page):
        super().__init__(artistName, previous_page, has_sub_page=True)

class SinglePlaylistPage(MenuPage):
    def __init__(self, previous_page, playlist, tracks_to_add=[]):
        # Credit for code to remove emoticons from string: https://stackoverflow.com/a/49986645
        regex_pattern = re.compile(pattern = "["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                            "]+", flags = re.UNICODE)

        super().__init__(regex_pattern.sub(r'',playlist.name), previous_page, has_sub_page=True)
        self.playlist = playlist
        self.tracks = None
        self.tracks_to_add = tracks_to_add
        self.repeat = True

    # this makes it so contextmenu can be openened when this is open
    def nav_context(self):
        return ContextMenuPage(self, self.tracks[self.index])

    def get_tracks(self):
        if self.tracks is None:
            self.tracks = spotify_manager.DATASTORE.getPlaylistTracks(self.playlist.uri)
        return self.tracks

    def total_size(self):
        if self.tracks:
            return len(self.tracks)
        return self.playlist.track_count

    def page_at(self, index):
        # print(self.playlist.uri, "&", self.repeat, len(self.tracks_to_add))
        if self.repeat == True and len(self.tracks_to_add) > 0:
            # add new tracks to playlist on spotifys servers
            spotify_manager.add_to_playlist(self.playlist.uri, self.tracks_to_add)
            # now sync that same playlist to get all tracks from servers
            syncd_tracks = spotify_manager.get_playlist_tracks(self.playlist.uri)
            self.playlist = spotify_manager.UserPlaylist(self.playlist.name, self.playlist.idx, self.playlist.uri, len(syncd_tracks))
            spotify_manager.DATASTORE.setPlaylist(self.playlist, syncd_tracks)
            
            self.repeat = False
        track = self.get_tracks()[index]
        command = NowPlayingCommand(lambda: spotify_manager.play_from_playlist(self.playlist.uri, track.uri, None))
        return NowPlayingPage(self, track.title, command)

class SingleShowPage(MenuPage):
    def __init__(self, show, previous_page):
        super().__init__(show.name, previous_page, has_sub_page=True)
        self.show = show
        self.episodes = None

    def get_episodes(self):
        if self.episodes is None:
            self.episodes = spotify_manager.DATASTORE.getShowEpisodes(self.show.uri)
        return self.episodes

    def total_size(self):
        return self.show.episode_count

    def page_at(self, index):
        episode = self.get_episodes()[index]
        command = NowPlayingCommand(lambda: spotify_manager.play_from_show(self.show.uri, episode.uri, None))
        return NowPlayingPage(self, episode.name, command)

class InMemoryPlaylistPage(SinglePlaylistPage):
    def __init__(self, playlist, tracks, previous_page):
        super().__init__(playlist, previous_page)
        self.tracks = tracks

class SingleTrackPage(MenuPage):
    def __init__(self, track, previous_page, playlist = None, album = None):
        super().__init__(track.title, previous_page, has_sub_page=False)
        self.track = track
        self.playlist = playlist
        self.album = album

    def render(self):
        r = super().render()
        print("render track")
        context_uri = self.playlist.uri if self.playlist else self.album.uri
        spotify_manager.play_from_playlist(context_uri, self.track.uri, None)
        return r

class SingleEpisodePage(MenuPage):
    def __init__(self, episode, previous_page, show = None):
        super().__init__(episode.name, previous_page, has_sub_page=False)
        self.episode = episode
        self.show = show

    def render(self):
        r = super().render()
        print("render episode")
        context_uri = self.show.uri
        spotify_manager.play_from_show(context_uri, self.episode.uri, None)
        return r

class SavedTracksPage(MenuPage):
    def __init__(self, previous_page):
        super().__init__("Saved Tracks", previous_page, has_sub_page=True)

    def total_size(self):
        return spotify_manager.DATASTORE.getSavedTrackCount()

    def page_at(self, index):
        # play track
        return SingleTrackPage(spotify_manager.DATASTORE.getSavedTrack(index), self)

class PlaceHolderPage(MenuPage):
    def __init__(self, header, previous_page, has_sub_page=True, is_title = False, command = None):
        super().__init__(header, previous_page, has_sub_page, is_title)
        self.command = command
        

    # def render(self):
    #     if (not self.command.has_run):
    #         self.command.run()
    #     return self.live_render

class RootPage(MenuPage):
    def __init__(self, previous_page):
        super().__init__("SpIpod", previous_page, has_sub_page=True)
        self.pages = [
            ArtistsPage(self),
            AlbumsPage(self),
            NewReleasesPage(self),
            PlaylistsPage(self),
            ShowsPage(self),
            SearchPage(self),
            SettingsPage(self),
            NowPlayingPage(self, "Now Playing", NowPlayingCommand()),
        ]
        self.index = 0
        self.page_start = 0
    
    def get_pages(self):
        if (not spotify_manager.DATASTORE.now_playing):
            return self.pages[0:-1] #starts at 1, because NowPlayingPage is the first entry in pages array
        return self.pages
    
    def total_size(self):
        return len(self.get_pages())

    def page_at(self, index):
        return self.get_pages()[index]


    
