# This code is a mess.
# This is me learning Python as I go.
# This is not how I write code for my day job.

import tkinter as tk 
import socket
import json
import time
from datetime import timedelta
from select import select
from tkinter import ttk
from view_model import *
from PIL import ImageTk, Image
from sys import platform
import os
import distro

import subprocess
import pigpio

BACKLIGHT_PIN = 18
ACTIVATE_BRIGHTNESS_SLIDER = False
SLIDER_WHEEL_DATA = None

LARGEFONT =("ChicagoFLF", 90) 
MED_FONT =("ChicagoFLF", 70) 
SCALE = 1
SPOT_GREEN = "#1DB954"
SPOT_BLACK = "#191414"
SPOT_WHITE = "#FFFFFF"

UDP_IP = "127.0.0.1"
UDP_PORT = 9090

DIVIDER_HEIGHT = 3

UP_KEY_CODE = 8255233 if platform == "darwin"  else 116
DOWN_KEY_CODE = 8320768 if platform == "darwin" else 111
LEFT_KEY_CODE = 8124162 if platform == "darwin" else 113
RIGHT_KEY_CODE = 8189699 if platform == "darwin" else 114
PREV_KEY_CODE = 2818092 if platform == "darwin" else 0
NEXT_KEY_CODE = 3080238 if platform == "darwin" else 0
PLAY_KEY_CODE = 3211296 if platform == "darwin" else 36
QUIT_KEY_CODE = 0 if platform == "darwin" else 22

SCREEN_TIMEOUT_SECONDS = 60

wheel_position = -1
last_button = -1

#useful for debugging, like for when using vncviewer  
def onQuitPressed():
    global page, app
    app.destroy()
    

last_interaction = time.time()
screen_on = True

def screen_sleep():
    global screen_on
    screen_on = False
    os.system('xset -display :0 dpms force off')

def screen_wake():
    global screen_on
    screen_on = True
    os.system('xset -display :0 dpms force on')

#i hav no idea if these are the correct/safest ways to do this, but idk
def system_reboot():
    os.system("reboot -h")

def system_poweroff():
    os.system("shutdown -h now")

def system_restart_raspotify():
    os.system("sudo systemctl enable raspotify")
    os.system("sudo systemctl restart raspotify")
    enabled = subprocess.run(["sudo", "systemctl", "is-enabled", "raspotify"], check=True, capture_output=True, text=True).stdout
    active = subprocess.run(["sudo", "systemctl", "is-active", "raspotify"], check=True, capture_output=True, text=True).stdout

    # os.system("sudo systemctl is-enabled raspotify")
    # os.system("sudo systemctl is-active raspotify")
    # print(enabled)
    # print(active)
    if enabled.strip() == "enabled".strip() and active.strip() == "active".strip():
        return True
    return False

#this works on rpi zero 2 W idk aboot the others
def is_rpi():
    active = subprocess.run(["sudo", "uname", "-m"], check=True, capture_output=True, text=True).stdout
    if active.strip() == "armv7l".strip():
        return True
    return False

def system_get_brightness():
    print("is running on rpi:", is_rpi())
    if is_rpi():
        pigpi = pigpio.pi()
        current_sys_brightness = pigpi.get_PWM_dutycycle(BACKLIGHT_PIN)
        return int(current_sys_brightness)
    #dev_brightness_path = r"/sys/class/backlight/amdgpu_bl0/brightness"
    #current_system_brightness = None
    #with open(dev_brightness_path, "r") as file:
    #    current_system_brightness = file.read()
    #    file.close()
    #return int(current_system_brightness)

    
def system_change_brightness(new_val):
    # brightness values ranges from 0 to 255
    #divide 255 into parts of 10 (so, basically in increments of 25.5)
    #must be int

    #set new brightness (this is for my local dev setup)
    #dev_brightness_path = r"/sys/class/backlight/amdgpu_bl0/brightness"
    #val = int(new_val)
    #curr_val = system_get_brightness()
    #print(val, "vs", curr_val)
    
    #here brightness values between 25 - 1024 according to docs, but in test 0-1024 worked too, so idk just assume the range 0-1024
    if is_rpi():
        pigpi = pigpio.pi()
        pigpi.set_PWM_range(BACKLIGHT_PIN, 1024)
        val = int(new_val)
        try:
            current_val = system_get_brightness()
            if val == current_val:
                return False
            pigpi.set_PWM_dutycycle(BACKLIGHT_PIN, val)
        except:
            pigpi.set_PWM_dutycycle(BACKLIGHT_PIN, val)
        #pigpi.stop()
        return True
    return False

    #if val == curr_val:
    #    return False
    #if val >= 0 and val <= 255:
    #    with open(dev_brightness_path, "w") as file:
    #        file.write(f"{val}")
    #        file.close
    #    return True
    #return False


