#!/usr/bin/env python3

import argparse
import bs4
import requests
import json
import sys
import fileinput


URL = "https://www.nftinspect.xyz/collections/{nid}/members"


def get_ids(args):
    if args.id:
        yield from args.id
    elif args.files is not None:
        yield from map(str.strip, fileinput.input(files=args.files or "-"))


def get_handles(nid):
    try:
        r = requests.get(URL.format(nid=nid))
        r.raise_for_status()
        bs = bs4.BeautifulSoup(r.text, "html.parser")

        data = bs.find(id="__NEXT_DATA__")
        data = json.loads(data.text)
        members = data["props"]["pageProps"]["members"]
        for member in members:
            print(f"@{member['username']}")

        print(f"Scraped {len(members)} members!", file=sys.stderr)
    except Exception as e:
        print(f"Failed to scrape {nid}: {e}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    id_parser = parser.add_mutually_exclusive_group(required=True)
    id_parser.add_argument("--files", nargs="*", help="Files to read, if empty use stdin")
    id_parser.add_argument("--id", nargs="+", type=str)

    args = parser.parse_args()

    for nid in get_ids(args):
        get_handles(nid)
