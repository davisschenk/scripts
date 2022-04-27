import fileinput
import argparse
import requests
import bs4
import itertools
import sys

NAME_URL = "https://www.runeclan.com/user/{name}"
ID_URL = "https://www.runeclan.com/uid/{uid}"
output_format = "{name} - {xp} - {date} - {previous}"


def progressbar(it, prefix="", size=60, file=sys.stdout, count=None):
    count = count or len(it)

    def show(j):
        x = int(size*j/count)
        file.write("%s[%s%s] %i/%i\r" % (prefix, "#"*x, "."*(size-x), j, count))
        file.flush()
    show(0)
    for i, item in enumerate(it):
        yield item
        show(i+1)
    file.write("\n")
    file.flush()


def parse_page(url, name=None):
    r = requests.get(url)
    r.raise_for_status()
    b = bs4.BeautifulSoup(r.text, "html.parser")

    xp = b.find("td", {"class": "xp_tracker_cxp"})
    date = b.find("div", {"class": "xp_tracker_activity_r"})
    previous = b.find("div", {"class": "xp_tracker_prevnames"})
    if name is None:
        name = b.find("span", {"class": "xp_tracker_hname"})
        if name is None:
            return True
        else:
            name = name.text

    if previous:
        previous = previous.text.strip("Previous Name: ")

    print(output_format.format(name=name, xp=getattr(xp, "text", "Not Tracked"), date=getattr(date, "text", "Not Tracked"), previous=previous or ""))


def parse_names(args):
    for name in progressbar(fileinput.input(files=args.files or "-"), file=sys.stderr):
        name = name.strip()

        parse_page(NAME_URL.format(name=name), name=name)


def parse_ids(args):
    for i in progressbar(itertools.count(args.min) if args.max is None else range(args.min, args.max+1), count=args.max or 819864, file=sys.stderr):
        if parse_page(ID_URL.format(uid=i)):
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    name_parser = subparsers.add_parser("by_name")
    name_parser.add_argument("files", metavar="FILE", nargs="*", help="Files to read, if empty use stdin")
    name_parser.set_defaults(func=parse_names)

    id_parser = subparsers.add_parser("by_id")
    id_parser.add_argument("--min", type=int, default=1)
    id_parser.add_argument("--max", type=int)
    id_parser.set_defaults(func=parse_ids)

    args = parser.parse_args()
    args.func(args)

