#!/usr/bin/env python

#	Copyright (C) 2015 by Andreas and Klaus Noever
#  	This program is free software: you can redistribute it and/or modify
#  	it under the terms of the GNU General Public License as published by
#  	the Free Software Foundation, either version 3 of the License, or
#  	(at your option) any later version.

#	python 3.9
#	revision date: 26-Mar-2022

#	Volume control: 
#	Default is using the RasPi audio output with software volume control.
#	At 100% volume, the audio quality is acceptable, however at lower 
#	volume level sets there will be increasing distortion. 
#	Default value is "0" 
#	If using a USB DAC, volume will be hardware controlled using amixer. 
#	We used the Plugable Audio Adapter> Quality is great at all volume levels.
#	In this case USB_audio must be set to '1'. 
USB_audio=1

#	Key delay
#	This is the minimum time interval in seconds between 2 commands to be executed as
#	separate commands.Depending on whether the user is fast or slow in pushing the
#	command buttons, this may need to be adjusted
key_delay=0.3


import os
import pyudev
import sys
import select
import tty
import termios
import time
import requests
from musicpd import (MPDClient, CommandError)
from text_to_speech import TTS

#
#
#	Generation of text to speech files

class Meta:
    def __init__(self, path, parent):
        """
        :type path: str
        :type parent: Folder
        """
        self.parent = parent
        self.path = path

    def meta_file(self, key):
        assert self.parent
        a, b = os.path.split(self.path)
        meta = os.path.join(a, '.meta')
        if not os.path.exists(meta):
            os.makedirs(meta)
        return os.path.join(meta, b + '_' + key)

    def __str__(self):
        return os.path.split(self.path)[1]


class Folder(Meta):
    def __init__(self, path, parent):
        super(Folder, self).__init__(path, parent)

        self._entries = []
        for e in os.listdir(path):
            if e == '.meta':
                continue
            e = os.path.join(path, e)
            if os.path.isdir(e):
                self._entries.append(Folder(e, self))
            elif os.path.isfile(e):
                self._entries.append(File(e, self))
            else:
                raise Exception('Neither a file nor a directory: %s' % e)
        self._entries.sort(key=lambda x: x.path)

    def is_folder(self):
        return True

    def is_empty(self):
        return len(self._entries) == 0

    def entries(self, recursive=False):
        ret = list(self._entries)
        if recursive:
            for e in self._entries:
                if e.is_folder():
                    ret.extend(e.entries(recursive=True))
        return ret

    def next_entry(self, entry):
        entries = self.entries()
        next = entries.index(entry) + 1
        if next == len(entries):
            return None
        return entries[next]


class File(Meta):
    def __init__(self, path, parent):
        super(File, self).__init__(path, parent)

    def is_folder(self):
        return False


def dump(f, ident=0):
    prefix = ' ' * ident
    print (prefix + os.path.split(f.path)[1])
    if f.is_folder():
        for e in f.entries():
            dump(e, ident + 2)


#
#
#	Navigation through folder hierarchy and playing files	

def play(path):
    client.clear()
    try:
        print (f'playing {path}')
        client.add(path[len(PATH) + 1:])
        client.play()
    except CommandError as e:
        print (e)


class Screen:
    def __init__(self, item):
        self.item = item

    def handle_up(self):
        if self.item.parent is None:
            print ('already at top level of hierarchy, will stay in same folder')
            client.play()
            return None
        return FolderBrowser(self.item.parent, self.item)

    def handle_volume_up(self):
        if USB_audio == 0:  # USB_audio as configured
            client.setvol(min(100, int(client.status()['volume']) + 5))
            print ('Volume:' + str(client.status()['volume']))
        if USB_audio ==1:
            os.system("amixer set 'Speaker' 2dB+")

    def handle_volume_down(self):
        if USB_audio == 0:
            client.setvol(max(0, int(client.status()['volume']) - 5))
            print ("Volume: %s") % client.status()['volume']

        if USB_audio == 1:
            os.system("amixer set 'Speaker' 2dB-")

    def handle_volume_up_large(self):
        if USB_audio == 0:
                client.setvol(min(100, int(client.status()['volume']) + 5))
                print ("Volume: %s") % client.status()['volume']
        if USB_audio ==1:
                os.system("amixer set 'Speaker' 10dB+")

    def handle_volume_down_large(self):
        if USB_audio == 0:
                client.setvol(max(0, int(client.status()['volume']) - 5))
                print ("Volume: %s") % client.status()['volume']
        if USB_audio == 1:
                os.system("amixer set 'Speaker' 10dB-")

    def handle_pos1(self):
        return root


