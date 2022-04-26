#!/usr/bin/env python3

import argparse
import imaplib
import email
from dataclasses import dataclass
from datetime import datetime
from bs4 import BeautifulSoup as bs
import sqlite3
import requests
import time
import sys
import dotenv
import os

dotenv.load_dotenv()



EMAIL = os.environ["EMAIL"]
PASSWORD = os.environ["PASSWORD"]
SERVER = os.environ["SERVER"]
ANTENNAS = {"gr5": "TPSGR5          NONE"}


@dataclass
class TconPos:
    x: float
    y: float
    z: float
    xu: float
    yu: float
    zu: float
    lat: (float, float, float)
    e_lon: (float, float, float)
    ellipsoid_height: float


@dataclass
class LLH:
    latitude: float
    longitude: float
    height: float

    def from_dms(degrees, minutes, seconds):
        return degrees + (minutes / 60) + (seconds / 3600)

    @classmethod
    def from_tuples(cls, latitude: (float, float, float), longitude: (float, float, float), height: float):
        return LLH(latitude=cls.from_dms(*latitude), longitude=cls.from_dms(*longitude), height=height)


@dataclass
class OPUSReport:
    time: datetime
    observation_start: datetime
    observation_end: datetime
    email: str
    obs: (int, int, int)
    amb: (int, int, int)
    rms: float
    antenna: str
    antenna_height: float
    accuracy_lat: float
    accuracy_lon: float
    accuracy_el_height: float
    ITRF2014: TconPos
    NAD83: TconPos
    ortho_height: float

    def _parse_time(tm):
        return datetime.fromisoformat(tm.replace("Z", "+00:00"))

    @classmethod
    def from_xml(cls, xml):
        soup = bs(xml, "lxml")

        solution = soup.find("opus_solution")

        positions = {}
        for position in solution.findAll("position"):
            frame = position.find("ref_frame")

            positions[frame.text.replace("(", " ").split()[0]] = TconPos(
                x=float(position.find("coordinate", axis="X").text),
                y=float(position.find("coordinate", axis="Y").text),
                z=float(position.find("coordinate", axis="X").text),
                xu=float(position.find("coordinate", axis="X")["uncertainty"]),
                yu=float(position.find("coordinate", axis="Y")["uncertainty"]),
                zu=float(position.find("coordinate", axis="Z")["uncertainty"]),
                lat=(
                    float(position.find("lat").find("degrees").text),
                    float(position.find("lat").find("minutes").text),
                    float(position.find("lat").find("seconds").text),
                ),
                e_lon=(
                    float(position.find("east_long").find("degrees").text),
                    float(position.find("east_long").find("minutes").text),
                    float(position.find("east_long").find("seconds").text),
                ),
                ellipsoid_height=float(position.find("el_height").text),
            )
        return OPUSReport(
            time=cls._parse_time(solution.find("solution_time").text),
            obs=(
                int(solution.find("percent_obs_used")["total"]),
                int(solution.find("percent_obs_used")["used"]),
                int(solution.find("percent_obs_used").text),
            ),
            amb=(
                int(solution.find("percent_amb_fixed")["total"]),
                int(solution.find("percent_amb_fixed")["fixed"]),
                int(solution.find("percent_amb_fixed").text),
            ),
            rms=float(solution.find("rms").text),
            observation_start=cls._parse_time(
                solution.find("observation_time")["start"]
            ),
            observation_end=cls._parse_time(solution.find("observation_time")["end"]),
            email=solution.find("email").text,
            antenna=solution.find("name").text,
            antenna_height=float(solution.find("arp_height").text),
            accuracy_lat=float(solution.find("data_quality").find("lat").text),
            accuracy_lon=float(solution.find("data_quality").find("long").text),
            accuracy_el_height=float(
                solution.find("data_quality").find("el_height").text
            ),
            ITRF2014=positions["ITRF2014"],
            NAD83=positions["NAD_83"],
            ortho_height=float(solution.find("ortho_hgt").text),
        )

    def print_quality(self, file=sys.stderr):
        print("QUALITY REPORT", file=file)
        print("-" * 14, file=file)
        print(
            f"OBS USED [{'VALID' if self.obs[2] > 90 else 'BAD'}]: {self.obs[2]} ({self.obs[1]}/{self.obs[0]})",
            file=file,
        )
        print(
            f"FIXED AMB [{'VALID' if self.amb[2] > 50 else 'BAD'}]: {self.amb[2]} ({self.amb[1]}/{self.amb[0]})",
            file=file,
        )
        print(
            f"OVERALL RMS [{'VALID' if self.rms  <= 0.03 else 'BAD'}]: {self.rms} m",
            file=file,
        )
        # print(f"peak-to-peak NAD83 [{'VALID' if self.NAD83.accuracy_lat <= 0.04 and self.NAD83.accuracy_lon <= 0.4 and self.NAD83.accuracy_el_height <= 0.08 else 'BAD'}]: Lat {self.NAD83.accuracy_lat} Lon {self.NAD83.accuracy_lon} El Hgt {self.NAD83.accuracy_el_height}", file=file)
        # print(f"peak-to-peak ITRF2014 [{'VALID' if self.ITRF2014.accuracy_lat <= 0.04 and self.ITRF2014.accuracy_lon <= 0.4 and self.ITRF2014.accuracy_el_height <= 0.08 else 'BAD'}]: Lat {self.ITRF2014.accuracy_lat} Lon {self.ITRF2014.accuracy_lon} El Hgt {self.ITRF2014.accuracy_el_height}", file=file)
        print("-" * 14, file=file)