def flattenAlpha(img):
    global SCALE
    [img_w, img_h] = img.size
    #Image.ANTIALIAS replaced by Image.Resampling.LANCZOS in pillow =< 10.0.0 
    img = img.resize((int(img_w * SCALE), int(img_h * SCALE)), Image.ANTIALIAS)


    alpha = img.split()[-1]  # Pull off the alpha layer
    ab = alpha.tobytes()  # Original 8-bit alpha

    checked = []  # Create a new array to store the cleaned up alpha layer bytes

    # Walk through all pixels and set them either to 0 for transparent or 255 for opaque fancy pants
    transparent = 50  # change to suit your tolerance for what is and is not transparent

    p = 0
    for pixel in range(0, len(ab)):
        if ab[pixel] < transparent:
            checked.append(0)  # Transparent
        else:
            checked.append(255)  # Opaque
        p += 1

    mask = Image.frombytes('L', img.size, bytes(checked))

    img.putalpha(mask)

    return img
   
class tkinterApp(tk.Tk): 
      
    # __init__ function for class tkinterApp  
    def __init__(self, *args, **kwargs):  
        global LARGEFONT, MED_FONT, SCALE
        # __init__ function for class Tk 
        tk.Tk.__init__(self, *args, **kwargs)

        # Darwin is macos btw
        if (platform == 'darwin' or distro.id() != "raspbian"):
            self.geometry("320x240")
            SCALE = 0.24
        else:
            self.attributes('-fullscreen', True)
            # originally was divided with 930, for my screen 1000 works better
            SCALE = self.winfo_screenheight() / 1000
            print("Scale of App is: ", SCALE)

        # 72 & 52
        LARGEFONT =("ChicagoFLF", int(72 * SCALE))
        MED_FONT =("ChicagoFLF", int(52 * SCALE))
        # creating a container 
        container = tk.Frame(self)   
        container.pack(side = "top", fill = "both", expand = True)  
   
        container.grid_rowconfigure(0, weight = 1) 
        container.grid_columnconfigure(0, weight = 1) 
   
        # initializing frames to an empty array 
        self.frames = {}   
   
        # iterating through a tuple consisting 
        # of the different page layouts 
        for F in (StartPage, NowPlayingFrame, SearchFrame, SettingsFrame): #SettingsFrame
   
            frame = F(container, self) 
   
            # initializing frame of that object from 
            # startpage, page1, page2 respectively with  
            # for loop 
            self.frames[F] = frame  
   
            frame.grid(row = 0, column = 0, sticky ="nsew") 
   
        self.show_frame(StartPage) 
   
    # to display the current frame passed as 
    # parameter 
    def show_frame(self, cont): 
        frame = self.frames[cont] 
        frame.tkraise() 

# pass font arg, defaults to LARGEFONT
class Marquee(tk.Canvas):
    def __init__(self, parent, text, fontOffset=0, margin=2, borderwidth=0, relief='flat', fps=24):
        tk.Canvas.__init__(self, parent, highlightthickness=0, borderwidth=borderwidth, relief=relief, background=SPOT_BLACK)
        #
        # fontOffset="Large" doesen't get checked cuz it defaults to largefont
        # fontOffset="medium" sets to  mediumfont
        #print((LARGEFONT[0], LARGEFONT[1] - fontOffset))
        #currentFont = LARGEFONT
        currentFont = (LARGEFONT[0], LARGEFONT[1] - fontOffset)
        # print(fontOffset)
        print(currentFont)

        self.fps = fps
        self.margin = margin
        self.borderwidth = borderwidth
        # start by drawing the text off screen, then asking the canvas
        # how much space we need. Use that to compute the initial size
        # of the canvas. 
        self.saved_text = text
        self.text = self.create_text(0, -1000, text=text, font=currentFont, fill=SPOT_GREEN, anchor="w", tags=("text",))
        (x0, y0, x1, y1) = self.bbox("text")
        self.width = (x1 - x0) + (2*margin) + (2*borderwidth)
        self.height = (y1 - y0) + (2*margin) + (2*borderwidth)
        self.configure(width=self.width, height=self.height)
        self.reset = True
        self.pause_ctr = 100
        self.after_id = None
        self.redraw()

    def set_text(self, text):
        if (self.saved_text == text):
            return
        self.saved_text = text
        self.itemconfig(self.text, text=text)
        (x0, y0, x1, y1) = self.bbox("text")
        self.width = (x1 - x0) + (2*self.margin) + (2*self.borderwidth)
        self.height = (y1 - y0) + (2*self.margin) + (2*self.borderwidth)
        self.configure(width=self.width, height=self.height)
        if (self.width > self.winfo_width()):
            self.coords("text", 100, self.winfo_height()/2)
        else:
            self.coords("text", (self.winfo_width() / 2) - (self.width / 2), self.winfo_height()/2)
        self.pause_ctr = 100
        self.reset = True
        self.redraw()

    def redraw(self):
        if self.after_id:
            self.after_cancel(self.after_id)
        (x0, y0, x1, y1) = self.bbox("text")
        win_width = self.winfo_width()
        if win_width < 2:
            pass
        elif self.width < win_width:
            self.coords("text", (win_width / 2) - (self.width / 2), self.winfo_height()/2)
            return 
        elif x1 < 0 or y0 < 0 or self.reset:
            self.reset = False
            self.animating = True
            x0 = 20
            y0 = int(self.winfo_height()/2)
            self.pause_ctr = 100
            self.coords("text", x0, y0)
        elif self.pause_ctr > 0:
            self.pause_ctr = self.pause_ctr - 1
        else:
            self.move("text", -2, 0)
        self.after_id = self.after(int(1000/self.fps), self.redraw)
   
