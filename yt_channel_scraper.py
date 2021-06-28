import argparse
import sys
import fileinput
import requests
import re

API_TOKEN = "[lol token goes here]"
URL_REGEX = re.compile(r"https://www\.youtube\.com/"
                       r"((c/(?P<customURL>[a-zA-Z0-9-_]+))|"
                       r"(channel/(?P<channelID>[a-zA-Z0-9-_]+))|"
                       r"((user/)?(?P<user>[a-zA-Z0-9-_]+)))/videos")


class GoogleAPI:
    YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
    YOUTUBE_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
    YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

    def __init__(self, token):
        self.quota = 0
        self.token = token

    def request(self, url, params=None):
        params = {} or params
        params["key"] = self.token

        r = requests.get(url, params=params, timeout=10)

        if url == self.YOUTUBE_SEARCH_URL:
            self.quota += 50
        else:
            self.quota += 1

        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            if r.status_code == 403:
                print(f"API Forbidden: {e} {r.json()}", file=sys.stderr)
                sys.exit(1)
            elif r.status_code == 404:
                print(f"404 Error: {e}", file=sys.stderr)
                return None
            raise e
        return r.json()


class VideoScraper:
    def __init__(self, token):
        self.api = GoogleAPI(token)

    def get_uploads_playlist(self, custom_url):
        url = URL_REGEX.match(custom_url)

        if url.group("customURL"):
            return self._get_playlist_id_for_custom_url(url.group("customURL"))
        elif url.group("channelID"):
            return self._get_channels(channel_id=url.group("channelID"))
        elif url.group("user"):
            return self._get_channels(username=url.group("user"))

    def _get_playlist_id_for_custom_url(self, custom_url):
        raw_search = self.api.request(
            GoogleAPI.YOUTUBE_SEARCH_URL,
            params={"part": "id", "type": "channel", "q": custom_url, "maxResults": 50}
        )

        if raw_search is None:
            return None

        for result in raw_search["items"]:
            channel_id = result["id"]["channelId"]

            channel = self._get_channels(channel_id=channel_id, custom_url=custom_url)
            if channel:
                return channel

    def _get_channels(self, username=None, channel_id=None, custom_url=None):
        raw_channel = self.api.request(
            GoogleAPI.YOUTUBE_CHANNELS_URL,
            params={"forUsername": username, "id": channel_id, "part": "contentDetails,snippet"}
        )

        if raw_channel is None:
            return None

        if custom_url:
            for channel in raw_channel["items"]:
                if channel["snippet"].get("customUrl") == custom_url.lower():
                    return channel["contentDetails"]["relatedPlaylists"]["uploads"]
        elif raw_channel["pageInfo"]["totalResults"] != 0:  # Not a custom URL and we found something
            return raw_channel["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    def get_videos(self, url):
        playlist_id = self.get_uploads_playlist(url)

        if playlist_id is None:
            print(f"Failed to get videos for {url}", file=sys.stderr)
            return
        next_token = None
        results_gathered = 0

        while next_token or results_gathered == 0:
            uploads = self.api.request(
                GoogleAPI.YOUTUBE_PLAYLIST_ITEMS_URL,
                params={"playlistId": playlist_id, "part": "snippet,contentDetails", "maxResults": 50, "pageToken": next_token}
            )
            if uploads is None:
                print(f"Failed to get videos for {url}", file=sys.stderr)
                return

            next_token = uploads.get("nextPageToken")

            for video in uploads.get("items", []):
                results_gathered += 1
                yield video["contentDetails"]["videoId"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", metavar="FILE", nargs="*", help="Files to read, if empty use stdin")

    args = parser.parse_args()
    scraper = VideoScraper(API_TOKEN)

    for url in fileinput.input(files=args.files or "-"):
        url = url.strip()

        for index, video in enumerate(scraper.get_videos(url), start=1):
            print(f"https://youtube.com/watch?v={video}")
            sys.stderr.write(f"Captured {index} video URLs from {url}\r")
        print(file=sys.stderr)

    print(f"Quota Used: {scraper.api.quota}", file=sys.stderr)
