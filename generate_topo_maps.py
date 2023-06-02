#!/usr/bin/python3


"""
Data: https://www.ncei.noaa.gov/products/etopo-global-relief-model
"""


from geotiff import GeoTiff
from itertools import product
import cairo
from os import mkdir
from math import atan, ceil


data_file = 'data/ETOPO_2022_v1_60s_N90W180_bed.tif'
output_dir = 'topo'


etopo = GeoTiff(data_file)

try:
	mkdir(output_dir)
except FileExistsError:
	pass


step = 15
for xa, ya in product(range(-180, 180, step), range(-90, 90, step)):
	box = etopo.read_box(((xa, ya), (xa + step, ya + step)))
	xr, yr = box.shape
	
	for downscale in [1, 2, 4, 8]:
		surface = cairo.ImageSurface(cairo.Format.RGB24, ceil(xr / downscale), ceil(yr / downscale))
		ctx = cairo.Context(surface)
		ctx.scale(1 / downscale, 1 / downscale)
		
		for xb, row in enumerate(box):
			for yb, value in enumerate(row):
				if value > 0:
					k = atan(value / 1000)
					rgb = k / 2, 1 - k / 2, 0
				else:
					k = 1 + atan(value / 10000)
					rgb = k, k, 1
				ctx.set_source_rgb(*rgb)
				ctx.rectangle(yb, xb, 1, 1)
				ctx.fill()
		
		surface.flush()
		surface.write_to_png(f'{output_dir}/{xa:+}{ya:+}s{downscale}.png')