class SearchFrame(tk.Frame): 
    def __init__(self, parent, controller):  
        tk.Frame.__init__(self, parent) 
        self.configure(bg=SPOT_BLACK)
        self.header_label = tk.Label(self, text ="Search", font = LARGEFONT, background=SPOT_BLACK, foreground=SPOT_GREEN) 
        self.header_label.grid(sticky='we', padx=(0, 10))
        self.grid_columnconfigure(0, weight=1)
        divider = tk.Canvas(self)
        divider.configure(bg=SPOT_GREEN, height=DIVIDER_HEIGHT, bd=0, highlightthickness=0, relief='ridge')
        divider.grid(row = 1, column = 0, sticky ="we", pady=(10, int(160 * SCALE)), padx=(10, 30))
        contentFrame = tk.Canvas(self, bg=SPOT_BLACK, highlightthickness=0, relief='ridge')
        contentFrame.grid(row = 2, column = 0, sticky ="nswe")
        self.query_label = tk.Label(contentFrame, text ="", font = LARGEFONT, background=SPOT_BLACK, foreground=SPOT_GREEN) 
        self.letter_label= tk.Label(contentFrame, text ="a", font = LARGEFONT, background=SPOT_GREEN, foreground=SPOT_BLACK) 
        self.query_label.grid(row = 0, column = 0, sticky = "nsw", padx=(120,0))
        self.letter_label.grid(row = 0, column = 1, sticky = "nsw")
        contentFrame.grid_columnconfigure(1, weight=1)
        search_line = tk.Canvas(self)
        search_line.configure(bg=SPOT_GREEN, height=5, bd=0, highlightthickness=0, relief='ridge')
        search_line.grid(row = 3, column = 0, sticky ="we", pady=10, padx=120)
        self.loading_label = tk.Label(self, text ="", font = LARGEFONT, background=SPOT_BLACK, foreground=SPOT_WHITE) 
        self.loading_label.grid(row = 4, column = 0, sticky ="we", pady=(int(100 * SCALE), 0))

    def update_search(self, query, active_char, loading):
        self.query_label.configure(text=query)
        self.letter_label.configure(text=active_char)
        loading_text = "Loading..." if loading else ""
        self.loading_label.configure(text=loading_text)

class SettingsFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.is_raspotify_running = False

        self.configure(bg=SPOT_BLACK)
        self.grid_columnconfigure(0, weight=1)

        divider = tk.Canvas(self)
        divider.configure(bg=SPOT_GREEN, height=DIVIDER_HEIGHT, bd=0, highlightthickness=0, relief="ridge")
        divider.grid(row = 2, column=0, sticky="we", pady=(10, int(160 * SCALE)), padx=(10, 30))

        contentFrame = tk.Canvas(self, bg=SPOT_BLACK, highlightthickness=0, relief="ridge")
        contentFrame.grid(row=1, column=0, sticky="nswe")
        contentFrame.grid_columnconfigure(0, weight=1)        
        # self.header_label = tk.Label(self, text="nan", font=LARGEFONT, background=SPOT_BLACK, foreground=SPOT_GREEN)
        self.header_label = Marquee(contentFrame, text="Non", fontOffset=0)
        self.header_label.grid(sticky="we", padx=(0, 10))

        mainContentFrame = tk.Canvas(self, bg=SPOT_BLACK, highlightthickness=0, relief="ridge")
        mainContentFrame.grid(row=3, column=0, sticky="nswe")
        mainContentFrame.grid_columnconfigure(0, weight=1) 
        self.main_label = Marquee(mainContentFrame, text="No Text", fontOffset=0)
        self.main_label.grid(sticky="we", padx=(0, 10))
        self.main_label2 = Marquee(mainContentFrame, text="No Text", fontOffset=0)
        self.main_label2.grid(sticky="we", padx=(0, 10))


        self.brightnessFrame = tk.Canvas(self, bg=SPOT_BLACK, highlightthickness=0, relief="ridge")
        self.brightnessFrame.grid(row=4, column=0, sticky="nswe")
        self.brightnessFrame.grid_columnconfigure(0, weight=1) 

        self.frame_img = ImageTk.PhotoImage(flattenAlpha(Image.open('prog_frame.png')))
        self.update()
        self.padding_offset = (self.frame_img.width() - self.winfo_width()) / 2 * SCALE
        # self.padding_offset = 25 for this offset im just tryign random shit
        self.padding_offset = (self.winfo_reqwidth() - self.frame_img.width()) / 1.5 * SCALE
        
        print(self.padding_offset, "\n", self.winfo_reqwidth(), self.frame_img.width())


    def update_brightness(self):
        parent_width = self.winfo_width()
        if parent_width > 2:
            # this is straight up copied from NowPlayingFrame, just made interactive
            self.progress_frame = tk.Canvas(self.brightnessFrame, height=int(72 * SCALE), bg=SPOT_BLACK, highlightthickness=0)        
            self.progress_frame.grid(row=4, column=0, sticky="wens", pady=(int(52 * SCALE), 0), padx=(self.padding_offset, 0))


            self.current_brightness = system_get_brightness()
            self.main_label.set_text(f"{self.current_brightness}")
            self.main_label2.set_text("")
            # somehow implement padding offset so don't have to use random value 
            # (for my display/ui setup doing -30.5 makes the playback bar work but 
            # its stoopid)
            self.midpoint = self.frame_img.width() / 2
            # print("this is midpoint of playback bar", self.midpoint)
            self.progress_width = self.frame_img.width()
            self.progress_start_x = self.midpoint - self.progress_width / 2 -1 #why the -1, idk somehow is related to janky solution for padding_offset, but it works on my screen i guess
            self.progress = self.progress_frame.create_rectangle(self.progress_start_x, 0, self.midpoint, int(72 * SCALE) , fill=SPOT_GREEN)
            self.progress_frame.create_image(self.midpoint, (self.frame_img.height() - 1)/2, image=self.frame_img)

            self.max_brightness_val = 1024 #255 on old dev environment, on rpi its 1024
            #i know this ist a normalized val or the correct func, bobo brain still decided to call it taht
            self.current_normalized_brightness = min(1.0, self.current_brightness / self.max_brightness_val)
            # print(self.current_normalized_brightness, "vs", self.progress_start_x)
            
            # self.progress_frame.coords(self.progress, self.progress_start_x, 0, self.progress_width * adjusted_progress_pct + self.progress_start_x, int(72 * SCALE))
            self.progress_frame.coords(self.progress, self.progress_start_x, 0, self.progress_width * self.current_normalized_brightness + self.progress_start_x, int(72 * SCALE))



    def update_settings(self, updated_info):
        self.callback = False
        self.current_setting = updated_info
        self.current_setting_name = self.current_setting["name"]
        self.current_setting_id = self.current_setting["id"]
        #self.new_brightness_val = self.current_setting["brightness_val"]
        
        self.header_label.set_text(self.current_setting_name)
        # print(self.current_setting)
        if self.current_setting_id == 0:
            print("set brightness")

            #system_change_brightness(self.new_brightness_val)
            self.update_brightness()
            
            self.callback = False
            global ACTIVATE_BRIGHTNESS_SLIDER
            ACTIVATE_BRIGHTNESS_SLIDER = True #this reroutes process_input, to now run alternative input processing func: slider_input
            # then inside wherever input is processed, make it so when the back button is pressed, change back to False


        elif self.current_setting_id == 1:
            print("restarting raspotify")
            is_raspotify_running = system_restart_raspotify()
            if is_raspotify_running == True:
                self.main_label.set_text("Finished")
                self.main_label2.set_text("Raspotify is running")

        elif self.current_setting_id == 2:
            print("rebooting now")
            system_reboot()
        elif self.current_setting_id == 3:
            print("Shutting down now")
            system_poweroff()
            
        elif self.current_setting_id == 4:
            self.main_label.set_text("")
            self.main_label2.set_text("")
        
        return self.callback
            


