#!/usr/bin/env python3
import argparse
import requests
import regex as re
import fileinput
import sys
import time

URL_REGEX = re.compile(r"(https?:\/\/www.(m\.)?youtube\.com)?\/(channel|c|user)\/([0-9a-zA-Z-_]+)(\/[0-9a-zA-Z-_]*)?")

def process(url, missed):
    url = url.strip()

    r = requests.get(url)
    try:
        r.raise_for_status()
        matches = URL_REGEX.findall(r.text, re.MULTILINE)
        yt_id = next(filter(lambda x: x[2] == "channel", matches), None)
        yt_custom = next(filter(lambda x: x[2] == "c", matches), None)
        yt_user = next(filter(lambda x: x[2] == "user", matches), None)


        print(f"https://www.youtube.com/channel/{yt_id[3]}" if yt_id else "N/A", end=" | ")
        print(f"https://www.youtube.com/user/{yt_user[3]}" if yt_user else "N/A", end=" | ")
        print(f"https://www.youtube.com/c/{yt_custom[3]}" if yt_custom else "N/A")
    except Exception as e:
        print(f"Failed to get({r.status_code}): {url} {e}", file=sys.stderr)
        missed.append(url)

        if r.status_code == 429:
            print("Sleeping 10 minutes", file=sys.stderr)
            time.sleep(60*10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", metavar="FILE", nargs="*", help="Files to read, if empty use stdin")

    args = parser.parse_args()

    missed = []
    for url in fileinput.input(files=args.files or "-"):
        process(url, missed)

    while missed:
        url = missed.pop()
        process(url, missed)
