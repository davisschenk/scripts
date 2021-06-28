import requests
import fileinput
import re
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", metavar="FILE", nargs="*", help="Files to read, if empty use stdin")

    args = parser.parse_args()

    for url in fileinput.input(files=args.files or "-"):
        url = url.strip()

        r = requests.get(url)
        print(f"https://www.youtube.com/channel/{re.search(r'channel_id=([a-zA-Z0-9-_]+)', r.text).group(1)}/videos")
