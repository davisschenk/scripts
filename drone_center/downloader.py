from micasense.imageset import ImageSet
import plotly.express as px
import pandas as pd
import numpy as np
import glob
import os
import shutil

def check_calibrated(capture):
    if capture.panels_in_all_expected_images():
        return True
    capture.clear_image_data()
    return False

class DataDownloader:
    def __init__(self):
        self.flights = {}
        self.data = {}

    def print_menu(self):
        print("-- Menu --")
        print("1. Create Flight")
        print("2. List Flights")
        print("3. Load Data")
        print("4. Add Data to Flight")
        print("5. Display Data")
        print("6. Display Flights")
        print("7. Process Flights")
        print("q. Exit")

    def create_flight(self):
        flight_name = input("Flight Name > ")

        if flight_name in self.flights:
            print("Flight already exists")
            return

        self.flights[flight_name] = []

    def list_flights(self):
        print("-- Flights --")
        for flight_name, data in self.flights.items():
            print(f"{flight_name}: {data}")

    def commands(self):
        return {
            "1": self.create_flight,
            "2": self.list_flights,
            "3": self.load_data,
            "4": self.add_data_to_flight,
            "5": self.display_all_data,
            "6": self.display_all_flights,
            "7": self.process_flights
        }

    def load_data(self):
        paths = input("Path > ")

        for path in glob.glob(paths):
            name = path.split("/")[-1]

            ims = ImageSet.from_directory(path, use_tqdm=True)
            if len(ims.captures):
                self.data[name] = ims
                print(f"Loaded {name} from {path}")

    def add_data_to_flight(self):
        print("-- Flights --")
        for idx, flight in enumerate(self.flights.keys()):
            print(f"\t{idx}. {flight}")

        flight = list(self.flights.keys())[int(input("Id > "))]

        print("-- Data --")
        for idx, data in enumerate(self.data.keys()):
            print(f"\t{idx}. {data}")

        data = list(self.data.keys())[int(input("Id > "))]

        if data not in self.flights[flight]:
            self.flights[flight].append(data)

    def data_as_df(self, img):
        data, columns = img.as_nested_lists()
        df = pd.DataFrame.from_records(data, columns=columns)

        for capture in img.captures:
            ci = capture.images[0].capture_id
            df.loc[df.capture_id == ci, "capture"] = capture

        cutoff_altitude = df.altitude.mean()-3.0*df.altitude.std()
        df["valid_altitude"] = df["altitude"] > cutoff_altitude

        return df

    def display_all_data(self):
        frames = []
        for name, data in self.data.items():
            data = self.data_as_df(data)
            data["set_id"] = name
            frames.append(data)

        df = pd.concat(frames)

        fig = px.line_mapbox(
            df, lat=df.latitude, lon=df.longitude, color=df.set_id, zoom=14
        )
        fig.update_layout(
            mapbox_style="white-bg",
            mapbox_layers=[
                {
                    "below": "traces",
                    "sourcetype": "raster",
                    "sourceattribution": "United States Geological Survey",
                    "source": [
                        "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"
                    ],
                }
            ],
        )

        fig.show()

    def display_all_flights(self):
        frames = []
        for flight_name, flight_data in self.flights.items():
            for data in flight_data:
                data = self.data_as_df(self.data[data])
                data["flight"] = flight_name
                frames.append(data)

        df = pd.concat(frames)

        fig = px.line_mapbox(
            df, lat=df.latitude, lon=df.longitude, color=df.flight, zoom=14
        )
        fig.update_layout(
            mapbox_style="white-bg",
            mapbox_layers=[
                {
                    "below": "traces",
                    "sourcetype": "raster",
                    "sourceattribution": "United States Geological Survey",
                    "source": [
                        "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"
                    ],
                }
            ],
        )

        fig.show()

    def process_flights(self):
        frames = []
        for flight_name, flight_data in self.flights.items():
            for data in flight_data:
                data = self.data_as_df(self.data[data])
                data["flight"] = flight_name
                frames.append(data)

        df = pd.concat(frames)

        for flight_name in df.flight.unique():
            os.mkdir(flight_name)
            os.mkdir(f"{flight_name}/Data")
            os.mkdir(f"{flight_name}/Reflectence")
            os.mkdir(f"{flight_name}/Reflectence/Start")
            os.mkdir(f"{flight_name}/Reflectence/End")

            flight = df[df["flight"] == flight_name]


            flight["calibrated"] = False
            flight.calibrated.iloc[:10] = flight.capture.iloc[:10].apply(check_calibrated)
            flight.calibrated.iloc[-10:] = flight.capture.iloc[-10:].apply(check_calibrated)

            assert any(flight.calibrated.iloc[-10:])
            assert any(flight.calibrated.iloc[:10])

            cutoff_altitude = df.altitude.mean()-3.0*df.altitude.std()
            flight["valid_altitude"] = flight["altitude"] > cutoff_altitude

            gr = flight.groupby((flight.calibrated != flight.calibrated.shift()).cumsum())
            cal_start = gr.get_group(min(gr.groups.keys()))
            cal_end = gr.get_group(max(gr.groups.keys()))

            for cs in cal_start.capture:
                for fn in cs.images:
                    print(f"Moving {fn.path} to Start")
                    shutil.copy2(fn.path, f"{flight_name}/Reflectence/Start/")

            print(f"Copied {len(cal_start)} captures to {flight_name}/Reflectence/Start/")

            for cs in cal_end.capture:
                for fn in cs.images:
                    print(f"Moving {fn.path} to End")
                    shutil.copy2(fn.path, f"{flight_name}/Reflectence/End/")

            print(f"Copied {len(cal_end)} captures to {flight_name}/Reflectence/End/")

            img_number = 0
            for cs in flight[flight["valid_altitude"]].capture:
                for fn in cs.images:

                    n = fn.path.split("/")[-1].split(".")[0].split("_")[-1]
                    filename = f"{flight_name}/Data/IMG_{img_number:04}_{n}.tif"
                    print(f"Moving {fn.path} to {filename}")
                    shutil.copy2(fn.path, filename)
                img_number += 1

            print(f"Copied {len(flight[flight['valid_altitude']])} captures to {flight_name}/Data")

    def main(self):
        self.print_menu()
        while (inp := input("> ")) != "q":
            cmds = self.commands()
            if inp in cmds:
                # try:
                cmds[inp]()
                # except Exception as e:
                #     print(f"Exception occured while processing command: {e}")
            else:
                print("Command not recognized")
            self.print_menu()

if __name__ == "__main__":
    dd = DataDownloader()
    # dd.flights = {"Flight 1": ["0000SET", "0001SET"]}
    # dd.data = {"0000SET": ImageSet.from_directory("/media/davis/UBUNTU 20_0/Easten 050122 M300/0000SET"), "0001SET": ImageSet.from_directory("/media/davis/UBUNTU 20_0/Easten 050122 M300/0001SET")}
    dd.main()
