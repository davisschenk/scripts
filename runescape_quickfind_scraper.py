import requests
import bs4
import argparse
import fileinput
import sys
import time
import re

def get_posts(category, page):
    URL = f"{category.strip()},goto,{page}"
    print(URL, file=sys.stderr)

    
    r = requests.get(URL, timeout=10)
    r.raise_for_status()

    bs = bs4.BeautifulSoup(r.text, "html.parser")

    for post in bs.find_all("a", attrs={"class": "thread-plate__main-link thread-plate__main-link--forumview"}):
        link = post["href"]
        count = post.find("span", attrs={"class": "thread-plate__total-posts"}).text

        print(f"https://secure.runescape.com/m=forum/sl=0/{link} - {count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", metavar="FILE", nargs="*", help="Files to read, if empty use stdin")

    args = parser.parse_args()

    for category in fileinput.input(files=args.files or "-"):
        for page in range(50):
            try:
                get_posts(category, page+1)
            except Exception as e:
                print(f"Exception occured sleeping before retrying: {e}", file=sys.stderr)
                time.sleep(60)
                get_posts(category, page+1)
