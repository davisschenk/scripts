import argparse
import requests
import bs4
import itertools
import re
import sys
import concurrent.futures as cf
url = "https://www.runescapescammer.com/runescape-scammed-accounts-list.html?per_page={page}"


def find_span(soup: bs4.BeautifulSoup, heading_text):
    heading = soup.find("span", attrs={"class": "specification-heading"}, text=heading_text)
    return heading.find_next("span")


def scrape_page(url):
    try:
        data_r = requests.get(url, timeout=5)
        data_r.raise_for_status()
    except Exception as e:
        print(f"Bad Request: {str(e)} for URL: {url}", file=sys.stderr)
        return {"error": e, "url": url}

    data_soup = bs4.BeautifulSoup(data_r.text, "html.parser")
    try:
        return {
            "login_name":  find_span(data_soup, "Login name").text,
            "paypal_email":  find_span(data_soup, "Paypal Email").text,
            "skype_id":  find_span(data_soup, "Skype ID").text,
            "bought_from":  find_span(data_soup, "Bought from").text,
            "reported_by":  find_span(data_soup, "Reported by").text,
            "date_uploaded":  find_span(data_soup, "Date uploaded").text,
            "what_happened":  find_span(data_soup, "What happened?").text,
            "url": url
        }
    except Exception as e:
        return {"error": e, "url": url}


def collect_urls(page_number):
    urls = set()
    home_r = requests.get(url.format(page=page_number), timeout=5)
    try:
        home_r.raise_for_status()
    except Exception as e:
        print(f"Bad Request: {str(e)}", file=sys.stderr)
    home_soup = bs4.BeautifulSoup(home_r.text, "html.parser")

    pages = home_soup.find_all("a", text="View Details")
    if not pages:
        return urls

    for page in pages:
        urls.add(page["href"])

    return urls


def progressbar(it, prefix="", size=60, file=sys.stdout, count=None):
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


def get_max_page():
    r = requests.get(url.format(page=""))
    soup = bs4.BeautifulSoup(r.text, "html.parser")

    return int(soup.select_one("body > div.wrap > div.content > div.section.group > div:nth-child(3) > font:nth-child(2)").text)


def print_results(result):
    print("-" * 50)
    print("Login:", result["login_name"])
    print("Paypal:", result["paypal_email"])
    print("Skype:", result["skype_id"])
    print("Bought from:", result["bought_from"])
    print("Reported by: ", result["reported_by"])
    print("Uploaded:", result["date_uploaded"])
    print("Description:", re.sub("\s\s+", " ", result["what_happened"]).replace("\n", " ").strip())



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Runescape Scammers")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=None)

    args = parser.parse_args()

    with cf.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(collect_urls, page_number) for page_number in range(args.start, (args.end or get_max_page()) * 20, 20)]
        urls = set()
        print("Collecting URLs...", file=sys.stderr)
        for complete in progressbar(cf.as_completed(futures), file=sys.stderr, count=len(futures)):
            results = complete.result()
            urls = urls.union(results)

        print(f"Collected {len(urls)}", file=sys.stderr)

    with cf.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(scrape_page, url) for url in urls]
        print("Scraping pages...", file=sys.stderr)
        failed = set()
        for complete in progressbar(cf.as_completed(futures), file=sys.stderr, count=len(futures)):
            result = complete.result()

            if "error" in result:
                failed.add(result["url"])
                continue

            print_results(result)

    if failed:
        print("Retrying failed...", file=sys.stderr)
        for fail in progressbar(failed, file=sys.stderr, count=len(failed)):
            r = scrape_page(fail)
            if "error" in r:
                print(f"Failed: {fail}", file=sys.stderr)
            else:
                print_results(result)