class EmptyFolderBrowser(Screen):
    def __init__(self, folder):
        super(EmptyFolderBrowser, self).__init__(folder)


class FolderBrowser(EmptyFolderBrowser):
    def __init__(self, folder, entry=None, audiobook=False):
        super(FolderBrowser, self).__init__(folder)
        assert not folder.is_empty()
        self.folder = folder
        self.audiobook = audiobook
        if entry:
            self.index = self.folder.entries().index(entry)
        else:
            self.index = 0
        self.read_entry()

    def entry(self):
        """
        :rtype: Meta
        """
        return self.folder.entries()[self.index]

    def read_entry(self):
        """
        Read the current entry
        """
        play(self.entry().meta_file('tts.mp3'))

    def handle_down(self):
        return self.entry()

    def handle_right(self):
        self.index = (self.index + 1) % len(self.folder.entries())
        self.read_entry()

    def handle_left(self):
        self.index = (self.index - 1) % len(self.folder.entries())
        self.read_entry()

    def handle_bookmark(self):
        screen = get_screen_for_bookmark(self.folder)
        if not screen and self.entry().is_folder:
            return get_screen_for_bookmark(self.entry())
        return screen


class MusicPlayer(Screen):
    def __init__(self, file, mark=0):
        """
        :type file: File
        """
        super(MusicPlayer, self).__init__(file)
        self.file = file
        play(self.file.path)
        client.seek(0, mark)

    def maybe_set_bookmark(self):
        elapsed = int(float(client.status().get('elapsed', "0")))
        index = self.file.parent.entries().index(self.file)
        if elapsed > 30:
            print (f'creating bookmark at {index}-{elapsed}')
            with open(self.file.parent.meta_file('bookmark.txt'), 'w') as f:
                f.write(str(index) + '\n')
                f.write(str(elapsed) + '\n')
        else:
            print (f'not creating bookmark, elapsed = {elapsed} <= 30s')

    def handle_up(self):
        self.maybe_set_bookmark()
        return super(MusicPlayer, self).handle_up()

    def handle_pos1(self):
        self.maybe_set_bookmark()
        return super(MusicPlayer, self).handle_pos1()

    def handle_play_pause(self):
        os.system('mpc toggle')

    def handle_stopped(self):
        return self.file.parent.next_entry(self.file)

    def handle_right(self):
        os.system('mpc seek +00:01:00')

    def handle_left(self):
        os.system('mpc seek -00:01:00')

    def handle_tick(self):
        if client.status()['state'] == 'stop':
            return self.handle_stopped()

    def handle_bookmark(self):
        return get_screen_for_bookmark(self.file.parent)


def get_screen(entry):
    if isinstance(entry, Screen):
        return entry
    if entry.is_folder():
        if entry.is_empty():
            return EmptyFolderBrowser(entry)
        else:
            return FolderBrowser(entry)
    else:
        return MusicPlayer(entry)


def get_screen_for_bookmark(folder):
    if not folder.parent:
        return None
    try:
        with open(folder.meta_file('bookmark.txt'), 'r') as f:
            index = int(f.readline())
            mark = int(f.readline())
        print (f"found mark: {index}-{mark}")
        return MusicPlayer(folder.entries()[index], mark)
    except IOError:
        return None


