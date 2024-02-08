#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jan 15 19:20:47 2023

@author: simon
"""

import ctypes
import win32gui
import win32api
from win32con import SWP_NOMOVE
from win32con import SWP_NOSIZE
from win32con import SW_HIDE
from win32con import SW_SHOW
from win32con import HWND_TOPMOST
from win32con import GWL_EXSTYLE
from win32con import WS_EX_TOOLWINDOW
from win32gui import GetWindowText, GetForegroundWindow, SetForegroundWindow


def find_window(name):
    try:
        return win32gui.FindWindow(None, name)
    except win32gui.error:
        print("Error while finding the window")
        return None

def hide_from_taskbar(name):
    try:
        hw = find_window(name)
        win32gui.ShowWindow(hw, SW_HIDE)
        win32gui.SetWindowLong(hw, GWL_EXSTYLE,win32gui.GetWindowLong(hw, GWL_EXSTYLE)| WS_EX_TOOLWINDOW);
        win32gui.ShowWindow(hw, SW_SHOW);
    except win32gui.error:
        print("Error while hiding the window")
        return None

def set_topmost(hw):
    try:
          win32gui.SetWindowPos(hw, HWND_TOPMOST, 0,0,0,0, SWP_NOMOVE | SWP_NOSIZE)
    except win32gui.error:
        print("Error while move window on top")