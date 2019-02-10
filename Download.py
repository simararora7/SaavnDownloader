import ast
import base64
import html
import json
import os
import re
import urllib.request

import logger
import requests
import urllib3.request
from bs4 import BeautifulSoup
from mutagen.mp4 import MP4, MP4Cover
from pySmartDL import SmartDL
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from pyDes import *

urllib3.disable_warnings()
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:49.0) Gecko/20100101 Firefox/49.0'
}

def get_decipher():
    return des(b"38346591", ECB, b"\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)

def add_tags(filename, json_data, playlist_name):
    audio = MP4(filename)
    audio['\xa9nam'] = str(json_data['song'])
    audio['\xa9ART'] = str(json_data['primary_artists'])
    audio['\xa9alb'] = str(json_data['album'])
    audio['aART'] = str(json_data['singers'])
    audio['\xa9wrt'] = str(json_data['music'])
    audio['desc'] = str(json_data['starring'])
    audio['\xa9gen'] = str(playlist_name)
    audio['\xa9day'] = str(json_data['year'])
    audio['cprt'] = str(json_data['label'])
    cover_url = json_data['image'][:-11] + '500x500.jpg'
    fd = urllib.request.urlopen(cover_url)
    cover = MP4Cover(fd.read(), getattr(MP4Cover, 'FORMAT_PNG' if cover_url.endswith('png') else 'FORMAT_JPEG'))
    fd.close()
    audio['covr'] = [cover]
    audio.save()

def download_songs(songs_json):
    des_cipher = get_decipher()
    for song in songs_json['songs']:
        try:
            enc_url = base64.b64decode(song['encrypted_media_url'].strip())
            dec_url = des_cipher.decrypt(enc_url, padmode=PAD_PKCS5).decode('utf-8')
            dec_url = dec_url.replace('_96.mp4', '_320.mp4')
            filename = html.unescape(song['song']) + '.m4a'
            filename = filename.replace("\"", "'")
        except Exception as e:
            logger.error(str(e))
        try:
            location = os.path.join(os.path.sep, os.getcwd(), "songs", filename)
            if os.path.isfile(location):
               print("{0} already downloaded".format(filename))
            else :
                print("Downloading {0}".format(filename))
                obj = SmartDL(dec_url, location)
                obj.start()
                name = songs_json['name'] if ('name' in songs_json) else songs_json['listname']
                add_tags(location, song, name)
        except Exception as e:
             logger.error(str(e))

def get_songs(url):
    songs_json = []
    respone = requests.get(url, verify=False, headers=headers)
    if respone.status_code == 200:
        songs_json = list(filter(lambda x: x.startswith("{"), respone.text.splitlines()))[0]
        songs_json = json.loads(songs_json)
    return songs_json

def get_playlist_songs(list_id):
    return get_songs('https://www.saavn.com/api.php?listid={0}&_format=json&__call=playlist.getDetails'.format(list_id))

def get_album_songs(album_id):
    return get_songs('https://www.saavn.com/api.php?_format=json&__call=content.getAlbumDetails&albumid={0}'.format(album_id))

if __name__ == '__main__':
    input_url = input('Enter Playlist/Album Url:').strip()
    try:
        res = requests.get(input_url, headers=headers)
    except Exception as e:
        logger.error(str(e))
    
    soup = BeautifulSoup(res.text, "lxml")

    try:
        playlist_id = soup.select(".flip-layout")[0]["data-listid"]
        if playlist_id is not None:
            print("Downloading songs from playlist {0}".format(playlist_id))
            download_songs(get_playlist_songs(playlist_id))
            sys.exit()
    except Exception as e:
        print("No Playlist Found")
    try:
        album_id = soup.select(".play")[0]["onclick"]
        album_id = ast.literal_eval(re.search("\[(.*?)\]", album_id).group())[1]
        if album_id is not None:
            print("Downloading songs from album {0}".format(album_id))
            download_songs(get_album_songs(album_id))
            sys.exit()
    except Exception as e:
        print("No Album Found")