class FileBrowser:
    def __init__(self, folder):
        self.folder = folder
        self.current = get_screen(folder)
    # assignment of key input, using IR command device ALPINE RUE-4202 and FLIRC
    def handle(self, input):
        handlers = {'r': 'handle_right',
                    'l': 'handle_left',
                    'd': 'handle_down',
                    'u': 'handle_up',
                    'w': 'handle_bookmark', # A.PROC ,these are special command buttons on APLPINE RUE-4202
                    't': 'handle_bookmark', # MUTE
                    'z': 'handle_pos1',    # POWER	
                    'm': 'handle_volume_up',
                    'v': 'handle_volume_down',
                    'p': 'handle_play_pause',
                    'tick': 'handle_tick',
                    'g': 'handle_volume_down_large', # SOURCE
                    'q': 'handle_volume_up_large',}  # BAND	
        handler = handlers.get(input)

        if not handler:
            return  # invalid character
        if not hasattr(self.current, handler):
            return  # current screen is not interested
        next = getattr(self.current, handler)()  # invoke handler
        if next:
            print (f"transition: {next}")
            self.current = get_screen(next)
            print (f"new screen: {self.current}")


#
#
#	Reset at start

os.system("sudo /etc/init.d/mpd stop")
os.system("sudo umount /mnt/usb")


#
#
#	Management of USB storage device

USBName = "LOAD"

def checkForUSBDevice(name):
    res = None
    try:
        context = pyudev.Context()
        for device in context.list_devices(subsystem='block', DEVTYPE='partition'):
            if device.get('ID_FS_LABEL') == name:
                res = device.device_node
    except Exception:
        print ("error")
    return res

print (f"Waiting for usb device {USBName}")

while True:
    device = checkForUSBDevice(USBName)
    if device:
        print (f"Mounting {device}")
        os.system(f"sudo mount -o iocharset=utf8,uid=mpd,gid=audio,umask=000 {device} /mnt/usb")
        break
    time.sleep(1)

def internet_connection():
    url = "https://www.google.com"
    timeout = 10
    try:
        # requesting URL
        request = requests.get(url, timeout=timeout)
        return True
  
        # catching exception
    except (requests.ConnectionError, requests.Timeout):
        return False


#
#
#	Run generation of metafolders and files

PATH = '/var/lib/mpd/music'
assert PATH[-1] != '/'

root = Folder(PATH, None)

internet = internet_connection()

if internet:
    for f in root.entries(recursive=True):
        path = f.meta_file('tts.mp3')
        mp3_tts = TTS(str(f), path)
        mp3_tts.download_tts_filename()

#
#
#	Activate media player

os.system("sudo /etc/init.d/mpd start")

client = MPDClient()
client.timeout = 60
client.idletimeout = None
client.connect("localhost", 6600)
os.system("sudo mpc update")


#
#
#	Controlcycle of USB storage device and keyborad inputs

def run():
    fb = FileBrowser(root)
    last = time.time()
    while True:
        # check if usb is still there
        if not checkForUSBDevice(USBName):
            print ("lost usb device - exiting")
            os.system("sudo mpc stop")
            os.system("sudo /etc/init.d/mpd stop")
            os.system("sudo umount /mnt/usb")
            return # exit - and restart

        # check for input
        char = None
        if select.select([sys.stdin], [], [], 0.5)[0]:
            char = os.read(sys.stdin.fileno(), 1)
            char = char if type(char) is str else char.decode()

        if char:
            # handle input
            if time.time() - last < key_delay:  # intra/inter key delay in seconds, value configured
                print (f'command {char} - ignored')
            else:
                print (f'command {char}')
                fb.handle(char)
                last = time.time()
        fb.handle('tick')

#
#
# use single character input without "return" as command
try:
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())
    run()

finally:
    #old_settings = termios.tcgetattr(sys.stdin)
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
exit()
