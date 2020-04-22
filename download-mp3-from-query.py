import os
import subprocess
import logging
from dotenv import load_dotenv
import urllib.parse
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from time import sleep

load_dotenv(verbose=True)
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


options = Options()
# options.headless = True
driver = webdriver.Firefox(options=options)

query = "Eminem when I'm gone"

url = "https://music.youtube.com/search?" + urllib.parse.urlencode({"q": query})

driver.get(url)

buttons = None

while buttons is None or len(buttons) == 0:
    sleep(1)
    buttons = driver.find_elements_by_class_name("ytmusic-chip-cloud-chip-renderer")
    print("======================")

filter_by_songs = buttons[0]

filter_by_songs.click()

css_selector = "ytmusic-responsive-list-item-renderer.style-scope:nth-child(1) > div:nth-child(2) > ytmusic-item-thumbnail-overlay-renderer:nth-child(5) > div:nth-child(2) > ytmusic-play-button-renderer:nth-child(1) > div:nth-child(1) > yt-icon:nth-child(1)"

res = driver.find_element_by_css_selector(css_selector)

res.click()

song_url = driver.current_url
## https://music.youtube.com/watch?v=1wYNFfgrXTI&list=RDAMVM1wYNFfgrXTI
pos = song_url.find("&list")
if pos != -1:
    song_url = song_url[:pos]

subprocess.run(
    [
        "youtube-dl",
        "-f",
        "bestaudio",
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        song_url,
    ],
    check=True,
)