@dataclass
class MjfPoint:
    key: int
    name: str
    point_type: int
    fkey: int
    latitude: float
    longitude: float
    height: float
    fkey_dataset: int
    station_type: int
    extra_type_flags: int
    fkey_layer: int

    def from_mjf_file(mjf):
        db = sqlite3.connect(mjf)
        cur = db.cursor()

        points = cur.execute("SELECT * FROM tblSoPoints").fetchall()

        for point in points:
            i, name, typ, fkey, lat, lon, hgt, ds, st, et, fl = point

            yield MjfPoint(
                key=i,
                name=name,
                point_type=typ,
                fkey=fkey,
                latitude=lat,
                longitude=lon,
                height=hgt,
                fkey_dataset=ds,
                station_type=st,
                extra_type_flags=et,
                fkey_layer=fl,
            )

    @classmethod
    def find_base(cls, files):
        found = False
        for file in files:
            for point in cls.from_mjf_file(file):
                if "base" in point.name.lower():
                    found = True
                    yield point

        if not found:
            raise FileNotFoundError("Couldnt find a base point")


class TconMail:
    OPUS_EMAIL = "opus@ngs.noaa.gov"

    def __init__(self, email, password, server):
        self.email = email
        self.password = password
        self.server = server

        # Set up mail client
        self.mail_client = imaplib.IMAP4_SSL(server)
        self.mail_client.login(email, password)
        self.mail_client.select("inbox")

    def receive(self, ident: str):
        # Find all the emails we have that have ident in the subject line
        self.mail_client._simple_command("NOOP")  # Make sure we have up to date emails
        status, data = self.mail_client.search(
            None, f"FROM {self.OPUS_EMAIL} TEXT {ident}"
        )
        mail_ids = sorted([d for block in data for d in block.split()])

        if len(mail_ids) == 0:
            return

        status, tcon_email = self.mail_client.fetch(mail_ids[-1], "(RFC822)")

        for part in tcon_email:
            if isinstance(part, tuple):
                message = email.message_from_bytes(part[1])

                if message.is_multipart():
                    for part in message.get_payload():
                        if part.get_content_type() == "text/xml":
                            return part.get_payload()
                else:
                    if part.get_content_type() == "text/xml":
                        return part.get_payload()

        raise FileNotFoundError("Failed to find xml file in email")


class OPUS:
    URL = "https://www.ngs.noaa.gov/OPUS-cgi/OPUS/Upload/Opusup.prl"

    def __init__(self, email, extended=True, xml=True):
        self.email = email
        self.extended = extended
        self.xml = xml

    def _get_data(self, tps: str, antenna: str, antenna_height: float):
        ident = f"OP{int(time.time() * 1000)}"

        with open(tps, "rb") as r:
            data = {
                "selectList1": (None, None),
                "email_address": (None, self.email),
                "ant_type": (None, antenna),
                "height": (None, str(antenna_height)),
                "extend_code": (None, 1),
                "xml_code": (None, 1),
                "set_profile": (None, 0),
                "delete_profile": (None, 0),
                "share": (None, 2),
                "submit_database": (None, 2),
                "opusOption": (None, 1),
                "geoid_model": (None, 1),
                "seqnum": (None, ident),
                "theHost1": (None, "www.ngs.noaa.gov"),
                "uploadfile": r.read(),
            }

        return ident, data

    def request_report(self, tps: str, antenna: str, antenna_height: float):
        ident, data = self._get_data(tps, antenna, antenna_height)

        r = requests.post(self.URL, files=data)
        r.raise_for_status()

        return ident


