import requests
import bs4
import argparse
import sys
import concurrent.futures as cf


urls = {
    "modern": "https://secure.runescape.com/m=hiscore/ranking?table={table}&page={page}",
    "oldschool": "https://secure.runescape.com/m=hiscore_oldschool/overall?table={table}&page={page}"
}

output_formats = {
    "tabulated": "{rank}\t{player}\t{level}\t{xp}\t{member}",
    "csv": "{rank},{player},{level},{xp},{member}",
    "pretty": "{rank:<6}{player:<25}{level:<7}{xp:<12}{member!s:<8}"
}

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}


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


def load_url(urlf, table, page):
    try:
        r = requests.get(urlf.format(table=table, page=page), headers=headers, timeout=30)
        r.raise_for_status()

        soup = bs4.BeautifulSoup(r.text, "html.parser")
        tbody = soup.find("tbody")

        if url == urls["oldschool"]:
            rows = tbody.find_all("tr", {"class": "personal-hiscores__row"})
        else:
            rows = tbody.find_all("tr")

        out = {"table": table, "page": page, "data": []}

        for row in rows:
            rank, player, level, xp = map(lambda t: t.text.strip(), row.find_all("td"))
            member = row.find("img", {"class": "memberIcon"}) is not None
            rank = int(rank.replace(",", ""))
            level = int(level.replace(",", ""))
            xp = int(xp.replace(",", ""))

            out["data"].append({"member": member, "rank": rank, "level": level, "xp": xp, "player": player})

        return out

    except Exception as e:
        print(r.text)
        return {"table": table, "page": page, "error": e}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Runescape Tables")
    parser.add_argument("--min", type=int, default=1, help="Starting page")
    parser.add_argument("--max", type=int, help="Ending page (inclusive)", required=True)
    parser.add_argument("--url", type=str.lower, help="Change the url to be used. Choose between `modern` (default) and `oldschool`. It is also possible to use a custom format string with {table} and {page}", default="modern")
    parser.add_argument("--table", type=int, help="Table number, formatted into url", default=0)
    parser.add_argument("--output", type=str.lower, help="Change the output format. Choose between `tabulated` (default), `csv` or `pretty`. It is also possible to use a custom format string with {rank}, {player}, {member}, {level} and {xp}", default="tabulated")
    parser.add_argument("--connections", type=int, default=25)

    args = parser.parse_args()

    url = urls.get(args.url, args.url)
    output_format = output_formats.get(args.output, args.output)

    print("Fetching Data", file=sys.stderr)

    if args.output == "csv":
        print("rank,player,level,xp,member")
    if args.output == "pretty":
        print(f"{'rank':<6}{'player':<25}{'level':<7}{'xp':<12}{'member':<8}")

    with cf.ThreadPoolExecutor(max_workers=args.connections) as executor:
        futures = [executor.submit(load_url, url, args.table, page) for page in range(args.min, args.max + 1)]
        data = []

        for complete in progressbar(cf.as_completed(futures), file=sys.stderr, count=len(futures)):
            result = complete.result()

            if "error" not in result:
                for player in result["data"]:
                    data.append(player)
            else:
                print(f"Failed to fetch page {result['page']}: {result['error']}", file=sys.stderr)

        print("Outputting Data", file=sys.stderr)
        for player in sorted(data, key=lambda p: p["rank"]):
            print(output_format.format(rank=player["rank"], player=player["player"], level=player["level"],
                                       xp=player["xp"], member=player["member"]))




