import argparse
import string
import sys
import fileinput
import bs4
import requests
import re
import os
from contextlib import redirect_stdout
import time


base_url = "https://secure.runescape.com/m=forum/sl=0/forums?{code},goto,{page}"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"
}
code_re = re.compile(
    r"https?:\/\/secure\.runescape\.com\/m=forum\/sl=0\/forums\?((\d+,)+\d+).*( - (\d+))?"
)


def code_to_url(code):
    match = code_re.match(code)
    if match:
        code = match[1]

    code = code.strip().replace("-", ",")
    print(code, file=sys.stderr)
    return base_url.format(code=code, page="{page}")


def clean(t):
    return "".join(filter(lambda c: c in string.printable, t)).translate(
        str.maketrans("\r\n", "  ")
    )


def get_page(url, page, s_get_page=False, retry_count=0):
    try:
        r = requests.get(url.format(page=page), headers=headers)
        r.raise_for_status()
        bs = bs4.BeautifulSoup(r.text, "html.parser")

        names = bs.find_all("a", attrs={"class": "post-avatar__name-link"})
        posts = filter(
            lambda p: p.text != "The contents of this message have been hidden",
            bs.find_all("span", attrs={"class": "forum-post__body"}),
        )

        for name, post in zip(names, posts):
            text = clean(post.text)
            print(f"{name.text} - {text}")

        if s_get_page:
            page_n = bs.find("a", attrs={"class": "forum-pagination__top-last"})
            if page_n is None:
                return 1
            return int(page_n.text)

    except Exception as e:
        print(f"Failed page {page}: {e}", file=sys.stderr)

        if retry_count < 4:
            print(
                f"Retrying page {page} in {2**(retry_count+4)} seconds", file=sys.stderr
            )
            time.sleep(2 ** (retry_count + 4))
            get_page(url, page, s_get_page=s_get_page, retry_count=retry_count + 1)
        else:
            print(f"Permanently failed page {page}")


def from_code(args):
    url = code_to_url(args.code)
    last_page = get_page(url, args.start, s_get_page=True)

    for page in range(args.start + 1, args.end or (last_page + 1)):
        get_page(url, page)


def from_file(args):
    os.makedirs("out", exist_ok=True)
    for code in fileinput.input(files=args.files or "-"):
        url = code_to_url(code)
        file_name = code_re.match(url)[1].replace(",", "-")

        with open(f"out/{file_name}.txt", "w") as f:
            with redirect_stdout(f):
                last_page = get_page(url, 1, s_get_page=True) or 1

                for page in range(2, last_page + 1):
                    get_page(url, page)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parser for getting all usernames from a runescape forum thread"
    )

    subparsers = parser.add_subparsers()

    from_file_p = subparsers.add_parser("from_file")
    from_file_p.add_argument(
        "files", metavar="FILE", nargs="*", help="Files to read, if empty use stdin"
    )
    from_file_p.set_defaults(func=from_file)

    from_code_p = subparsers.add_parser("from_code")
    from_code_p.add_argument(
        "code", type=str, help="Enter quick find code, found on bottom of forum post"
    )
    from_code_p.add_argument("--start", type=int, default=1)
    from_code_p.add_argument("--end", type=int, default=None)
    from_code_p.set_defaults(func=from_code)

    args = parser.parse_args()
    args.func(args)
