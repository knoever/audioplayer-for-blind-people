import gtts, os
from playsound import playsound


files = os.listdir()

#tts = gtts.gTTS("Hello World")

#tts_file = tts.save('hello.mp3')

#playsound('hello.mp3')

for f in files:
    print(f)

with open('test.mp3', 'wb') as mp3:
    for f in files:
        tts = gtts.gTTS(f)
        tts.write_to_fp(mp3)

playsound('test.mp3')