class NowPlayingFrame(tk.Frame): 
    def __init__(self, parent, controller):  
        tk.Frame.__init__(self, parent) 
        self.inflated = False
        self.active = False
        self.update_time = False
        self.configure(bg=SPOT_BLACK)
        self.header_label = tk.Label(self, text ="Now Playing", font = LARGEFONT, background=SPOT_BLACK, foreground=SPOT_GREEN) 
        # padx=(0, 10)
        self.header_label.grid(sticky='we', padx=(0, 0))
        self.grid_columnconfigure(0, weight=1)
        divider = tk.Canvas(self)
        divider.configure(bg=SPOT_GREEN, height=DIVIDER_HEIGHT, bd=0, highlightthickness=0, relief='ridge')
        #padx=(10,30)
        divider.grid(row = 1, column = 0, sticky ="we", pady=10, padx=(30, 30))
        contentFrame = tk.Canvas(self, bg=SPOT_BLACK, highlightthickness=0, relief='ridge')
        contentFrame.grid(row = 2, column = 0, sticky ="nswe")
        contentFrame.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.context_label = tk.Label(contentFrame, text ="", font = MED_FONT, background=SPOT_BLACK, foreground=SPOT_GREEN) 
        self.context_label.grid(row=0, column=0,sticky ="w", padx=int(50 * SCALE))
        #when changing tk.Label to Marquee make sure to change references to
        # .configure to set_text
        # e.g. for self.track_label = Marquee(contentFrame, text="")
        # use self.track_label.set_text(...)

        #self.artist_label = tk.Label(contentFrame, text ="", font = LARGEFONT, background=SPOT_BLACK, foreground=SPOT_GREEN) 
        self.artist_label = Marquee(contentFrame, text="", fontOffset=0)
        # padx=(10, 30)
        self.artist_label.grid(row=2, column=0,sticky ="we", padx=(10, 10))
        
        #self.album_label = tk.Label(contentFrame, text ="", font = LARGEFONT, background=SPOT_BLACK, foreground=SPOT_GREEN) 
        self.album_label = Marquee(contentFrame, text="", fontOffset=0)
        #padx=(10, 30)
        self.album_label.grid(row=3, column=0,sticky ="we", padx=(10, 10))
        
        self.track_label = Marquee(contentFrame, text="")
        #padx=(30, 50)
        self.track_label.grid(row=1, column=0,sticky ="we", padx=(30, 30))
        
        self.progress_frame = tk.Canvas(contentFrame, height=int(72 * SCALE), bg=SPOT_BLACK, highlightthickness=0)
        
        self.frame_img = ImageTk.PhotoImage(flattenAlpha(Image.open('prog_frame.png')))
        # padx=(30, 50)
        # padx=(30,30)
        # 30,20
        # needs fixing, this isn't centering
        self.update()
        padding_offset = (self.frame_img.width() - self.winfo_width()) / 2 * SCALE
        # padding_offset = 25 for this offset im just tryign random shit
        padding_offset = (self.winfo_reqwidth() - self.frame_img.width()) / 1.5 * SCALE

        print(padding_offset, "\n", self.winfo_reqwidth(), self.frame_img.width())
        self.progress_frame.grid(row=4, column=0, sticky="wens", pady=(int(52 * SCALE), 0), padx=(padding_offset, 0))

        self.time_frame = tk.Canvas(contentFrame, bg=SPOT_BLACK, highlightthickness=0)
        self.time_frame.grid(row=5, column=0,sticky ="we", padx=0, pady=(10, 0))
        self.time_frame.grid_columnconfigure(0, weight=1)
        self.elapsed_time = tk.Label(self.time_frame, text ="00:00", font = LARGEFONT, background=SPOT_BLACK, foreground=SPOT_GREEN)
        self.elapsed_time.grid(row=0, column=0, sticky ="nw", padx = int(40 * SCALE))
        self.remaining_time = tk.Label(self.time_frame, text ="-00:00", font = LARGEFONT, background=SPOT_BLACK, foreground=SPOT_GREEN)
        self.remaining_time.grid(row=0, column=1, sticky ="ne", padx = int(60 * SCALE))
        self.cached_album = None
        self.cached_artist = None
        
    def update_now_playing(self, now_playing):
        if not self.inflated:
            parent_width = self.winfo_width()
            if parent_width > 2:
                # - 40
                # - 30
                # self.midpoint = (parent_width / 2) - 30.5
                
                # somehow implement padding offset so don't have to use random value 
                # (for my display/ui setup doing -30.5 makes the playback bar work but 
                # its stoopid)
                self.midpoint = self.frame_img.width() / 2
                print("this is midpoint of playback bar", self.midpoint)
                self.progress_width = self.frame_img.width()
                self.progress_start_x = self.midpoint - self.progress_width / 2 -1 #why the -1, idk somehow is related to janky solution for padding_offset, but it works on my screen i guess
                self.progress = self.progress_frame.create_rectangle(self.progress_start_x, 0, self.midpoint, int(72 * SCALE) , fill=SPOT_GREEN)
                self.progress_frame.create_image(self.midpoint, (self.frame_img.height() - 1)/2, image=self.frame_img)
                self.inflated = True
        if not now_playing:
            return
        self.track_label.set_text(now_playing['name'])
        artist = now_playing['artist']
        if self.cached_artist != artist:

            truncd_artist = artist
            #truncd_artist = artist if len(artist) < 20 else artist[0:17] + "..."
            #self.artist_label.configure(text=truncd_artist)
            self.artist_label.set_text(truncd_artist)
            self.cached_artist = artist
        album = now_playing['album']
        if self.cached_album != album:
            #truncd_album = album if len(album) < 20 else album[0:17] + "..."
            truncd_album = album
            #self.album_label.configure(text=truncd_album)
            self.album_label.set_text(truncd_album)
            self.cached_album = album
        context_name = now_playing['context_name']
        truncd_context = context_name if context_name else "Now Playing"
        truncd_context = truncd_context if len(truncd_context) < 20 else truncd_context[0:17] + "..."
        self.header_label.configure(text=truncd_context)
        
        update_delta = 0 if not now_playing['is_playing'] else (time.time() - now_playing["timestamp"]) * 1000.0
        adjusted_progress_ms = now_playing['progress'] + update_delta
        adjusted_remaining_ms = max(0, now_playing['duration'] - adjusted_progress_ms)
        if self.update_time:
            progress_txt = ":".join(str(timedelta(milliseconds=adjusted_progress_ms)).split('.')[0].split(':')[1:3])
            remaining_txt = "-" + ":".join(str(timedelta(milliseconds=adjusted_remaining_ms)).split('.')[0].split(':')[1:3])
            self.elapsed_time.configure(text=progress_txt)
            self.remaining_time.configure(text=remaining_txt)
        self.update_time = not self.update_time
        if self.inflated:
            adjusted_progress_pct = min(1.0, adjusted_progress_ms / now_playing['duration'])
            self.progress_frame.coords(self.progress, self.progress_start_x, 0, self.progress_width * adjusted_progress_pct + self.progress_start_x, int(72 * SCALE))
        if(now_playing['track_index'] < 0):
            self.context_label.configure(text="")
            return
        context_str = str(now_playing['track_index']) + " of " + str(now_playing['track_total'])
        self.context_label.configure(text=context_str)
        
   
