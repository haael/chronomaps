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
from math import ceil, isnan, pi
from itertools import product
import cairo
from os import mkdir
from random import choice
from multiprocessing import Pool


colors = [
	(0.4, 0.4, 0.0), # shore

	(0.1, 0.9, 0.1), # tropical forest
	(0.3, 0.9, 0.3), # tropical forest
	(0.5, 0.9, 0.5), # tropical forest

	(0.6, 0.8, 0.5), # ??? (mid)
	(0.5, 0.8, 0.4), # ??? (incl north)
	(0.4, 0.8, 0.3), # europe, china (sth)
	(0.3, 0.8, 0.2), # europe, china (nth)
	(0.2, 0.8, 0.1), # america, europe (nth)
	(0.1, 0.8, 0.0), # america, asia

	(0.8, 0.5, 0.1), # tundra
	(0.8, 0.5, 0.2), # tundra, north asia

	(0.7, 0.9, 0.7), # tropical forest

	(0.9, 0.5, 0.1), # equator, steppe

	(0.6, 0, 0.9), # mountains

	(0.9, 0.5, 0.2), # sth europe, sth africa, sth australia, west americs
	(0.9, 0.5, 0.3), # america, asia (minor)
	(0.9, 0.5, 0.4), # shore, minor

	(0.6, 0.4, 0.6), # -
	(0.8, 0.4, 0.1), # cancer, minor
	(0.8, 0.4, 0.2), # america, asia
	(0.9, 0.9, 0), # dessert

	(0.5, 0, 0.8), # glacier, high mountains
	(0.4, 0, 0.7), # high mountains, far north
	(0.3, 0, 0.6), # far north
	(0.2, 0, 0.5), # arctic
	(0.1, 0, 0.4), # arctic

	(0.5, 0.4, 0.0), # dessert, minor
	(1, 1, 1) # glacier
]


data_file = 'data/LateQuaternary_Environment.nc'
output_dir = 'biome'

def neighbors_of(x, y):
	for dx, dy in product([-1, 0, 1], [-1, 0, 1]):
		if dx == dy == 0: continue
		yield x + dx, y + dy


def solve_maze(sx, sy, points, stick, o=None):
	if o is None:
		o = sx, sy
	assert (sx, sy) in points
	
	x, y = sx, sy
	solution = []
	while True:
		solution.append((x, y))
		points.remove((x, y))
		stick_to = frozenset(neighbors_of(x, y)) & stick
		
		neighbors = set()
		for nx, ny in neighbors_of(x, y):
			if (nx, ny) not in points: continue
			dx = nx - x
			dy = ny - y
			for px, py in neighbors_of(x, y):
				if (px, py) not in stick: continue
				qx = px - x
				qy = py - y
				if dx * qy - dy * qx > 0:
					neighbors.add((nx, ny))
					break
		
		if len(neighbors) == 0:
			return solution
		elif len(neighbors) == 1:
			x, y = list(neighbors)[0]
			continue
		else:
			break
	
	leaways = []
	for nx, ny in neighbors:
		points -= neighbors
		points.add((nx, ny))
		leaway = solve_maze(nx, ny, points, stick, o)
		leaways.append(leaway)
	leaways.sort(key=lambda _k: len(_k) + (10000 if (len(_k) > 3 and any(_no in _k for _no in neighbors_of(*o))) else 0))
	solution.extend(leaways[-1])
	return solution


def create_map(year, biome_points, lon, lat):
	print(year)
	
	surface = cairo.SVGSurface(f'biome/{year}.svg', 720, 360)
	ctx = cairo.Context(surface)
	
	ctx.set_line_width(1)
	ctx.set_line_join(cairo.LineJoin.ROUND)
	ctx.set_line_cap(cairo.LineCap.ROUND)
	
	points_to_draw = {}
	
	for w, color in enumerate(colors):
		interior_points = set()
		edge_points = set()		
		for x, y in product(range(lon), range(lat)):
			v = biome_points[lat - y - 1, x]
			if isnan(v) or w != int(v):
				continue
			
			neighbor_cnt = 0
			for nx, ny in neighbors_of(x, y):
				try:
					v_prim = biome_points[lat - ny - 1, nx]
				except IndexError:
					continue
				
				if not isnan(v_prim) and w == int(v_prim):
					neighbor_cnt += 1
			
			if neighbor_cnt < 8:
				edge_points.add((x, y))
			else:
				interior_points.add((x, y))
		
		if not edge_points:
			continue
		
		outer_border_points = set()
		inner_border_points = set()
		other_points = set()
		for x, y in edge_points:
			if any(_np in interior_points for _np in neighbors_of(x, y)):
				outer_border_points.add((x, y))
				inner_border_points.update(_np for _np in neighbors_of(x, y) if _np in interior_points)
			else:
				other_points.add((x, y))
		
		del edge_points, interior_points

		points_to_draw[w] = inner_border_points, outer_border_points, other_points
	
	for w, color in reversed(list(enumerate(colors))):
		try:
			inner_border_points, outer_border_points, other_points = points_to_draw[w]
		except KeyError:
			continue
		
		ctx.set_source_rgb(*color)
		points = set(outer_border_points)
		paths = []
		while points:
			sx, sy = next(iter(points))
			solution = solve_maze(sx, sy, set(points), inner_border_points)
			assert solution[0] == (sx, sy)
			if len(solution) > 1:
				paths.append(solution)
			else:
				other_points.add(solution[0])
			points -= frozenset(solution)
		
		while paths:
			path = paths.pop()
			sx, sy = path[0]
			ctx.move_to(sx + 0.5, sy + 0.5)
			
			while True:
				for x, y in path[1:]:
					ctx.line_to(x + 0.5, y + 0.5)
				ex, ey = path[-1]
				
				ns = max(abs(sx - ex), abs(sy - ey))
				np = 0
				for p in paths:
					np = max(np, abs(p[0][0] - ex), abs(p[0][1] - ey))
				
				if ns < np:
					ctx.close_path()
					break
				else:
					for p in paths:
						if max(abs(p[0][0] - ex), abs(p[0][1] - ey)) <= np:
							paths.remove(p)
							path = p
							sx, sy = path[0]
							ctx.line_to(sx + 0.5, sy + 0.5)
							break
					else:
						break
			
			ctx.close_path()
		ctx.fill_preserve()
		ctx.stroke()
	
	for w, color in reversed(list(enumerate(colors))):
		try:
			inner_border_points, outer_border_points, other_points = points_to_draw[w]
		except KeyError:
			continue
		
		gradient = cairo.RadialGradient(0, 0, 0, 0, 0, 1)
		gradient.add_color_stop_rgba(0, *color, 1)
		gradient.add_color_stop_rgba(1, *color, 0)
		#ctx.set_source_rgb(*color)
		
		for x, y in other_points:
			matrix = cairo.Matrix()
			matrix.translate(-x - 0.5, -y - 0.5)
			gradient.set_matrix(matrix)
			ctx.set_source(gradient)
			ctx.arc(x + 0.5, y + 0.5, 1, 0, 2 * pi)
			ctx.fill()
	
	surface.flush()



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
	
	lon = longitude.shape[0]
	lat = latitude.shape[0]
	
	with Pool(8) as pool:
		pool.starmap(create_map, ((year, biome[year_idx], lon, lat) for (year_idx, year) in enumerate(years)))

