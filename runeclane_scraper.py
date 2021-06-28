import sys
import fileinput
import argparse
import requests
import bs4

url = "https://www.runeclan.com/user/{name}"
output_format = "{name} - {xp} - {date} - {previous}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", metavar="FILE", nargs="*", help="Files to read, if empty use stdin")

    args = parser.parse_args()

    for name in fileinput.input(files=args.files or "-"):
        name = name.strip()

        r = requests.get(url.format(name=name))
        r.raise_for_status()
        b = bs4.BeautifulSoup(r.text, "html.parser")

        xp = b.find("td", {"class": "xp_tracker_cxp"})
        date = b.find("div", {"class": "xp_tracker_activity_r"})
        previous = b.find("div", {"class": "xp_tracker_prevnames"})

        if (xp, date, previous) == (None, None, None):
            print(f"{name} - Not Tracking")
        else:
            if previous:
                previous = previous.text.strip("Previous Name: ")

            print(output_format.format(name=name, xp=xp.text, date=date.text, previous=previous or ""))