class StartPage(tk.Frame): 
    def __init__(self, parent, controller):  
        tk.Frame.__init__(self, parent) 
        self.green_arrow_image = ImageTk.PhotoImage(flattenAlpha(Image.open('pod_arrow_grn.png')))
        self.black_arrow_image = ImageTk.PhotoImage(flattenAlpha(Image.open('pod_arrow_blk.png')))
        self.empty_arrow_image = ImageTk.PhotoImage(flattenAlpha(Image.open('pod_arrow_empty.png')))
        self.play_image = ImageTk.PhotoImage(flattenAlpha(Image.open('pod_play.png')))
        self.pause_image = ImageTk.PhotoImage(flattenAlpha(Image.open('pod_pause.png')))
        self.space_image = ImageTk.PhotoImage(flattenAlpha(Image.open('pod_space.png')))
        self.wifi_image = ImageTk.PhotoImage(flattenAlpha(Image.open('pod_wifi.png')))
        self.configure(bg=SPOT_BLACK)
        header_container = tk.Canvas(self, bg=SPOT_BLACK, highlightthickness=0, relief='ridge')
        header_container.grid(sticky='we')
        self.header_label = tk.Label(header_container, text ="sPot", font = LARGEFONT, background=SPOT_BLACK, foreground=SPOT_GREEN) 
        self.header_label.grid(sticky='we', column=1, row=0, padx=(0, 10))
        self.play_indicator = tk.Label(header_container, image=self.space_image, background=SPOT_BLACK)
        self.play_indicator.grid(sticky='w', column=0, row=0, padx=(70 * SCALE,0))
        self.wifi_indicator = tk.Label(header_container, image=self.space_image, background=SPOT_BLACK)
        self.wifi_indicator.grid(sticky='w', column=2, row=0, padx=(0,90 * SCALE))
        header_container.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        divider = tk.Canvas(self)
        divider.configure(bg=SPOT_GREEN, height=DIVIDER_HEIGHT, bd=0, highlightthickness=0, relief='ridge')
        divider.grid(row = 1, column = 0, sticky ="we", pady=10, padx=(10, 30))
        contentFrame = tk.Canvas(self, bg=SPOT_BLACK, highlightthickness=0, relief='ridge')
        contentFrame.grid(row = 2, column = 0, sticky ="nswe")
        self.grid_rowconfigure(2, weight=1)
        listFrame = tk.Canvas(contentFrame)
        listFrame.configure(bg=SPOT_BLACK, bd=0, highlightthickness=0)
        listFrame.grid(row=0, column=0, sticky="nsew")
        contentFrame.grid_rowconfigure(0, weight=1)
        contentFrame.grid_columnconfigure(0, weight=1)

        # scrollbar 
        self.scrollFrame = tk.Canvas(contentFrame)
        self.scrollFrame.configure(bg=SPOT_BLACK, width=int(50 * SCALE), bd=0, highlightthickness=4, highlightbackground=SPOT_GREEN)
        self.scrollBar = tk.Canvas(self.scrollFrame, bg=SPOT_GREEN, highlightthickness=0, width=int(20 * SCALE))
        self.scrollBar.place(in_=self.scrollFrame, relx=.5,  y=int(10 * SCALE), anchor="n", relwidth=.6, relheight=.9)
        self.scrollFrame.grid(row=0, column=1, sticky="ns", padx=(0, 30), pady=(0, 10))
        
        self.listItems = []
        self.arrows=[]
        #x = 1 # x is set to 1, to skip the firs entry into RootPage inside view_model.py, this is skipped so that now playing is at the top
        # range(7) aka 0-6 refers to: artists, albums, new releases, podcasts, playlists, search and my added settings page. The now playing page is added dynamically
        for x in range(6):
            item = tk.Label(listFrame, text =" " + str(x), justify=tk.LEFT, anchor="w", font = LARGEFONT, background=SPOT_BLACK, foreground=SPOT_GREEN, padx=(30 * SCALE))
            imgLabel = tk.Label(listFrame, image=self.green_arrow_image, background=SPOT_BLACK)
            imgLabel.image = self.green_arrow_image
            imgLabel.grid(row=x, column=1, sticky="nsw", padx = (0, 30))
            item.grid(row = x, column = 0, sticky="ew",padx = (10, 0))
            self.listItems.append(item)
            self.arrows.append(imgLabel)
        listFrame.grid_columnconfigure(0, weight=1)
        # listFrame.grid_columnconfigure(1, weight=1)
    

    def show_scroll(self, index, total_count):
        scroll_bar_y_rel_size = max(0.9 - (total_count - MENU_PAGE_SIZE) * 0.06, 0.03)
        scroll_bar_y_raw_size = scroll_bar_y_rel_size * self.scrollFrame.winfo_height()
        percentage = index / (total_count - 1)
        offset = ((1 - percentage) * (scroll_bar_y_raw_size + int(20 * SCALE))) - (scroll_bar_y_raw_size + int(10 * SCALE))
        self.scrollBar.place(in_=self.scrollFrame, relx=.5, rely=percentage, y=offset, anchor="n", relwidth=.66, relheight=scroll_bar_y_rel_size)
        self.scrollFrame.grid(row=0, column=1, sticky="ns", padx=(0, 30), pady=(0, 10))

    def hide_scroll(self):
        self.scrollFrame.grid_forget()

    def set_header(self, header, now_playing = None, has_wifi = False):
        truncd_header = header if len(header) < 20 else header[0:17] + "..."
        self.header_label.configure(text=truncd_header)
        play_image = self.space_image
        if now_playing is not None: #here play_image and pause_image can be switched around, i did so, cuz i think its intuitive taht way
            play_image = self.play_image if now_playing['is_playing'] else self.pause_image #edit 2: chagned them back again
        self.play_indicator.configure(image = play_image)
        self.play_indicator.image = play_image
        wifi_image = self.wifi_image if has_wifi else self.space_image
        self.wifi_indicator.configure(image = wifi_image)
        self.wifi_indicator.image = wifi_image
    
    def set_list_item(self, index, text, line_type = LINE_NORMAL, show_arrow = False):
        bgColor = SPOT_GREEN if line_type == LINE_HIGHLIGHT else SPOT_BLACK
        txtColor = SPOT_BLACK if line_type == LINE_HIGHLIGHT else \
            (SPOT_GREEN if line_type == LINE_NORMAL else SPOT_WHITE)
        truncd_text = text if len(text) < 17 else text[0:15] + "..."
        self.listItems[index].configure(background=bgColor, foreground=txtColor, text=truncd_text)
        arrow = self.arrows[index]
        arrow.grid(row=index, column=1, sticky="nsw", padx = (0, 30))
        arrowImg = self.empty_arrow_image if not show_arrow else \
            (self.black_arrow_image if line_type == LINE_HIGHLIGHT else self.green_arrow_image)
        arrow.configure(background=bgColor, image=arrowImg)
        arrow.image = arrowImg

        
