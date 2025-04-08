# -*- coding: utf-8 -*-
"""
Created on Sun Dec 13 19:06:42 2020

@author: Simon
"""
import os
import tkinter as tk
import time
import traceback
import subprocess
import tempfile
import platform
import logging
from datetime import datetime
import pyglet.gl as gl
from pyglet.window import mouse
from tkinter import messagebox

# set default display if it's not set yet
os.environ['DISPLAY'] = os.environ.get('DISPLAY', ':0')

try:
    import pyglet
except Exception:
    messagebox.showerror(title=f'{__file__}', message=traceback.format_exc())


logging.getLogger().setLevel(logging.DEBUG)

if platform.system()=='Windows':
    from backends.windows import hide_from_taskbar
elif platform.system()=='Linux':
    from backends.linux import get_desktop_environment
    env = get_desktop_environment()
    if env=='kde':
        from backends.linux import hide_from_taskbar


class main(pyglet.window.Window):
    def __init__ (self):

        display = pyglet.canvas.get_display()
        screens_orig = display.get_screens()

        # sort monitor by distance to (0, 0)
        # the primary monitor has its corner in (0, 0)
        # screens = sorted(screens, key=lambda x:x.x**2+x.y**2, reverse=True)
        screens = sorted(screens_orig, key=lambda x:x.height, reverse=True)
        self.scroll_accumulator = 0
        self.last_scroll_time = 0

        for idx, screen in enumerate(screens):
            self.lock_file = f'{tempfile.gettempdir()}/_tmp_screen{idx}.lock'
            # if no lockfile is present or lockfile is older than 2h
            if (not os.path.isfile(self.lock_file)
                or (time.time()-os.path.getmtime(self.lock_file))>7200):
                with open(self.lock_file, 'w') as f:
                    f.write('')
                break
        else:
            logging.error(f'No screen left. screens: {screens}')
            return

        if idx<2:
            self.idx_monitorcontrol = int(not idx)
        else:
            self.idx_monitorcontrol = None
        print(f'{self.idx_monitorcontrol=}, {idx=}')

        if self.idx_monitorcontrol is not None:
            self.previous_luminance = subprocess.check_output(f'monitorcontrol --get-luminance --monitor {self.idx_monitorcontrol}', shell=True).decode().strip()
            subprocess.Popen(f'monitorcontrol --set-luminance 0 --monitor {self.idx_monitorcontrol}', shell=True)
            self.current_brightness = 0
        else:
            self.current_brightness = None # Indicate no brightness control

        logging.info(f'dimming {idx}: {screen}')
        super(main, self).__init__(screen=screen, style='borderless')
        self.set_location(screen.x, screen.y)
        self.set_size(screen.width, screen.height)
        self.dispatch_events()

        self.background = pyglet.graphics.Batch()
        self.time_label = pyglet.text.Label('Hello, world',
                          font_name='arial',
                          font_size=75,
                          anchor_x='right',
                          color=(128,128,128, 128),
                          x=screen.width-20, y=screen.height-55,
                          anchor_y='center')
        self.date_label = pyglet.text.Label(
                          datetime.now().strftime('%d.%m.%y'),
                          font_name='arial',
                          font_size=36,
                          # multiline=True,
                          color=(128,128,128, 128),
                          anchor_x='right',
                          x=screen.width-35, y=screen.height-135,
                          anchor_y='center')
        hide_from_taskbar(__file__)
        self.mouse_visible = True
        self.last_move = time.time()
        self.last_click = time.time()
        self.running = True
        self.cleaned_up = False
        self.white_screen_mode = False
        self.brightness_before_white = 0 # Store brightness before white screen activation
        self.run()

    def cleanup(self):
        if self.cleaned_up:
            return
        if self.idx_monitorcontrol is not None:
            subprocess.check_output(f'monitorcontrol --set-luminance 100 --monitor {self.idx_monitorcontrol}', shell=True)
            # subprocess.check_output(f'monitorcontrol --set-luminance {self.previous_luminance} --monitor {self.idx_monitorcontrol}', shell=True)
        logging.debug(f'deleting {self.lock_file=}')
        try:
            os.remove(self.lock_file)
        except FileNotFoundError:
            logging.warning(f'lock file was already removed {self.lock_file=}')
        self.cleaned_up = True

    def __del__(self):
        self.cleanup()

    def on_mouse_motion(self, x, y, button, modifiers):
        self.last_move = time.time()
        self.set_mouse_visible(True)
        self.mouse_visible = True

    def on_mouse_press(self, x, y, button, modifiers):
        if button == mouse.LEFT:
            if time.time() - self.last_click < 0.5:
                self.close()
                self.running = False
            self.last_click = time.time()
        elif button == mouse.RIGHT:
            if not self.white_screen_mode:
                # Activate white screen mode
                self.white_screen_mode = True
                if self.idx_monitorcontrol is not None and self.current_brightness is not None:
                    self.brightness_before_white = self.current_brightness
                    self.current_brightness = 100
                    self._set_brightness(self.current_brightness)
            else:
                # Deactivate white screen mode
                self.white_screen_mode = False
                if self.idx_monitorcontrol is not None and self.current_brightness is not None:
                    self.current_brightness = self.brightness_before_white
                    self._set_brightness(self.current_brightness)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        if self.idx_monitorcontrol is None or self.current_brightness is None:
            return # No monitor control available

        # Accumulate scroll amount
        self.scroll_accumulator += scroll_y * 10
        # Update the last scroll time
        self.last_scroll_time = time.time()

    def on_key_press(self, symbol, modifiers):
        if symbol > 740324309504:
            return # media keys

    def render(self):
        # pass
        if self.context is None: return

        # Check if it's time to apply brightness change (250ms after last scroll)
        current_time = time.time()
        if hasattr(self, 'last_scroll_time') and self.scroll_accumulator != 0 and current_time - self.last_scroll_time >= 0.1:
            # Calculate new brightness based on accumulated scroll
            new_brightness = self.current_brightness + self.scroll_accumulator
            # Clamp brightness between 0 and 100
            new_brightness = max(0, min(100, new_brightness))

            # Apply the change if needed
            if new_brightness != self.current_brightness:
                self.current_brightness = new_brightness
                self._set_brightness(self.current_brightness)

            # Reset accumulator
            self.scroll_accumulator = 0

        # Set background color based on mode
        if self.white_screen_mode:
            gl.glClearColor(1, 1, 1, 1) # White
        else:
            gl.glClearColor(0, 0, 0, 1) # Black (default)

        self.clear()
        self.time_label.text = datetime.now().strftime('%H:%M')
        self.background.draw()
        self.time_label.draw()
        self.date_label.draw()
        self.flip()
        if self.mouse_visible:
            if time.time() - self.last_move>0.5:
                self.set_mouse_visible(False)
                self.mouse_visible = False

    def _set_brightness(self, value):
        """Sets the monitor brightness using monitorcontrol."""
        if self.idx_monitorcontrol is not None:
            brightness_value = int(round(value)) # Ensure integer value
            command = f'monitorcontrol --set-luminance {brightness_value} --monitor {self.idx_monitorcontrol}'
            subprocess.Popen(command, shell=True)

    def run(self):
        while self.running:
            self.dispatch_events()
            self.render()
            time.sleep(0.1)
        self.cleanup()
        self.close()

if __name__=='__main__':
    try:
        self = main()
    except Exception:
        messagebox.showerror(title=f'{__file__}', message=traceback.format_exc())
        for i in range(2):
            lock_file = f'{tempfile.gettempdir()}/_tmp_screen{i}.lock'
            try:
                subprocess.check_output(f'monitorcontrol --set-luminance 100 --monitor {i}', shell=True)
            except Exception as e:
                print(f'ERROR: {e} {str(e)}, {repr(e)}')
            if os.path.exists(lock_file): os.remove(lock_file)
