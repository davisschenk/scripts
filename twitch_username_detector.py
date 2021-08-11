import argparse
import datetime
import itertools
import json
import os
import re
import sqlite3
import sys
import time
import concurrent.futures as cf
import requests

# https://dev.twitch.tv/console/apps/create
USER_ENDPOINT = "https://api.twitch.tv/helix/users"


def progressbar(it, prefix="", size=60, file=sys.stdout, count=None, multiplier=1):
    def show(j):
        x = int(size * j / count)
        file.write("%s[%s%s] %i/%i\r" % (prefix, "#" * x, "." * (size - x), j, count))
        file.flush()

    show(0)
    for i, item in enumerate(it):
        yield item
        show((i + 1) * multiplier)
    file.write("\n")
    file.flush()


class Twitch:
    def __init__(self, client_id, client_secret, secret_json="secrets.json"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.secret_json = secret_json

        self.rate_limit_max = None
        self.rate_limit_remaining = None
        self.rate_limit_reset = None

        self.attempts = 0
        if os.path.isfile(secret_json):
            with open(secret_json, "r") as r:
                secrets = json.load(r)
                self.token_expire = datetime.datetime.fromisoformat(secrets.get("expires"))
                self.token = secrets.get("token")
        else:
            self.token = None
            self.token_expire = None

    def get_access_token(self):
        if self.token is not None and datetime.datetime.now() < self.token_expire:
            return self.token

        r = requests.post("https://id.twitch.tv/oauth2/token", params={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        })
        r.raise_for_status()
        j = r.json()
        self.token = j["access_token"]
        self.token_expire = datetime.datetime.now() + datetime.timedelta(seconds=j["expires_in"])

        with open(self.secret_json, "w") as w:
            json.dump({
                "expires": self.token_expire.isoformat(),
                "token": self.token
            }, w)

        return self.token

    def get(self, *args, **kwargs):
        header = {
            "Client-Id": self.client_id,
            "Authorization": f"Bearer {self.get_access_token()}"
        }
        kwargs.update(headers=header)

        r = requests.get(*args, **kwargs)
        if r.status_code not in [429, 200] and self.attempts < 5:
            self.attempts += 1
            return self.get(*args, **kwargs)

        self.rate_limit_max = int(r.headers["Ratelimit-Limit"])
        self.rate_limit_remaining = int(r.headers["Ratelimit-Remaining"])
        self.rate_limit_reset = datetime.datetime.fromtimestamp(int(r.headers["Ratelimit-Reset"]))

        if self.rate_limit_remaining <= 0:
            print("Sleeping: ", (self.rate_limit_reset - datetime.datetime.utcnow()).seconds)
            time.sleep((self.rate_limit_reset - datetime.datetime.utcnow()).seconds)

        if r.status_code == 429:
            self.attempts += 1
            return self.get(*args, **kwargs)

        r.raise_for_status()
        self.attempts = 0
        return r


def grouper(n, iterable):
    iterable = iter(iterable)
    return iter(lambda: list(itertools.islice(iterable, n)), [])


def setup_db(args):
    cur = args.database.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            ID int UNSIGNED PRIMARY KEY, 
            username varchar(254) NOT NULL COLLATE NOCASE,
            display_name varchar (254) NOT NULL COLLATE NOCASE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users_username_changes (
            ID int PRIMARY KEY,
            userID int UNSIGNED NOT NULL,
            username_old varchar(254) COLLATE NOCASE,
            username_new varchar(254) COLLATE NOCASE,
            found_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users_display_name_changes (
            ID int PRIMARY KEY,
            userID int UNSIGNED NOT NULL,
            username_old varchar(254) COLLATE NOCASE,
            username_new varchar(254) COLLATE NOCASE,
            found_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
       CREATE TRIGGER IF NOT EXISTS username_change AFTER UPDATE on users FOR EACH ROW
       WHEN NEW.username != OLD.username
       BEGIN
            INSERT INTO users_username_changes(userID,username_old,username_new) VALUES (NEW.id,OLD.username,NEW.username);
       END;
    """)

    cur.execute("""
       CREATE TRIGGER IF NOT EXISTS display_name_change AFTER UPDATE on users FOR EACH ROW
       WHEN NEW.display_name != OLD.display_name
       BEGIN
            INSERT INTO users_display_name_changes(userID,username_old,username_new) VALUES (NEW.id,OLD.display_name,NEW.display_name);
       END;
    """)

    print("Setup DB")


def get_ids(file, pattern):
    with open(file) as r:
        for line in r:
            match = re.search(pattern, line)
            if match:
                yield match.group("id"), match.group("username")


def load_file(args):
    twitch = Twitch(args.client, args.secret)
    cursor = args.database.cursor()

    ids = list(get_ids(args.file, args.pattern))
    for i,users in enumerate(progressbar(grouper(100, ids), count=len(ids)//100)):
        get_users(twitch, cursor, users)

        if i % 100 == 0:
            args.database.commit()
    args.database.commit()


def users_to_urls(users):
    return f"{USER_ENDPOINT}?{'&'.join(f'id={int(i[0])}' for i in users)}"


def get_users(twitch, cursor, users):
    try:
        r = twitch.get(users_to_urls(users))
    except Exception as e:
        return print(f"Error getting {users}: {e}")

    for entry in r.json()["data"]:
        cursor.execute("""
            INSERT INTO users(ID,username,display_name) VALUES (?,?,?) 
            ON CONFLICT(ID) DO UPDATE SET username=excluded.username,display_name=excluded.display_name;
        """, (entry["id"], entry["login"], entry["display_name"]))


def check_twitch(args):
    twitch = Twitch(args.client, args.secret)
    read_cur = args.database.cursor()
    edit_cur = args.database.cursor()

    read_cur.execute("SELECT ID from users")
    ids = read_cur.fetchall()

    for i, users in enumerate(progressbar(grouper(100, ids), count=len(ids)//100)):
        get_users(twitch, edit_cur, users)

        if i % 100 == 0:
            args.database.commit()
    args.database.commit()


def get_changes(changes_l):
    c = []
    for i, change in enumerate(changes_l):
        c.append(change[2])
        if i == len(changes_l) - 1:
            c.append(change[3])

    return c


def changes(args):
    cursor = args.database.cursor()

    cursor.execute("SELECT * FROM users_username_changes WHERE userID=?", (args.id,))
    username_changes = cursor.fetchall()
    username_changes.sort(key=lambda x: datetime.datetime.fromisoformat(x[4]))

    cursor.execute("SELECT * FROM users_display_name_changes WHERE userID=?", (args.id,))
    display_changes = cursor.fetchall()
    display_changes.sort(key=lambda x: datetime.datetime.fromisoformat(x[4]))

    print("Username Changes:")
    for i, c in enumerate(get_changes(username_changes)):
        print(f"\t{i+1}: {c}")
    print()
    print("Display Name Changes")
    for i, c in enumerate(get_changes(display_changes)):
        print(f"\t{i + 1}: {c}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=sqlite3.connect, default="twitch.db")
    subparsers = parser.add_subparsers(title="Subcommands")

    setup_parser = subparsers.add_parser("setup")
    setup_parser.set_defaults(func=setup_db)

    load_parser = subparsers.add_parser("load")
    load_parser.add_argument("file", help="A file to read usernames and ids from")
    load_parser.add_argument("--client", help="Twitch Developer ClientID")
    load_parser.add_argument("--secret", help="Twitch Developer Secret")
    load_parser.add_argument("--pattern", help="A regex pattern with named capture groups for `username` and `id` "
                                               "which applied on each line of the file", default=r"^(?P<username>["
                                                                                                 r"^:]+)\:(?P<id>["
                                                                                                 r"0-9]+)\:.+$")
    load_parser.set_defaults(func=load_file)

    twitch_parser = subparsers.add_parser("check")
    twitch_parser.add_argument("--client", help="Twitch Developer ClientID")
    twitch_parser.add_argument("--secret", help="Twitch Developer Secret")
    twitch_parser.set_defaults(func=check_twitch)

    twitch_parser = subparsers.add_parser("changes")
    twitch_parser.add_argument("id", type=int)
    twitch_parser.set_defaults(func=changes)

    arguments = parser.parse_args()
    arguments.func(arguments)