def slider_input(wheel_data, btn_state, last_btn, btn):
    # nth is for in how many equal parts the range should be split up in
    # eg nth=10, every 10th position on the wheel will be registered
    # the clickwheel goes from 0 to 47
    #global wheel_position, last_button, last_interaction, ACTIVATE_BRIGHTNESS_SLIDER, SLIDER_WHEEL_DATA
    global ACTIVATE_BRIGHTNESS_SLIDER, last_interaction, last_button, app, page
    button_state = btn_state
    #last_button = last_btn
    button = btn
    position = wheel_data
    
    # get modulo operator to convert range 0-47 to steps of 10
    #odulo_op = 10 / 47
    #print(modulo_op)
    if position % 5 == 0:
        # highest clickwheel val can be 47, lowest 0
        normalized_wheel_pos = position / 47
        #scale normalized wheel pos to range 0 - 1024, then use value in system_change_brightness(val)
        scaled_normalized_wheel_pos = normalized_wheel_pos * 1024
        print("slider:", normalized_wheel_pos, "vs:",scaled_normalized_wheel_pos)
        system_change_brightness(scaled_normalized_wheel_pos)
        #render(app, page.render())
        #render_settings(app, page.render())
        
        #print(app.frames)
        frame = app.frames[SettingsFrame]
        # check if were on brightness page
        c = frame.update_settings(
                {
                    "name": "Brightness",
                    "id": 0
                })


    
    # 1/10 of range = 4.7
    #t = 47 / position / 100




    #ten_percent = 47 * 10 / 100
    #print(ten_percent)
    #normalized_ten_percent = 0.1

    #print(scaled_normalized_wheel_pos // 102)


    #position = input[2]
    #button = input[0]
    #button_state = input[1]

    #if button == 29 and button_state == 0:
    #    wheel_position = -1
    #elif wheel_position == -1:
    #    wheel_position = position
    #elif position % 2 != 0:
    #    pass
    #print("from slider input:", wheel_position)
    
    if button_state == 0:
        last_button = -1
    elif button == last_button:
        pass
    elif button == 11:
        onBackPressed()
        last_button = button
        ACTIVATE_BRIGHTNESS_SLIDER = False


    now = time.time()
    if (now - last_interaction > SCREEN_TIMEOUT_SECONDS):
        print("waking")
        screen_wake()
    last_interaction = now

    #system_change_brightness(scaled_normalized_wheel_pos)
    #SLIDER_WHEEL_DATA = wheel_position
    #print(SLIDER_WHEEL_DATA)

    # idk think this needed
    # elif wheel_position <=1 and position > 44:
    #     onDownPressed()
    #     wheel_position = position
    # elif wheel_position >=44 and position < 1:
    #     onUpPressed()
    #     wheel_position = position
    # elif abs(wheel_position - position) > 6:
    #     wheel_position = -1
    # elif wheel_position > position:
    #     onDownPressed()
    #     wheel_position = position
    # elif wheel_position < position:
    #     onUpPressed()
    #     wheel_position = position


