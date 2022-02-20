import gtts
from playsound import playsound

class TTS:
    def __init__(self, filename) -> None:
        self.filename = filename
    
    def download_tts_filename(self):
        with open(f'tts.mp3', 'wb') as mp3:
            tts = gtts.gTTS(self.filename)
            tts.write_to_fp(mp3)
    
    def play_tts(self):
        playsound('tts.mp3')

if __name__ == '__main__':
    pass