#! /usr/bin/env python
import sys
import os
import glob
import argparse
from datetime import datetime
import math
import json
import subprocess



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
					fileNames = glob.glob('*{:03d}.*'.format(frameNum.value))
					fileName = fileNames[0]
					
					(name, ext) = os.path.splitext(fileName)
					if 1:
						commandLineList = ['exiftool']
						commandLineList.append(('-isospeed=' + str(ISOSpeed.value)))
	
					while line := f.readline().strip():		# 0x829a
						if line.startswith('Shutter:'):
							numerator = c_int()
							denominator = c_int()
							libc.sscanf(line.encode('utf-8'), b'Shutter: %d/%d', byref(numerator), byref(denominator))
							if denominator.value == 0:
								 denominator.value = 1

							commandLineList.append(('-exposuretime=' + str(float(numerator.value) / float(denominator.value))))

	
						if line.startswith('Aperture:'):	# 0x829d
							aperture = c_float()
							libc.sscanf(line.encode('utf-8'), b'Aperture: f/%f', byref(aperture))
							fstop = round(aperture.value, 1)

							commandLineList.append(('-fnumber=' + str(int(fstop*10)) + '/10'))
	
						# 2021:02:04 16:42:32

						if line.startswith('When taken:'):	# 0x0132 0x9003 0x9004
							dateBuffer = create_string_buffer(b'\000' * 32)
							libc.sscanf(line.encode('utf-8'), b'When taken: %[^\n]', dateBuffer)
							dateString = dateBuffer.value.decode('utf-8')
							ISODateTime = datetime.strptime(dateString, '%B %d, %Y')
							EXIFDateTime = ISODateTime.strftime('"%Y:%m:%d %H:%M:%S"')

							commandLineList.append(('-datetime=' + EXIFDateTime))
							commandLineList.append(('-datetimeoriginal=' + EXIFDateTime))
							commandLineList.append(('-datetimedigitized=' + EXIFDateTime))

	
						if line.startswith('Notes:'):
							notesBuffer = create_string_buffer(b'\000' * 128)
							libc.sscanf(line.encode('utf-8'), b'Notes: %[^\n]', notesBuffer)
							notesString = notesBuffer.value.decode('utf-8')

							commandLineList.append(('-usercomment=' + '"' + notesString + '"'))
	
						if line.startswith('Location:'):	# 0x8825
							latitude = c_float()
							longitude = c_float()
							radius = c_int()
							libc.sscanf(line.encode('utf-8'), b'Location: [Latitude: %f Longitude: %f Radius: %d',
									byref(latitude), byref(longitude), byref(radius))

							commandLineList.append(('-latitude=' + str(latitude.value)))
							commandLineList.append(('-exif:gpslatitude=' + str(latitude.value)))
							commandLineList.append(('-exif:gpslatituderef=' + ((latitude.value > 0) and "N" or "S")))
							commandLineList.append(('-longitude=' + str(longitude.value)))
							commandLineList.append(('-exif:gpslongitude=' + str(longitude.value)))
							commandLineList.append(('-exif:gpslongituderef=' + ((longitude.value > 0) and "E" or "W")))

					tmpName = '_tmp_' + fileName
					commandLineList.extend(['-q', '-o', tmpName , fileName ])
					#print(commandLineList)

					subprocess.run(commandLineList)
					
					if not args.keep:
						os.replace(tmpName, fileName)

	except Exception as error:
		print(error)
		raise


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Add EXIF tags for images based on metadata file')
	parser.add_argument('filename', type=str, help='metadata file for images')
	parser.add_argument('--keep', action='store_true', help='keep original and create temp files')

	args = parser.parse_args()

	main(args)

