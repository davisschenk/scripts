import argparse
import shutil
import pathlib
import requests
import os
import sys

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Content-Type": "application/x-www-form-urlencoded",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1"
}

client_id = "57390e1688f1bcb"

def progressbar(it, prefix="", size=60, file=sys.stdout):
    lines = [i for i in it]

    def show(j):
        x = int(size*j/len(lines))
        file.write("%s[%s%s] %i/%i\r" % (prefix, "#"*x, "."*(size-x), j, len(lines)))
        file.flush()
    show(0)
    for i, item in enumerate(lines):
        yield item
        show(i+1)
    file.write("\n")
    file.flush()


def download_file(url, output_dir):
    filename = url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        try:
            r.raise_for_status()
            with open(output_dir / (("removed-" if r.url.endswith("removed.png") else "") + filename), "wb") as f:
                shutil.copyfileobj(r.raw, f)
        except Exception as e:
            print(f"Failed to download: {url} because {e}", file=sys.stderr)


def download(args):
    for url in progressbar(args.FILE, file=sys.stderr):
        download_file(url.strip(), args.output_dir)


def delete(args):
    for url in progressbar(args.FILE, file=sys.stderr):
        delete_hash = url.strip().split("/")[-1]
        r = requests.delete(f"https://api.imgur.com/3/image/{delete_hash}", headers={"Authorization": f"Client-ID {client_id}"})

        try:
            r.raise_for_status()
        except Exception as e:
            print(f"Failed to delete: {url} because {e}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="Subcommands")

    capture = subparsers.add_parser("download")
    capture.add_argument("FILE", type=argparse.FileType("r"))
    capture.add_argument("--output_dir", type=pathlib.Path, default=".")
    capture.set_defaults(fn=download)

    remove = subparsers.add_parser("delete")
    remove.add_argument("FILE", type=argparse.FileType("r"))
    remove.set_defaults(fn=delete)

    args = parser.parse_args()
    args.fn(args)