def points_subcommand(args):
    for file in args.files:
        print(f"--- {file} ---", file=sys.stderr)
        for point in MjfPoint.from_mjf_file(file):
            if args.format == "pretty":
                print(f"{point.name}: {point.latitude} {point.longitude} {point.height}m")

            if args.format == "csv":
                print(point.name, point.latitude, point.longitude, point.height, sep=",")


def process_subcommand(args):
    email = TconMail(EMAIL, PASSWORD, SERVER)
    opus = OPUS(EMAIL)
    if args.tps:
        opus_request = opus.request_report(args.tps, ANTENNAS[args.ant], args.hgt)
        print("Request posted...", file=sys.stderr)
    elif args.seq:
        opus_request = args.seq

    print("Waiting for email...", file=sys.stderr)
    mail = email.receive(opus_request)
    while mail is None:
        mail = email.receive(opus_request)
        if mail is None:
            time.sleep(15)

    print("Found email...")

    report = OPUSReport.from_xml(mail)
    report.print_quality()

    bases = list(MjfPoint.find_base(args.mjf))
    if len(bases) > 1:
        print("Found too many bases, select one", file=sys.stderr)
        for index, base in enumerate(bases):
            print(f"{index}: {base.name}")
        base = bases[int(input("> "))]
    else:
        base = bases[0]

    print(f"Using base {base.name} with {args.model} model", file=sys.stderr)

    if args.model == "NAD83":
        corrected_position = report.NAD83
    elif args.model == "ITRF2014":
        corrected_position = report.ITRF2014

    corrected_position = LLH.from_tuples(corrected_position.lat, corrected_position.e_lon, corrected_position.ellipsoid_height)
    corrected_position.longitude -= 360

    latitude_offset = base.latitude - corrected_position.latitude
    longitude_offset = base.longitude - corrected_position.longitude
    height_offset = base.height - corrected_position.height

    print(f"Base Station ({base.name}): {base.latitude} {base.longitude} {base.height}", file=sys.stderr)
    print(f"Corrected Base Station ({base.name}): {corrected_position.latitude} {corrected_position.longitude} {corrected_position.height}", file=sys.stderr)
    print(f"Correction Offsets: {latitude_offset} {longitude_offset} {height_offset}", file=sys.stderr)

    for mjf_file in args.mjf:
        points = list(MjfPoint.from_mjf_file(mjf_file))
        output_name = f"{mjf_file.split('/')[-1].strip('.mjf')}_output.csv"

        with open(output_name, "w") as fp:
            for point in points:
                if point == base:
                    continue
                assert (base.latitude > corrected_position.latitude) == (point.latitude > point.latitude - latitude_offset)
                assert (base.longitude > corrected_position.longitude) == (point.longitude > point.longitude - longitude_offset)
                assert (base.height > corrected_position.height) == (point.height > point.height - height_offset)

                print(f"{point.name},{point.latitude-latitude_offset},{point.longitude-longitude_offset},{point.height-height_offset}", file=fp)

        print(f"Wrote corrected values for {mjf_file} to {output_name}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    points_parser = subparsers.add_parser("points", help="Get points from a .mfj file")
    points_parser.add_argument("files", metavar="FILES", nargs="+", help="Mjf files to read and output points")
    points_parser.add_argument("--format", type=str, default="pretty", choices=["csv", "pretty"])
    points_parser.set_defaults(func=points_subcommand)

    process_parser = subparsers.add_parser("process", help="Fully process topcon data using Opus")
    tps_group = process_parser.add_mutually_exclusive_group(required=True)
    tps_group.add_argument("--tps", type=str, help="TPS file from base station")
    tps_group.add_argument("--seq", type=str, help="An OP[x] number for an email that already exists")
    process_parser.add_argument("--mjf", type=str, required=True, nargs="+", help="Mjf file from Tesla")
    process_parser.add_argument("--ant", type=str, required=True, help="Antenna", choices=ANTENNAS.keys())
    process_parser.add_argument("--hgt", type=float, required=True, help="Slant Height")
    process_parser.add_argument("--model", type=str, choices=["NAD83", "ITRF2014"], required=True, default="NAD83")
    process_parser.add_argument("--out", type=str, default="")
    process_parser.set_defaults(func=process_subcommand)

    args = parser.parse_args()
    args.func(args)