def processInput(app, input):
    global wheel_position, last_button, last_interaction
    position = input[2]
    button = input[0]
    button_state = input[1]

    if button == 29 and button_state == 0:
        wheel_position = -1
    elif wheel_position == -1:
        wheel_position = position
    elif position % 2 != 0:
        pass
    
    global ACTIVATE_BRIGHTNESS_SLIDER
    #print("slider state:", ACTIVATE_BRIGHTNESS_SLIDER)
    if ACTIVATE_BRIGHTNESS_SLIDER == True:
        slider_input(position, input[1], last_button, input[0])
        return

    
    elif wheel_position <=1 and position > 44:
        onDownPressed()
        wheel_position = position
    elif wheel_position >=44 and position < 1:
        onUpPressed()
        wheel_position = position
    elif abs(wheel_position - position) > 6:
        wheel_position = -1
    elif wheel_position > position:
        onDownPressed()
        wheel_position = position
    elif wheel_position < position:
        onUpPressed()
        wheel_position = position
    

    if button_state == 0:
        last_button = -1
    elif button == last_button:
        pass
    elif button == 7:
        onSelectPressed()
        last_button = button
    elif button == 11:
        onBackPressed()
        last_button = button
    elif button == 10:
        onPlayPressed()
        last_button = button
    elif button == 8:
        onNextPressed()
        last_button = button
    elif button == 9:
        onPrevPressed()
        last_button = button
    
    now = time.time()
    if (now - last_interaction > SCREEN_TIMEOUT_SECONDS):
        print("waking")
        screen_wake()
    last_interaction = now

    # app.frames[StartPage].set_list_item(0, "Test") 

