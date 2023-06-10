#!/usr/bin/python3


"""
Data: https://www.ncei.noaa.gov/products/etopo-global-relief-model
"""


from geotiff import GeoTiff
from itertools import product
import cairo
from os import mkdir
from math import atan, ceil, pi
from multiprocessing import Pool


data_file = 'data/ETOPO_2022_v1_60s_N90W180_bed.tif'
output_dir = 'topo'


etopo = GeoTiff(data_file)

try:
	mkdir(output_dir)
except FileExistsError:
	pass


step = 15

def generate_map(xa, ya):
	print("generate_map", xa, ya)
	box = etopo.read_box(((xa, ya), (xa + step, ya + step)))
	xr, yr = box.shape
	
	for downscale in [1, 2, 4, 8]:
		surface = cairo.ImageSurface(cairo.Format.RGB24, ceil(xr / downscale), ceil(yr / downscale))
		ctx = cairo.Context(surface)
		
		for xb, row in enumerate(box):
			for yb, value in enumerate(row):
				if not (xb % downscale == 0 and yb % downscale == 0):
					continue
				
				k = (atan(value / 1000) / (pi / 2)) / 2 + 1/2
				if value >= 0:
					rgb = 0.5, k, 0
				else:
					rgb = 0, k, 0.5
				
				ctx.set_source_rgb(*rgb)
				ctx.rectangle(yb / downscale + 0.5, xb / downscale + 0.5, 1, 1)
				ctx.fill()
		
		surface.flush()
		surface.write_to_png(f'{output_dir}/{xa:+}{ya:+}s{downscale}.png')


if __name__ == '__main__':
	with Pool(8) as p:
		p.starmap(generate_map, ((xa, ya) for (xa, ya) in product(range(-180, 180, step), range(-90, 90, step))))

#if __name__ == '__main__':
#	with Pool(8) as p:
#		p.starmap(generate_map, ((xa, ya) for (xa, ya) in product(range(0, 15, step), range(45, 60, step))))
