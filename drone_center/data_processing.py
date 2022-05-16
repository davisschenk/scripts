import numpy as np
import pandas as pd
from micasense import imageset


if __name__ == "__main__":
    imgset = imageset.ImageSet.from_directory("/media/davis/UBUNTU 20_0/Easten 050122 M300/0000SET")

    data, columns = imgset.as_nested_lists()
    df = pd.DataFrame.from_records(data, index='timestamp', columns=columns)

    for capture in imgset.captures:
        ci = capture.images[0].capture_id
        df.loc[df.capture_id == ci, "capture"] = capture

    print(df.columns)

    middle_time = df.timestamp.mean()
    start = df[df.timestamp > middle_time].iloc[:10]
    end = df[df.timestamp < middle_time].iloc[:10]

    print(start)
    print(end)
