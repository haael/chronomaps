#!/usr/bin/python3


"""
Generate biome background maps from NetCDF file.

Attributed to: Robert Beyer
Paper: https://www.nature.com/articles/s41597-020-0552-1
Data: https://figshare.com/articles/dataset/LateQuaternary_Environment_nc/12293345/4
License: CC BY 4.0 https://creativecommons.org/licenses/by/4.0/
"""

#import numpy as np
import netCDF4 as nc4
from math import ceil, isnan
from itertools import product
import cairo
from os import mkdir


colors = [
	(0.4, 0.4, 0.4), # shore
	(0.1, 1, 0.1), # tropical forest
	(0.2, 1, 0.2), # tropical forest
	(0.3, 1, 0.3), # tropical forest
	(0.5, 0.8, 0.5), # ??? (mid)
	(0.4, 0.8, 0.4), # ??? (incl north)
	(0.3, 0.8, 0.3), # europe, china (sth)
	(0.2, 0.8, 0.2), # europe, china (nth)
	(0.1, 0.8, 0.1), # america, europe (nth)
	(0.0, 0.8, 0.0), # america, asia
	(0.8, 0.5, 0.1), # tundra
	(0.8, 0.5, 0.2), # tundra, north asia
	(0.1, 0.9, 0.1), # tropical forest
	(0.9, 0.5, 0.1), # equator, steppe
	(0.8, 0.8, 0.9), # mountains
	(0.9, 0.5, 0.2), # sth europe, sth africa, sth australia, west americs
	(0.9, 0.5, 0.3), # america, asia (minor)
	(0.9, 0.5, 0.4), # shore, minor
	(0.6, 0.4, 0.6), # -
	(0.8, 0.4, 0.1), # cancer, minor
	(0.8, 0.4, 0.2), # america, asia
	(0.9, 0.9, 0), # dessert
	(0.4, 0.4, 0.5), # glacier, high mountains
	(0.5, 0.5, 0.6), # high mountains, far north
	(0.6, 0.6, 0.7), # far north
	(0.7, 0.7, 0.8), # arctic
	(0.8, 0.8, 0.8), # arctic
	(0.9, 0.9, 0.2), # dessert, minor
	(1, 1, 1) # glacier
]


data_file = 'data/LateQuaternary_Environment.nc'
output_dir = 'biome'


if __name__ == '__main__':	
	nc = nc4.Dataset(data_file, 'r')
	longitude   = nc.variables['longitude'][...]
	latitude    = nc.variables['latitude'][...]
	years       = nc.variables['time'][...]
	#months      = nc.variables['month']
	#temperature = nc.variables['temperature']
	biome       = nc.variables['biome']
	
	try:
		mkdir(output_dir)
	except FileExistsError:
		pass
	
	for year_idx, year in enumerate(years):
		surface = cairo.ImageSurface(cairo.Format.ARGB32, 720, 360)
		ctx = cairo.Context(surface)
		
		#cts.set_operator(cairo.Operator.CLEAR)
		#ctx.set_source_rgba(0, 0, 0, 0)
		#ctx.paint()
		#cts.set_operator(cairo.Operator.OVER)
		
		b = biome[year_idx]
		
		vs = set()
		lm = latitude.shape[0]
		for x, y in product(range(longitude.shape[0]), range(latitude.shape[0])):
			v = b[y, x]
			
			if not isnan(v):
				vs.add(v)
			
			if isnan(v):
				rgba = None
			elif v == 28:
				rgba = 1, 1, 1, 1
			else:
				rgba = colors[int(v)] + (0.33,)
			
			if rgba:
				ctx.set_source_rgba(*rgba)
				ctx.rectangle(x, lm - y, 1, 1)
				ctx.fill()
		
		surface.flush()
		surface.write_to_png(f'{output_dir}/{abs(year)}.png')

