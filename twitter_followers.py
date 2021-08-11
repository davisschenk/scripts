import string
import sys
import time
import requests
import argparse

bearer_token = "<token>"


def countdown(seconds, out=sys.stderr):
    for remaining in range(seconds, 0, -1):
        print(f"Sleeping for {remaining} seconds   ", file=out, end="\r", flush=True)
        time.sleep(1)
    print()


class Twiiter:
    def __init__(self, bearer_token):
        self.bearer_token = bearer_token

    def get(self, *args, **kwargs):
        headers = {
            "Authorization": f"Bearer {self.bearer_token}"
        }

        headers.update(kwargs.get("headers", {}))
        kwargs["headers"] = headers

        r = requests.get(*args, **kwargs)

        if int(r.headers["x-rate-limit-remaining"]) <= 0:
            countdown(int(r.headers["x-rate-limit-reset"]) - int(time.time()) + 3)

        return r


def get_id(args, twitter):
    if args.id:
        yield None, args.id

    if args.username:
        r = twitter.get(f"https://api.twitter.com/2/users/by/username/{args.username}")
        print(args.username)
        yield args.username, r.json().get("data", []).get("id")

    if args.id_file:
        for i in args.id_file:
            yield None, i.strip()

    if args.username_file:
        for i in args.username_file:
            r = twitter.get(f"https://api.twitter.com/2/users/by/username/{i.strip()}")

            yield i.strip(), r.json().get("data", []).get("id")


def clean(t):
    return ''.join(filter(lambda c: c in string.printable, t)).translate(str.maketrans("\r", " "))


def run(args):
    twitter = Twiiter(args.token)

    for username, user_id in get_id(args, twitter):
        print(f"Getting {username=} {user_id=}")
        if user_id is None:
            print(f"Failed to get user: {username}", file=sys.stderr)
            continue
        pagination = None
        results = 0

        while pagination or results == 0:
            r = twitter.get(f"https://api.twitter.com/2/users/{user_id}/followers", params={"max_results": args.max_results, "pagination_token": pagination, "user.fields": "description,name,username"})

            if r.status_code == 429:
                continue

            try:
                j = r.json()
                r.raise_for_status()
            except (ValueError, requests.HTTPError) as e:
                print(f"Exception occurred, retrying: {e}")
                continue

            if j.get("data") is None:
                print("No Data. Retrying: ", j, file=sys.stderr)
                countdown(60)

            for user in j["data"]:
                results += 1
                print(args.format.format(name=clean(user["name"]), description=clean(user["description"].replace("\n", "\\n")), username=user["username"]), file=sys.stdout)

            print(f"Got {results} users", file=sys.stderr)
            pagination = j["meta"].get("next_token")


if __name__ == "__main__":
    twitter = Twiiter(bearer_token)
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="Subcommands")

    run_parser = subparsers.add_parser("run")
    user_group = run_parser.add_mutually_exclusive_group(required=True)
    user_group.add_argument("--id")
    user_group.add_argument("--username")
    user_group.add_argument("--id-file", type=argparse.FileType("r"))
    user_group.add_argument("--username-file", type=argparse.FileType("r"))

    run_parser.add_argument("--token", default=bearer_token)
    run_parser.add_argument("--max-results", default=1000)
    run_parser.add_argument("--format", default='{name} "{description}" @{username}', help="Format string to specify output, takes [name, username, description]")
    run_parser.set_defaults(func=run)

    arguments = parser.parse_args()
    arguments.func(arguments)
