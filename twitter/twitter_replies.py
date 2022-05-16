#!/usr/bin/env python3

import string
import sys
import time
import requests
import argparse

bearer_token = "AAAAAAAAAAAAAAAAAAAAAMJHSAEAAAAAZ8uhvHdPjlUGR7teoiMAXqgAhd4%3DDfYl59nkjIMtMZVSdEBOf5DUtI8slzE8xH9cLolPtIrGWmtul7"


def countdown(seconds, out=sys.stderr):
    for remaining in range(seconds, 0, -1):
        print(f"Sleeping for {remaining} seconds   ", file=out, end="\r", flush=True)
        time.sleep(1)
    print()


class Twitter:
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

def clean(t):
    return ''.join(filter(lambda c: c in string.printable, t)).translate(str.maketrans("\r\n", "  "))

def run(args):
    twitter = Twitter(args.token)

    results = 0
    pagination = None

    while pagination or results == 0:
        r = twitter.get("https://api.twitter.com/2/tweets/search/recent", params={
            "query": f"conversation_id:{args.id}",
            "max_results": str(args.max_results),
            "next_token": pagination,
            "user.fields": "name,username",
            "expansions": "author_id"
        })

        try:
            j = r.json()
            r.raise_for_status()
        except (ValueError, requests.HTTPError) as e:
            print(f"Exception occurred, retrying: {e}")
            continue


        if j.get("data") is None:
            print("No Data. Retrying: ", j, file=sys.stderr)
            countdown(60)

        tweets = {t["author_id"]: t for t in j["data"]}
        for user in j["includes"]["users"]:
            tweets[user["id"]].update(user)

        for tweet in tweets.values():
            results += 1
            print(args.format.format(display_name=clean(tweet["name"]), username=tweet["username"], message=clean(tweet["text"])))


        print(f"Got {results} tweets", file=sys.stderr)
        pagination = j["meta"].get("next_token")


def users(args):
    twitter = Twitter(args.token)

    r_results = 0
    t_results = 0
    q_results = 0
    t_pagination = None
    r_pagination = None
    q_pagination = None

    while t_pagination or r_results == 0:
        likes_r = twitter.get(f"https://api.twitter.com/2/tweets/{args.id}/liking_users", params={
                    "pagination_token": t_pagination,
                    "user.fields": "name,username",
                    "max_results": 100
                })

        try:
            likes = likes_r.json()
            likes_r.raise_for_status()
        except (ValueError, requests.HTTPError) as e:
            raise e
            print(f"Exception occurred, retrying: {e}", file=sys.stderr)
            continue

        for data in likes.get("data", []):
            r_results += 1
            print(data.get("username", ""))

        if likes["meta"]["result_count"] == 0:
            break

        t_pagination = likes["meta"].get("next_token")

    while r_pagination or t_results == 0:
        retweets_r = twitter.get(f"https://api.twitter.com/2/tweets/{args.id}/retweeted_by", params={
                    "pagination_token": r_pagination,
                    "user.fields": "name,username",
                    "max_results": 100
                })

        try:
            retweets = retweets_r.json()
            retweets_r.raise_for_status()
        except (ValueError, requests.HTTPError) as e:
            print(f"Exception occurred, retrying: {e}", file=sys.stderr)
            continue

        for data in retweets.get("data", []):
            t_results += 1
            print(data.get("username", ""))

        if retweets["meta"]["result_count"] == 0:
            break

        r_pagination = retweets["meta"].get("next_token")

    while q_pagination or q_results == 0:
        qtweets_r = twitter.get(f"https://api.twitter.com/2/tweets/{args.id}/quote_tweets", params={
                    "expansions": "author_id",
                    "pagination_token": q_pagination,
                    "user.fields": "name,username",
                    "max_results": 100
                })

        try:
            qtweets = qtweets_r.json()
            qtweets_r.raise_for_status()
        except (ValueError, requests.HTTPError) as e:
            print(f"Exception occurred, retrying: {e}", file=sys.stderr)
            continue

        for data in qtweets["includes"]["users"]:
            q_results += 1
            print(data.get("username", ""))

        if qtweets["meta"]["result_count"] == 0:
            break

        q_pagination = qtweets["meta"].get("next_token")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="Subcommands", required=True)

    run_parser = subparsers.add_parser("replies")
    user_group = run_parser.add_mutually_exclusive_group(required=True)
    user_group.add_argument("--id")

    run_parser.add_argument("--token", default=bearer_token)
    run_parser.add_argument("--max-results", default=100)
    run_parser.add_argument("--format", default='{display_name} - @{username} - {message}', help="Format string to specify output, takes [name, username, message]")
    run_parser.set_defaults(func=run)

    users_p = subparsers.add_parser("likes")
    users_p.add_argument("--id", required=True)
    users_p.add_argument("--token", default=bearer_token)
    users_p.set_defaults(func=users)

    arguments = parser.parse_args()
    arguments.func(arguments)
