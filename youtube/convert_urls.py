import requests
import fileinput
import re
import argparse
import sys
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", metavar="FILE", nargs="*", help="Files to read, if empty use stdin")

    args = parser.parse_args()

    for url in fileinput.input(files=args.files or "-"):
        url = url.strip()

        r = requests.get(url)
        try:
            r.raise_for_status()
            print(f"https://www.youtube.com/channel/{re.search(r'channel_id=([a-zA-Z0-9-_]+)', r.text).group(1)}/videos")
        except Exception as e:
            print(f"Failed to get: {url}", file=sys.stderr)
