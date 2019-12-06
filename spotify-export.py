# -*- coding: utf-8 -*-
""" Export your Deezer playlists as JSON

This module spins up a server to perform authentication to a
Deezer app (see Readme) through oauth2 protocol and then uses
the official Deezer API to retrieve
and save as JSON file all your playlists.
"""

import os
import time
import webbrowser
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import requests

APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
USER_ID = os.environ.get("USER_ID")


def get_playlist(token, playlist_id):
    """
    Use Deezer API to get a playlist from its id.
    The only information returned about each playlist is the name and tracklist (a track is described
    by the name of the artist/band, the name of the album and the title.

    Args:
        token (string): The token given by Deezer to authenticate requests
        playlist_id (string): The id of the playlist to get

    Returns:
        A dictionary representing the playlist 
    """
    req = requests.get("https://api.deezer.com/playlist/{}&access_token={}".format(playlist_id, token))
    playlist_item = req.json()
    playlist = dict([('name', playlist_item['title']), ('songs', list())])
    for title in playlist_item['tracks']['data']:
        song = dict(
            [
                ('title', title['title']),
                ('artist', title['artist']['name']),
                ('album', title['album']['title'])
            ]
        )
        playlist['songs'].append(song)

    return playlist

def save_all_playlists(token):
    """
    Use Deezer API to get all user playlists and save each one in its own file as JSON.
    The only information saved about each playlist is the name and tracklist (a track is described
    by the name of the artist/band, the name of the album and the title.

    Args:
        token (string): The token given by Deezer to authenticate requests

    Returns:
        None
    """


    endpoint = "https://api.spotify.com/v1/users/USER_ID/playlists?limit=50"
    

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json", 
        "Authorization": "Bearer " + token
    }

    print(requests.get(endpoint,  headers=headers).json())
    print()
    print()

    for playlist in requests.get(endpoint,  headers=headers).json()['items']:
        print(playlist.get('name'), playlist.get('id'))

        url = "https://api.spotify.com/v1/playlists/{}/tracks".format(playlist.get('id'))
        tracks = requests.get(url,  headers=headers).json()
        for track in tracks.get('items'):
            name = track.get('track').get('name')

            print("\t {}".format(name))
            
            

    exit()
    
    req = requests.get("https://api.deezer.com/user//playlists&access_token={}".format(token))
    playlists = list()

    for item_playlist in req.json()['data']:
        playlist_id = item_playlist['id']
        playlist = get_playlist(token, playlist_id)
        
        playlists.append(playlist)

    directory = 'playlists_{}'.format(time.time())
    if not os.path.exists(directory):
        os.makedirs(directory)

    for index, playlist in enumerate(playlists):
        filename = os.path.join(directory, '{}.json'.format(index))
        with open(filename, 'w') as file_descriptor:
            json.dump(playlist, file_descriptor)
            file_descriptor.close()


class Server(BaseHTTPRequestHandler):
    """Basic HTTP Server to serve as redirection URI and obtain the token from Deezer
    """
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        if self.path.startswith('/callback?code='):
            code = self.path.split('=')[1]
            print("Found code: {}".format(code))
            print('Attempting to obtain token...')

            endpoint = "https://accounts.spotify.com/api/token"

            payload = {
                'grant_type' : "authorization_code",
                'redirect_uri' : "http://localhost:5000/callback",
                'code' : code,
                'client_id' : APP_ID,
                'client_secret' : APP_SECRET
            }
            
            
            print(endpoint)
            time.sleep(5)
            req = requests.post(endpoint, data=payload)
            access_token = req.json().get('access_token')
            print(access_token)
            time.sleep(5)

            save_all_playlists(access_token)

        self._set_headers()
        self.wfile.write(
            "<html><body><h1>hi!</h1>" \
            "<script>alert('You can now close this page')</script></body></html>".encode()
        )

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        # Doesn't do anything with posted data
        self._set_headers()
        self.wfile.write("<html><body><h1>POST!</h1></body></html>".encode())

def run(port=5000):
    """ Run a HTTP server and listen
    Args:
        port (int): The port on which to listen. Should match the port in your Deezer app config.
    """
    server_address = ('', port)
    httpd = HTTPServer(server_address, Server)
    print('Starting httpd...')
    httpd.serve_forever()


if __name__ == "__main__":

    if not APP_ID or not APP_SECRET:
        raise Exception(
            "APP_ID and APP_SECRET environement variables must be defined!" \
            "- See Readme for more information on this issue."
        )
    HTTP_SERVER = Thread(target=run, daemon=True)
    HTTP_SERVER.start()


    response_type = 'code'
    redirect_uri = 'http://localhost:5000/callback'
#    scope = 'user-read-private user-read-email user-read-playback-state user-read-currently-playing user-library-read playlist-read-collaborative playlist-read-private'#['user-read-private', 'playlist-read-private', 'playlist-read-collaborative', 'user-read-email', 'user-library-read', 'user-read-private', 'user-read-private', 'user-top-read', 'user-follow-read']
    scope = "playlist-read-private playlist-read-collaborative"

    url = "https://accounts.spotify.com/authorize?client_id={}&response_type={}&redirect_uri={}&scope={}&username={}".format(APP_ID, response_type, redirect_uri, scope, "USER_ID")
    
    webbrowser.open(url)
    HTTP_SERVER.join()
