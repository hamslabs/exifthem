#! /usr/bin/env python
import sys
import os
import glob
import argparse
from datetime import datetime
import math
import piexif
from PIL import Image
from PIL.ExifTags import TAGS

from ctypes import *
from ctypes.util import find_library
if os.name == 'nt':
	libc = cdll.msvcrt
else:
	libc = cdll.LoadLibrary(find_library('c'))


metaFilename = 'Metadata Source File.txt'


def main(args) -> None:


	try:
		with open(args.filename) as f:
			while line := f.readline():
				if line.startswith(' [FILM'):
					while line := f.readline().strip():
						if line.startswith('Speed:'):		# 0x8827
							ISOSpeed = c_int()
							libc.sscanf(line.encode('utf-8'), b'Speed: %d', byref(ISOSpeed))
	
				if line.startswith(' [Frame'):
					frameNum = c_int()
					libc.sscanf(line.encode('utf-8'), b' [Frame %d', byref(frameNum))
					fileNames = glob.glob('*{:04d}.*'.format(frameNum.value))
					fileName = fileNames[0]
					
					try:
						with Image.open(fileName) as img:
							exifDict = piexif.load(img.info['exif'])


							eifDict['Exif'][piexif.ExifIFD.ISOSpeed] =  ISOSpeed.value
	
							while line := f.readline().strip():		# 0x829a
								if line.startswith('Shutter:'):
									numerator = c_int()
									denominator = c_int()
									libc.sscanf(line.encode('utf-8'), b'Shutter: %d/%d', byref(numerator), byref(denominator))
									exifDict['Exif'][piexif.ImageIFD.ExposureTime] =  (numerator.value, denominator.value)
			
								if line.startswith('Aperture:'):	# 0x829d
									aperture = c_float()
									libc.sscanf(line.encode('utf-8'), b'Aperture: f/%f', byref(aperture))
									fstop = round(aperture.value, 1)
									exifDict['Exif'][piexif.ExifIFD.FNumber] =  (int(fstop*10), 10)
			
								# 2021:02:04 16:42:32

								if line.startswith('When taken:'):	# 0x0132 0x9003 0x9004
									dateBuffer = create_string_buffer(b'\000' * 32)
									libc.sscanf(line.encode('utf-8'), b'When taken: %[^\n]', dateBuffer)
									dateString = dateBuffer.value.decode('utf-8')
									ISODateTime = datetime.strptime(dateString, '%B %d, %Y')
									EXIFDateTime = ISODateTime.strftime('%Y:%m:%d %H:%M:%S')

									exifDict['0th'][piexif.ImageIFD.DateTime] =  EXIFDateTime 
									exifDict['Exif'][piexif.ExifIFD.DateTimeOriginal] =  EXIFDateTime
									exifDict['Exif'][piexif.ExifIFD.DateTimeDigitized] =  EXIFDateTime

			
								if line.startswith('Notes:'):
									notesBuffer = create_string_buffer(b'\000' * 128)
									libc.sscanf(line.encode('utf-8'), b'Notes: %[^\n]', notesBuffer)
									notesString = notesBuffer.value.decode('utf-8')
									exifDict['Exif'][piexif.ExifIFD.UserComment] =  notesString.encode('utf-8')
			
								if line.startswith('Location:'):	# 0x8825
									latitude = c_float()
									longitude = c_float()
									radius = c_int()
									libc.sscanf(line.encode('utf-8'), b'Location: [Latitude: %f Longitude: %f Radius: %d',
											byref(latitude), byref(longitude), byref(radius))

									latMinutes, latDegrees = math.modf(latitude.value)
									exifDict['GPS'][piexif.GPSIFD.GPSLatitudeRef] =  'N'
									exifDict['GPS'][piexif.GPSIFD.GPSLatitude] = ((int(latDegrees),1), (int(latMinutes * 60 * 1000000),1000000), (0,1))
									
									longMinutes, longDegrees = math.modf(math.fabs(longitude.value))
									exifDict['GPS'][piexif.GPSIFD.GPSLongitudeRef] =  'W'
									exifDict['GPS'][piexif.GPSIFD.GPSLongitude] = ((int(longDegrees),1), (int(longMinutes * 60 * 1000000),1000000), (0,1))

							exifBytes = piexif.dump(exifDict)
							img.save('_' + fileName, 'jpeg', exif=exifBytes)

					except Exception as error:
						print(error)

	except Exception as error:
		print(error)


'''		
	for filename in args.filenames:
		image = Image.open(filename)
		exifdata = image.getexif()
		print (exifdata)
		for tag_id in exifdata:
			# get the tag name, instead of human unreadable tag id
			tag = TAGS.get(tag_id, tag_id)
			data = exifdata.get(tag_id)
			# decode bytes
			if isinstance(data, bytes):
				data = data.decode()
			print(f"{tag:25}: {data}")
'''


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Process some integers.')
	parser.add_argument('filename', metavar='filenames', type=str, help='some files to process')

	args = parser.parse_args()

#	print(glob.glob("*0001.*"))
	

	main(args)
