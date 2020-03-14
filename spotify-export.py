# -*- coding: utf-8 -*-
""" Download your favorite songs from your Spotify account

This module spins up a server to perform authentication to a
Spotify app (see Readme) through oauth2 protocol, then uses
the official Spotify API to retrieve  all your playlists.
Finally it downloads the playlist using youtube-dl.
"""

import os
import time
import webbrowser
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from queue import Queue
import requests

APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
USER_ID = os.environ.get("USER_ID")
PLAYLIST_DIR = "{}/.cache/spotify-to-mp3/playlists/".format(os.environ.get("HOME"))


class Worker(Thread):
    """ Thread executing tasks from a given task queue """

    def __init__(self, tasks):
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()

    def run(self):
        while True:
            func, args = self.tasks.get()
            try:
                func(*args)
            except Exception as error:
                # An exception happened while executing
                print(error)
            finally:
                # Mark this task as done, whether an exception happened or not
                self.tasks.task_done()


class ThreadPool:
    """ Pool of threads consuming tasks from a queue """

    def __init__(self, num_threads):
        self.tasks = Queue(num_threads)
        for _ in range(num_threads):
            Worker(self.tasks)

    def map(self, func, arg_list):
        """ Add a list of tasks to the queue """
        for args in arg_list:
            self.tasks.put((func, args))

    def wait_completion(self):
        """ Wait for completion of all tasks in the queue """
        self.tasks.join()


def get_headers(token):
    """ Return a dict containing headers necessary to make a request on Spotify API endpoints """
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token,
    }


def get_playlist(token, playlist_id, playlist_name):
    """
    Use Spotify API to get a playlist from its id.
    The only information returned about each playlist is the name and tracklist (a track is described
    by the name of the artist/band, the name of the album and the title.

    Args:
        token (string): The token given by Spotify to authenticate requests
        playlist_id (string): The id of the playlist to get

    Returns:
        A dictionary representing the playlist 
    """
    endpoint = "https://api.spotify.com/v1/playlists/{}/tracks".format(playlist_id)
    headers = get_headers(token)

    playlist_item = requests.get(endpoint, headers=headers).json()
    playlist = dict([("name", playlist_name), ("songs", list())])

    for track in playlist_item.get("items"):
        song = dict(
            [
                ("title", track.get("track").get("name")),
                ("artist", [a.get("name") for a in track.get("track").get("artists")]),
                ("album", track.get("track").get("album").get("name")),
                ("album_art_url", track.get("track").get("album").get("images")[0].get("url")),
                ("duration_ms", track.get("track").get("duration_ms"))
            ]
        )
        playlist["songs"].append(song)

    filename = os.path.join(PLAYLIST_DIR, "{}.json".format(playlist_name))
    with open(filename, "w") as file_descriptor:
        json.dump(playlist, file_descriptor)
        file_descriptor.close()

    print(playlist)


def save_all_playlists(token):
    """
    Use Spotify API to get all user playlists and save each one in its own file as JSON.
    The only information saved about each playlist is the name and tracklist (a track is described
    by the name of the artist/band, the name of the album and the title.

    Args:
        token (string): The token given by Spotify to authenticate requests

    Returns:
        None
    """

    headers = get_headers(token)
    offset = 0
    limit = 50

    while True:
        endpoint = "https://api.spotify.com/v1/users/{}/playlists?limit={}&offset={}".format(
            USER_ID, limit, offset
        )
        playlists_data = requests.get(endpoint, headers=headers).json()["items"]

        offset += limit

        if len(playlists_data) == 0:
            break

        pool = ThreadPool(len(playlists_data))
        pool.map(
            get_playlist,
            zip(
                [token for _ in range(len(playlists_data))],
                [p.get("id") for p in playlists_data],
                [p.get("name") for p in playlists_data],
            ),
        )
        pool.wait_completion()



class Server(BaseHTTPRequestHandler):
    """Basic HTTP Server to serve as redirection URI and obtain the token from Deezer
    """

    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/callback?code="):
            code = self.path.split("=")[1]
            print("Found code: {}".format(code))
            print("Attempting to obtain token...")

            endpoint = "https://accounts.spotify.com/api/token"

            payload = {
                "grant_type": "authorization_code",
                "redirect_uri": "http://localhost:5000/callback",
                "code": code,
                "client_id": APP_ID,
                "client_secret": APP_SECRET,
            }

            print(endpoint)
            time.sleep(5)
            req = requests.post(endpoint, data=payload)
            access_token = req.json().get("access_token")

            self._set_headers()
            self.wfile.write(
                "<html><body><h1>hi!</h1>"
                "<script>alert('You can now close this page')</script></body></html>".encode()
            )

            print(access_token)
            time.sleep(5)

            playlist_manager = Thread(
                target=save_all_playlists, daemon=True, kwargs={"token": access_token}
            )
            playlist_manager.start()

    #      save_all_playlists(access_token)

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
    server_address = ("", port)
    httpd = HTTPServer(server_address, Server)
    print("Starting httpd...")
    httpd.serve_forever()


if __name__ == "__main__":
    if not APP_ID or not APP_SECRET or not USER_ID:
        raise Exception(
            "APP_ID, APP_SECRET and USER_ID environement variables must be defined!"
            "- See Readme for more information on this issue."
        )


    # Create a directory to store the playlist data
    if not os.path.exists(PLAYLIST_DIR):
        os.makedirs(PLAYLIST_DIR)

    
    HTTP_SERVER = Thread(target=run, daemon=True)
    HTTP_SERVER.start()

    response_type = "code"
    redirect_uri = "http://localhost:5000/callback"
    #    scope = 'user-read-private user-read-email user-read-playback-state user-read-currently-playing user-library-read playlist-read-collaborative playlist-read-private'#['user-read-private', 'playlist-read-private', 'playlist-read-collaborative', 'user-read-email', 'user-library-read', 'user-read-private', 'user-read-private', 'user-top-read', 'user-follow-read']
    scope = "playlist-read-private playlist-read-collaborative"

    url = "https://accounts.spotify.com/authorize?client_id={}&response_type={}&redirect_uri={}&scope={}&username={}".format(
        APP_ID, response_type, redirect_uri, scope, "USER_ID"
    )

    webbrowser.open(url)
    HTTP_SERVER.join()
