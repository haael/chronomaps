#!/usr/bin/python3
#-*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Rsvg', '2.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GObject, GLib, Rsvg, GdkPixbuf

import cairo
import math
from itertools import product
from collections import namedtuple
from enum import Enum, auto
from random import uniform
from pathlib import Path

from game_widget import GameWidget, surface, quantize_down, quantize_up, float_range


class ChronoMaps(GameWidget):
	def __init__(self):
		super().__init__()
		self.earth_horizontal_size = 15000
		self.earth_vertical_size = 7500
		
		loader = GdkPixbuf.PixbufLoader.new_with_mime_type('image/jpeg')
		loader.write(Path('earth.jpg').read_bytes())
		loader.close()
		pixbuf = loader.get_pixbuf()
		self.earth_image = Gdk.cairo_surface_create_from_pixbuf(pixbuf, 0, None)
		self.earth_image_width = pixbuf.get_width()
		self.earth_image_height = pixbuf.get_height()
		
		loader = GdkPixbuf.PixbufLoader.new_with_mime_type('image/png')
		loader.write(Path('maps/0.png').read_bytes())
		loader.close()
		pixbuf = loader.get_pixbuf()
		self.biome_image = Gdk.cairo_surface_create_from_pixbuf(pixbuf, 0, None)
		self.biome_image_width = pixbuf.get_width()
		self.biome_image_height = pixbuf.get_height()
		self.biome_year = 0
	
	def set_year_bp(self, year_bp):
		years = [int(p.stem) for p in Path('maps').iterdir() if p.suffix == '.png']
		year = min(_y for _y in years if _y >= year_bp)
		
		if year == self.biome_year: return
		
		loader = GdkPixbuf.PixbufLoader.new_with_mime_type('image/png')
		loader.write(Path(f'maps/{year}.png').read_bytes())
		loader.close()
		pixbuf = loader.get_pixbuf()
		self.biome_image = Gdk.cairo_surface_create_from_pixbuf(pixbuf, 0, None)
		self.biome_image_width = pixbuf.get_width()
		self.biome_image_height = pixbuf.get_height()
		self.biome_year = year
		
		self.invalidate('render_grid')
	
	@surface
	def render_grid(self):
		terrain_scale = self.terrain_scale
		viewport_width, viewport_height, viewport_left, viewport_right, viewport_top, viewport_bottom = self.viewport_extents()
		#print("render_grid", viewport_width, viewport_height, self.terrain_scale)
		
		surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, None)
		ctx = cairo.Context(surface)
		ctx.scale(1/self.terrain_scale, 1/self.terrain_scale)
		
		ctx.save()
		ctx.translate(-self.earth_horizontal_size / 2, -self.earth_vertical_size / 2)
		ctx.scale(self.earth_horizontal_size / self.earth_image_width, self.earth_vertical_size / self.earth_image_height)
		ctx.set_source_surface(self.earth_image)
		ctx.rectangle(0, 0, self.earth_image_width, self.earth_image_height)
		ctx.clip()
		ctx.paint()
		ctx.restore()
		
		ctx.save()
		ctx.translate(-self.earth_horizontal_size / 2, -self.earth_vertical_size / 2)
		ctx.scale(self.earth_horizontal_size / self.biome_image_width, self.earth_vertical_size / self.biome_image_height)
		ctx.set_source_surface(self.biome_image)
		ctx.rectangle(0, 0, self.biome_image_width, self.biome_image_height)
		ctx.clip()
		ctx.paint_with_alpha(0.5)
		ctx.restore()
		
		min_viewport_top = -self.earth_vertical_size / 2
		max_viewport_bottom = self.earth_vertical_size / 2
		viewport_top = max(min_viewport_top, viewport_top)
		viewport_bottom = min(max_viewport_bottom, viewport_bottom)
		
		if terrain_scale <= 10:
			ctx.set_line_width(2.5 * terrain_scale)
			ctx.set_source_rgba(0, 0, 0, 0.8)
			
			#ctx.move_to(0, viewport_top)
			#ctx.line_to(0, viewport_bottom)
			#ctx.stroke()
			
			for x in self.grid_lines_horizontal(self.earth_horizontal_size / 2):
				ctx.move_to(x, viewport_top)
				ctx.line_to(x, viewport_bottom)
				ctx.stroke()
			for y in self.grid_lines_vertical(self.earth_vertical_size / 2, min_viewport_top=viewport_top, max_viewport_bottom=viewport_bottom):
				ctx.move_to(viewport_left, y)
				ctx.line_to(viewport_right, y)
				ctx.stroke()
		
		if terrain_scale <= 10:
			ctx.set_line_width(1 * terrain_scale)
			ctx.set_source_rgba(0.65, 0.65, 0.65, 0.6)
			for x in self.grid_lines_horizontal(self.earth_horizontal_size / 24):
				ctx.move_to(x, viewport_top)
				ctx.line_to(x, viewport_bottom)
				ctx.stroke()
			for y in self.grid_lines_vertical(self.earth_vertical_size / 12, min_viewport_top=viewport_top, max_viewport_bottom=viewport_bottom):
				ctx.move_to(viewport_left, y)
				ctx.line_to(viewport_right, y)
				ctx.stroke()
		
		if terrain_scale <= 4:
			ctx.set_line_width(1 * terrain_scale)
			ctx.set_source_rgba(0.85, 0.85, 0.85, 0.4 * max(0, 4 - terrain_scale) / 4)
			for x in self.grid_lines_horizontal(self.earth_horizontal_size / 360):
				ctx.move_to(x, viewport_top)
				ctx.line_to(x, viewport_bottom)
				ctx.stroke()
			for y in self.grid_lines_vertical(self.earth_vertical_size / 180, min_viewport_top=viewport_top, max_viewport_bottom=viewport_bottom):
				ctx.move_to(viewport_left, y)
				ctx.line_to(viewport_right, y)
				ctx.stroke()
		
		surface.flush()
		return surface


