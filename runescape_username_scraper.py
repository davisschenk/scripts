import requests
import bs4
import sys
import argparse

base_url = "https://secure.runescape.com/m=forum/sl=0/forums?{code},goto,{page}"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}


def code_to_url(code):
    return base_url.format(code=code.replace("-", ","), page="{page}")


def get_last_page(url):
    r = requests.get(url.format(page=1), headers=headers)
    bs = bs4.BeautifulSoup(r.text, "html.parser")
    last_element = bs.find("input", attrs={"id": "gotopage"})

    return int(last_element["max"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parser for getting all usernames from a runescape forum thread")
    parser.add_argument("code", type=str, help="Enter quick find code, found on bottom of forum post")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=None)

    args = parser.parse_args()
    url = code_to_url(args.code)
    last_page = get_last_page(url)

    for page in range(args.start, args.end or last_page):
        try:
            r = requests.get(url.format(page=page), headers=headers)
            r.raise_for_status()
            bs = bs4.BeautifulSoup(r.text, "html.parser")

            for name in bs.find_all("h3", attrs={"class": "post-avatar__name"}):
                print(name["data-displayname"])
        except Exception as e:
            print(f"Failed page {page}: {e}", file=sys.stderr)




