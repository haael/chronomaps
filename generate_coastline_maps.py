#!/usr/bin/python3


"""
Generate coastline maps for different sea levels.

Attributed to: M. Zickel, D. Becker, J. Verheul, Y. Yener, C. Willmes (2016): Paleocoastlines GIS dataset.
CRC806-Database, doi: 10.5880/SFB806.19.

Paper: https://crc806db.uni-koeln.de/data/Z/Z2/Paleocoastlines_GIS_dataset.pdf
Data: https://crc806db.uni-koeln.de/dataset/show/paleocoastlines-gis-dataset1462293239/

"""

import shapefile
import cairo

sf = shapefile.Reader('data/Paleocoastlines.zip')

surfaces = []
ctxx = {}

for sr in sf.shapeRecords():
	l = sr.record.as_dict()['Sea level']
	try:
		ctx = ctxx[l]
	except KeyError:
		surface = cairo.SVGSurface(f'coast/{l}.svg', 360 * 2, 180 * 2)
		surfaces.append(surface)
		ctx = cairo.Context(surface)
		ctxx[l] = ctx
	
	ctx.set_source_rgb(0, 0, 1)
	ctx.move_to(*sr.shape.points[0])
	for x, y in sr.shape.points[1:]:
		ctx.line_to(x, y)
	ctx.close_path()
	ctx.fill()
	#print(sr.shape)

for surface in surfaces:
	surface.flush()