class UserInterface:
	def __getattr__(self, attr):
		widget = self.builder.get_object(attr)
		if widget != None:
			setattr(self, attr, widget)
			return widget
		else:
			raise AttributeError(gettext("Attribute not found in object nor in builder:") + " " + attr)
	
	def __init__(self):
		self.builder = Gtk.Builder()
		#self.builder.set_translation_domain(translation)
		self.builder.add_from_file('chronomaps.glade')
		self.builder.connect_signals(self)
	
	def add_map_widget(self, widget):
		self.map_widget = widget
		self.main_box.pack_start(widget, True, True, 0)
		self.main_box.reorder_child(widget, 0)
	
	def update_year_bp(self, *args):
		y = int(self.entry_year_bp.get_text())
		if y > 120000:
			self.entry_year_bp.set_text("120000")
		elif y < 0:
			self.entry_year_bp.set_text("0")
		else:
			#self.adjustment_year_bp()
			self.map_widget.set_year_bp(y)
	
	def slide_year_bp(self, *args):
		e = float(self.adjustment_year_bp.get_value())
		y = math.ceil(120000 * ((1.05 ** e) / (1.05 ** 100)))
		self.entry_year_bp.set_text(str(y))


if __name__ == '__main__':
	import signal
	import sys
	import os
	

	#window = gtk.Window(type=gtk.WindowType.TOPLEVEL)
	#window.set_title('Chrono Maps')
	
	ui = UserInterface()
	
	map_widget = ChronoMaps()
	map_widget.exit_action = ui.window.close
	ui.add_map_widget(map_widget)
	
	#header_bar = gtk.HeaderBar()
	#window.set_titlebar(header_bar)
	ui.window.show_all()
	#window.get_titlebar().hide()
	ui.window.maximize()
	
	mainloop = GLib.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())	
	ui.window.connect('destroy', lambda window: mainloop.quit())
	
	if os.environ.get('GDK_BACKEND', None) == 'broadway':
		map_widget.x11_fixes = False
	
	#widget.animation(10)
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()




