#!/usr/bin/env python3

import argparse
import pandas as pd
import numpy as np
import exiftool
from pathlib import Path
from datetime import datetime
import plotly.express as px

np.set_printoptions(formatter={"float": "{}".format})


def get_unique_field(df, selector):
    series = df[selector]
    v = series.unique()[0]

    if series.eq(v).all():
        return v

    raise ValueError(f"{selector} should only return one unique value over all images")


def get_utc_time(meta):
    str_time = meta["EXIF:DateTimeOriginal"]
    if str_time is not None:
        utc_time = datetime.strptime(str_time, "%Y:%m:%d %H:%M:%S")
    else:
        utc_time = None
    return utc_time


def get_position(meta):
    lat = meta["EXIF:GPSLatitude"]
    latref = meta["EXIF:GPSLatitudeRef"]
    if latref == "S":
        lat *= -1.0
    lon = meta["EXIF:GPSLongitude"]
    lonref = meta["EXIF:GPSLongitudeRef"]
    if lonref == "W":
        lon *= -1.0
    alt = meta["EXIF:GPSAltitude"]
    return lat, lon, alt


def dir_path(string):
    path = Path(string)
    if path.exists() and path.is_dir():
        return path
    else:
        raise NotADirectoryError(string)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=dir_path)
    parser.add_argument("--ext", default="tif")
    parser.add_argument("--param")

    args = parser.parse_args()

    datas = []
    with exiftool.ExifTool() as exif:
        for file in args.directory.glob(f"**/*.{args.ext}"):
            data = exif.get_metadata(str(file))
            datas.append(data)

    df = pd.DataFrame(datas)
    df[["latitude", "longitude", "altitude"]] = df.apply(get_position, axis=1).apply(
        pd.Series
    )
    df["date"] = df.apply(get_utc_time, axis=1)
    df.set_index("date", inplace=True)

    print("--- Image Metadata ---")
    print(f"Camera Make: {get_unique_field(df, 'EXIF:Make')}")
    print(f"Camera Model: {get_unique_field(df, 'EXIF:Model')}")
    print(f"Start Time: {df.index.min()}")
    print(f"End Time: {df.index.max()}")
    print(f"Total Time: {df.index.max() - df.index.min()}")
    print(f"Aperture Sizes: {df['Composite:Aperture'].unique()}")
    print(f"Shutter Speeds: {df['Composite:ShutterSpeed'].unique()}")
    print(f"Exposure Time: {df['EXIF:ExposureTime'].unique()}")
    print(f"Exposure Mode: {df['EXIF:ExposureMode'].unique()}")
    print(f"ISO: {df['EXIF:ISO'].unique()}")
    print(f"F-Number: {df['EXIF:FNumber'].unique()}")
    print(f"Mean Camera Pitch: {df['MakerNotes:CameraPitch'].mean()}")
    print(f"Light Value Mean: {df['Composite:LightValue'].mean()}")
    print(f"Light Value Standard Deviation: {df['Composite:LightValue'].std()}")

    if args.param:
        fig = px.scatter_mapbox(
            df,
            lat=df.latitude,
            lon=df.longitude,
            color=df.query(args.param),
            zoom=14,
            labels=dict(
                latitude="Latitude",
                longitude="Longitude",
                altitude="Altitude",
                param=args.param,
            ),
            hover_data=["altitude", "SourceFile"],
        )
        fig.update_layout(
            autosize=True,
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

    # Some Interesting Keys
    # Compsite:Aperture
    # Composite:ShutterSpeed
    # Composite:LightValue (calculated LV = 2 * log2(Aperture) - log2(ShutterSpeed) - log2(ISO/100); similar to exposure value but normalized to ISO 100)
    # EXIF:WhiteBalance
    # EXIF:ExposureTime
    # EXIF:ExposureMode
    #     AUTO_BRACKET = 2
    #     AUTO_EXPOSURE = 0
    #     MANUAL_EXPOSURE = 1
    # EXIF:ISO
    # EXIF:FNumber

    # Example Phantom 4 RTK Data
    # Composite:Aperture: 6.3
    # Composite:CircleOfConfusion: 0.0110169622305844
    # Composite:FOV: 73.7398575770811
    # Composite:FocalLength35efl: 24
    # Composite:GPSAltitude: 1573.236
    # Composite:GPSLatitude: 40.6531951111111
    # Composite:GPSLongitude: -104.993758611111
    # Composite:GPSPosition: 40.6531951111111 -104.993758611111
    # Composite:HyperfocalDistance: 1.11573982326446
    # Composite:ImageSize: 5472 3648
    # Composite:LightValue: 14.2764879418872
    # Composite:Megapixels: 19.961856
    # Composite:ScaleFactor35efl: 2.72727272727273
    # Composite:ShutterSpeed: 0.002
    # EXIF:ApertureValue: 6.29846381255363
    # EXIF:ColorSpace: 1
    # EXIF:ComponentsConfiguration: 0 3 2 1
    # EXIF:CompressedBitsPerPixel: 3.547934621
    # EXIF:Compression: 6
    # EXIF:Contrast: 0
    # EXIF:CreateDate: 2022:06:02 11:10:11
    # EXIF:CustomRendered: 0
    # EXIF:DateTimeOriginal: 2022:06:02 11:10:11
    # EXIF:DigitalZoomRatio: undef
    # EXIF:ExifImageHeight: 3648
    # EXIF:ExifImageWidth: 5472
    # EXIF:ExifVersion: 0230
    # EXIF:ExposureCompensation: 0
    # EXIF:ExposureIndex: undef
    # EXIF:ExposureMode: 0
    # EXIF:ExposureProgram: 2
    # EXIF:ExposureTime: 0.002
    # EXIF:FNumber: 6.3
    # EXIF:FileSource: 3
    # EXIF:Flash: 32
    # EXIF:FlashpixVersion: 0010
    # EXIF:FocalLength: 8.8
    # EXIF:FocalLengthIn35mmFormat: 24
    # EXIF:GPSAltitude: 1573.236
    # EXIF:GPSAltitudeRef: 0
    # EXIF:GPSLatitude: 40.6531951111111
    # EXIF:GPSLatitudeRef: N
    # EXIF:GPSLongitude: 104.993758611111
    # EXIF:GPSLongitudeRef: W
    # EXIF:GPSVersionID: 2 3 0 0
    # EXIF:GainControl: 0
    # EXIF:ISO: 100
    # EXIF:ImageDescription: DCIM\SURVEY\100_0001\100_0
    # EXIF:InteropIndex: R98
    # EXIF:InteropVersion: 0100
    # EXIF:LightSource: 0
    # EXIF:Make: DJI
    # EXIF:MaxApertureValue: 2.79917173119039
    # EXIF:MeteringMode: 1
    # EXIF:Model: FC6310R
    # EXIF:ModifyDate: 2022:06:02 11:10:11
    # EXIF:Orientation: 1
    # EXIF:ResolutionUnit: 2
    # EXIF:Saturation: 0
    # EXIF:SceneCaptureType: 0
    # EXIF:SceneType: 1
    # EXIF:SerialNumber: 75a926e08caf41674cb2a21102d7d30a
    # EXIF:Sharpness: 0
    # EXIF:ShutterSpeedValue: 0.00200108754498594
    # EXIF:Software: v01.09.1755
    # EXIF:SubjectDistance: 0
    # EXIF:SubjectDistanceRange: 0
    # EXIF:ThumbnailImage: (Binary data 10956 bytes, use -b option to extract)
    # EXIF:ThumbnailLength: 10956
    # EXIF:ThumbnailOffset: 10240
    # EXIF:WhiteBalance: 1
    # EXIF:XPComment: Type=N, Mode=P, DE=None
    # EXIF:XPKeywords: v01.09.1755;1.3.0;v1.0.0
    # EXIF:XResolution: 72
    # EXIF:YCbCrPositioning: 1
    # EXIF:YResolution: 72
    # ExifTool:ExifToolVersion: 11.88
    # ExifTool:Warning: [minor] Possibly incorrect maker notes offsets (fix by 1783?)
    # File:BitsPerSample: 8
    # File:ColorComponents: 3
    # File:Directory: /media/davis/UBUNTU 20_0/060222 NEEDS TO BE SORTED/USB Drive/DCIM/SURVEY/100_0001
    # File:EncodingProcess: 0
    # File:ExifByteOrder: II
    # File:FileAccessDate: 2022:06:23 19:48:06-06:00
    # File:FileInodeChangeDate: 2022:06:02 11:10:14-06:00
    # File:FileModifyDate: 2022:06:02 11:10:14-06:00
    # File:FileName: 100_0001_0001.JPG
    # File:FilePermissions: 755
    # File:FileSize: 9140374
    # File:FileType: JPEG
    # File:FileTypeExtension: JPG
    # File:ImageHeight: 3648
    # File:ImageWidth: 5472
    # File:MIMEType: image/jpeg
    # File:YCbCrSubSampling: 2 1
    # MPF:DependentImage1EntryNumber: 0
    # MPF:DependentImage2EntryNumber: 0
    # MPF:ImageUIDList: (Binary data 66 bytes, use -b option to extract)
    # MPF:MPFVersion: 0010
    # MPF:MPImageFlags: 8
    # MPF:MPImageFormat: 0
    # MPF:MPImageLength: 257922
    # MPF:MPImageStart: 8882452
    # MPF:MPImageType: 65537
    # MPF:NumberOfImages: 2
    # MPF:PreviewImage: (Binary data 257922 bytes, use -b option to extract)
    # MPF:TotalFrames: 1
    # MakerNotes:CameraPitch: -90
    # MakerNotes:CameraRoll: 0
    # MakerNotes:CameraYaw: 84.5
    # MakerNotes:Make: DJI
    # MakerNotes:Pitch: -21.1000003814697
    # MakerNotes:Roll: -5.09999990463257
    # MakerNotes:SpeedX: 0.200000002980232
    # MakerNotes:SpeedY: 0.400000005960464
    # MakerNotes:SpeedZ: 0
    # MakerNotes:Yaw: 89.4000015258789
    # SourceFile: /media/davis/UBUNTU 20_0/060222 NEEDS TO BE SORTED/USB Drive/DCIM/SURVEY/100_0001/100_0001_0001.JPG
    # XMP:About: DJI Meta Data
    # XMP:AbsoluteAltitude: +1573.24
    # XMP:AlreadyApplied: False
    # XMP:CalibratedFocalLength: 3666.666504
    # XMP:CalibratedOpticalCenterX: 2736.0
    # XMP:CalibratedOpticalCenterY: 1824.0
    # XMP:CamReverse: 0
    # XMP:CreateDate: 2022:06:02
    # XMP:DewarpData:  2021-10-26;3722.160000000000,3746.360000000000,-86.690000000000,54.740000000000,-0.290029000000,0.109597000000,-0.005739070000,0.000156646000,-0.018043300000
    # XMP:DewarpFlag: 0
    # XMP:FlightPitchDegree: -21.1
    # XMP:FlightRollDegree: -5.1
    # XMP:FlightXSpeed: +0.20
    # XMP:FlightYSpeed: +0.40
    # XMP:FlightYawDegree: +89.40
    # XMP:FlightZSpeed: +0.00
    # XMP:Format: image/jpg
    # XMP:GPSLatitude: 40.65319514
    # XMP:GPSLongtitude: -104.99375862
    # XMP:GimbalPitchDegree: -90.0
    # XMP:GimbalReverse: 0
    # XMP:GimbalRollDegree: +0.00
    # XMP:GimbalYawDegree: +84.50
    # XMP:HasCrop: False
    # XMP:HasSettings: False
    # XMP:Make: DJI
    # XMP:Model: FC6310R
    # XMP:ModifyDate: 2022:06:02
    # XMP:PhotoDiff: 34YDH3B001PP2G20220602171038
    # XMP:RelativeAltitude: +40.11
    # XMP:RtkFlag: 50
    # XMP:RtkStdHgt: 0.02293
    # XMP:RtkStdLat: 0.01129
    # XMP:RtkStdLon: 0.01193
    # XMP:SelfData: Undefined
    # XMP:Version: 7.0

    # Red Edge Tags
    # Composite:Aperture
    # Composite:CircleOfConfusion
    # Composite:FOV
    # Composite:FocalLength35efl
    # Composite:GPSAltitude
    # Composite:GPSLatitude
    # Composite:GPSLongitude
    # Composite:GPSPosition
    # Composite:HyperfocalDistance
    # Composite:ImageSize
    # Composite:Megapixels
    # Composite:ScaleFactor35efl
    # Composite:ShutterSpeed
    # Composite:SubSecModifyDate
    # EXIF:BitsPerSample
    # EXIF:BlackLevel
    # EXIF:BlackLevelRepeatDim
    # EXIF:Compression
    # EXIF:CreateDate
    # EXIF:DateTimeOriginal
    # EXIF:ExifVersion
    # EXIF:ExposureProgram
    # EXIF:ExposureTime
    # EXIF:FNumber
    # EXIF:FocalLength
    # EXIF:FocalPlaneResolutionUnit
    # EXIF:FocalPlaneXResolution
    # EXIF:FocalPlaneYResolution
    # EXIF:GPSAltitude
    # EXIF:GPSAltitudeRef
    # EXIF:GPSDOP
    # EXIF:GPSLatitude
    # EXIF:GPSLatitudeRef
    # EXIF:GPSLongitude
    # EXIF:GPSLongitudeRef
    # EXIF:GPSVersionID
    # EXIF:ISOSpeed
    # EXIF:ImageHeight
    # EXIF:ImageWidth
    # EXIF:Make
    # EXIF:MeteringMode
    # EXIF:Model
    # EXIF:ModifyDate
    # EXIF:OpcodeList3
    # EXIF:Orientation
    # EXIF:PhotometricInterpretation
    # EXIF:PlanarConfiguration
    # EXIF:RowsPerStrip
    # EXIF:SamplesPerPixel
    # EXIF:SerialNumber
    # EXIF:Software
    # EXIF:StripByteCounts
    # EXIF:StripOffsets
    # EXIF:SubSecTime
    # EXIF:SubfileType
    # ExifTool:ExifToolVersion
    # File:Directory
    # File:ExifByteOrder
    # File:FileAccessDate
    # File:FileInodeChangeDate
    # File:FileModifyDate
    # File:FileName
    # File:FilePermissions
    # File:FileSize
    # File:FileType
    # File:FileTypeExtension
    # File:MIMEType
    # SourceFile
    # XMP:About
    # XMP:BandName
    # XMP:BandSensitivity
    # XMP:Bandwidth
    # XMP:BootTimestamp
    # XMP:CaptureId
    # XMP:CenterWavelength
    # XMP:CentralWavelength
    # XMP:DarkRowValue
    # XMP:Exposure
    # XMP:FlightId
    # XMP:GPSXYAccuracy
    # XMP:GPSZAccuracy
    # XMP:Gain
    # XMP:Irradiance
    # XMP:IrradianceExposureTime
    # XMP:IrradianceGain
    # XMP:IrradiancePitch
    # XMP:IrradianceRoll
    # XMP:IrradianceYaw
    # XMP:ModelType
    # XMP:OffMeasurement
    # XMP:PerspectiveDistortion
    # XMP:PerspectiveFocalLength
    # XMP:PerspectiveFocalLengthUnits
    # XMP:Pitch
    # XMP:PressureAlt
    # XMP:PrincipalPoint
    # XMP:RadiometricCalibration
    # XMP:RawMeasurement
    # XMP:RigCameraIndex
    # XMP:RigName
    # XMP:RigRelatives
    # XMP:RigRelativesReferenceRigCameraIndex
    # XMP:Roll
    # XMP:SensorId
    # XMP:Serial
    # XMP:SpectralIrradiance
    # XMP:SwVersion
    # XMP:TimeStamp
    # XMP:TriggerMethod
    # XMP:VignettingCenter
    # XMP:VignettingPolynomial
    # XMP:WavelengthFWHM
    # XMP:XMPToolkit
    # XMP:Yaw