def onKeyPress(event):
    c = event.keycode
    if (c == UP_KEY_CODE):
        onUpPressed()
    elif (c == DOWN_KEY_CODE):
        onDownPressed()
    elif (c == RIGHT_KEY_CODE):
        onSelectPressed()
    elif (c == LEFT_KEY_CODE):
        onBackPressed()
    elif (c == NEXT_KEY_CODE):
        onNextPressed()
    elif (c == PREV_KEY_CODE):
        onPrevPressed()
    elif (c == PLAY_KEY_CODE):
        onPlayPressed()
    elif (c == QUIT_KEY_CODE):
        onQuitPressed()
    else:
        print("unrecognized key: ", c)

def update_search(q, ch, loading, results):
    global app, page
    search_page = app.frames[SearchFrame]
    if (results is not None):
        page.render().unsubscribe()
        page = SearchResultsPage(page, results)
        render(app, page.render())
    else:
        search_page.update_search(q, ch, loading)

def render_search(app, search_render):
    app.show_frame(SearchFrame)
    search_render.subscribe(app, update_search)



def update_settings(setting):
    global app, page
    frame = app.frames[SettingsFrame]
    # check if were on brightness page
    sett_id = setting["id"]
    c = frame.update_settings(setting)
    print("update settings callback:", c)
    if sett_id == 0:
        if (c != False):
            page.render().subscribe(app, update_settings)
            app.show_frame(SettingsFrame)
            page = SingleSettingPage(setting, page)
            render(app, page.render())
            # time.sleep(5)


def render_settings(app, settings_render):
    app.show_frame(SettingsFrame)
    settings_render.subscribe(app, update_settings)

# def update_settings(settings):
#     frame = app.frames[SettingsFrame]
#     frame.update_settings(settings)

#def render_settings(app, settings_render):
#    app.show_frame(SettingsFrame)
    # settings_render.subscribe(app, update_settings
#    frame = app.frames[SettingsFrame]
#    frame.render()    

def render_menu(app, menu_render):
    app.show_frame(StartPage)
    page = app.frames[StartPage]
    if(menu_render.total_count > MENU_PAGE_SIZE):
        page.show_scroll(menu_render.page_start, menu_render.total_count)
    else:
        page.hide_scroll()
    for (i, line) in enumerate(menu_render.lines):
        page.set_list_item(i, text=line.title, line_type = line.line_type, show_arrow = line.show_arrow) 
    page.set_header(menu_render.header, menu_render.now_playing, menu_render.has_internet)

def update_now_playing(now_playing):
    frame = app.frames[NowPlayingFrame]
    frame.update_now_playing(now_playing)

def render_now_playing(app, now_playing_render):
    app.show_frame(NowPlayingFrame)
    now_playing_render.subscribe(app, update_now_playing)

def render(app, render):
    if (render.type == MENU_RENDER_TYPE):
        render_menu(app, render)
    elif (render.type == NOW_PLAYING_RENDER):
        render_now_playing(app, render)
    elif (render.type == SEARCH_RENDER):
        render_search(app, render)
    elif (render.type == SETTINGS_RENDER):
        render_settings(app, render)
        

def onPlayPressed():
    global page, app
    page.nav_play()
    render(app, page.render())
    
def onSelectPressed():
    global page, app
    if (not page.has_sub_page):
        return
    page.render().unsubscribe()
    page = page.nav_select()
    render(app, page.render())

def onBackPressed():
    global page, app
    previous_page = page.nav_back()
    if (previous_page):
        page.render().unsubscribe()
        page = previous_page
        render(app, page.render())
    
def onNextPressed():
    global page, app
    page.nav_next()
    render(app, page.render())

def onPrevPressed():
    global page, app
    page.nav_prev()
    render(app, page.render())

def onUpPressed():
    global page, app
    page.nav_up()
    render(app, page.render())

def onDownPressed():
    global page, app
    page.nav_down()
    render(app, page.render())

#init display brightness
system_change_brightness(1024)

# Driver Code 
page = RootPage(None)
app = tkinterApp() 
render(app, page.render())
app.overrideredirect(True)
app.overrideredirect(False)
sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(0)
socket_list = [sock]
loop_count = 0

def app_main_loop():
    global app, page, loop_count, last_interaction, screen_on
    try:
        read_sockets = select(socket_list, [], [], 0)[0]
        for socket in read_sockets:
            data = socket.recv(128)
            processInput(app, data)
        loop_count += 1
        if (loop_count >= 300):
            if (time.time() - last_interaction > SCREEN_TIMEOUT_SECONDS and screen_on):
                screen_sleep()
            render(app, page.render())
            loop_count = 0
    except:
        pass
    finally:
        app.after(2, app_main_loop)

app.bind('<KeyPress>', onKeyPress)
app.after(5, app_main_loop)
app.mainloop()
