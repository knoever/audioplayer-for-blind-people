import gtts
from playsound import playsound

class TTS:
    def __init__(self, filename, path) -> None:
        self.filename = filename
        self.path = path
    
    def download_tts_filename(self):
        with open(self.path, 'wb') as mp3:
            tts = gtts.gTTS(self.filename)
            tts.write_to_fp(mp3)
    
    def play_tts(self):
        playsound('tts.mp3')

if __name__ == '__main__':
    pass
