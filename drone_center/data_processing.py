class Project:
    pass


class Dataset:
    pass


class Location:
    pass


class Flight:
    def __init__(self, location, name, height, speed):
        self.location = location
        self.name = name
        self.height = height
        self.speed = speed
