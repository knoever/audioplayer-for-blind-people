import os, sys

sys.path.insert(0, '/Users/bellcha/OneDrive/audioplayer-for-blind-people')

from text_to_speech import TTS

cwd = os.getcwd()
files = os.listdir("/Users/bellcha/OneDrive")

for file in files:

    tts = TTS(file)
    tts.download_tts_filename()
    tts.play_tts()
