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
	biome_imgs = 'biome', 'svg'
	topo_imgs = 'topo', 'png'
	
	def __init__(self):
		super().__init__()
		self.earth_degree = 42
		self.earth_horizontal_size = self.earth_degree * 360
		self.earth_vertical_size = self.earth_degree * 180		
		self.biome_year = None
		self.set_year_bp(0)
	
	def load_pixbuf(self, filename, mime):
		loader = GdkPixbuf.PixbufLoader.new_with_mime_type(mime)
		loader.write(Path(filename).read_bytes())
		loader.close()
		pixbuf = loader.get_pixbuf()
		image = Gdk.cairo_surface_create_from_pixbuf(pixbuf, 0, None)
		width = pixbuf.get_width()
		height = pixbuf.get_height()
		return image, width, height
	
	def load_svg(self, filename):
		rsvg = Rsvg.Handle.new_from_file(filename)
		image = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, (0, 0, rsvg.props.width, rsvg.props.height))
		ctx = cairo.Context(image)
		
		rect = Rsvg.Rectangle()
		rect.width = rsvg.props.width
		rect.height = rsvg.props.height
		
		rsvg.render_document(ctx, rect)
		
		width = rsvg.props.width
		height = rsvg.props.height
		return image, width, height
	
	@surface
	def load_image(self, filename):
		ext = filename.split('.')[-1]
		if ext == 'png':
			return self.load_pixbuf(filename, 'image/png')
		elif ext == 'svg':
			return self.load_svg(filename)
		else:
			raise NotImplementedError
	
	def set_year_bp(self, year_bp):
		biome_dir, biome_ext = self.biome_imgs
		years = [int(p.stem) for p in Path(biome_dir).iterdir() if p.suffix == '.' + biome_ext]
		#print(year_bp, [_y for _y in years if _y >= -year_bp])
		year = min(_y for _y in years if _y >= -year_bp)
		if year == self.biome_year: return
		self.biome_year = year
		self.invalidate('render_grid')
	
	def get_tile(self, x, y, s):
		#print(x, y)
		if s <= 1:
			s = 1
		elif 1 < s <= 2:
			s = 2
		elif 2 < s <= 4:
			s = 4
		else:
			s = 8
		
		if not -180 <= x < 180: x = (x + 180) % 360 - 180
		if not -90 <= y < 90: y = (y + 90) % 180 - 90 
		#print(" ", x, y)
		
		topo_dir, topo_ext = self.topo_imgs
		image, width, height = self.load_image(f'{topo_dir}/{x:+}{y:+}s{s}.{topo_ext}')
		return image, width, height
	
	@surface
	def render_grid(self):
		terrain_scale = self.terrain_scale
		viewport_width, viewport_height, viewport_left, viewport_right, viewport_top, viewport_bottom = self.viewport_extents()
		
		surface = cairo.ImageSurface(cairo.Format.RGB24, self.screen_width + 2 * self.scroll_redraw_rect_x, self.screen_height + 2 * self.scroll_redraw_rect_y)
		ctx = cairo.Context(surface)
		ctx.translate((self.screen_width + 2 * self.scroll_redraw_rect_x) / 2 + self.terrain_x, (self.screen_height + 2 * self.scroll_redraw_rect_y) / 2 + self.terrain_y)
		ctx.scale(1 / terrain_scale, 1 / terrain_scale)
		ctx.set_source_rgb(1, 1, 1)
		ctx.paint()
		
		ctx.set_operator(cairo.Operator.HSL_LUMINOSITY)
		for x, y in self.grid_points(self.earth_degree * 15, self.earth_degree * 15):
			xx = int(x / self.earth_degree)
			yy = -int(y / self.earth_degree)
			if not -90 <= yy < 90: continue
			surf, w, h = self.get_tile(xx, yy, terrain_scale)
			ctx.save()
			ctx.translate(x, y)
			ctx.rectangle(0, 0, self.earth_degree * 15, self.earth_degree * 15)
			ctx.clip()
			ctx.scale((self.earth_degree * 15 + 1) / w, (self.earth_degree * 15 + 1) / h)
			ctx.set_source_surface(surf)
			ctx.paint()
			ctx.restore()
		
		ctx.set_operator(cairo.Operator.OVER)
		ctx.save()
		ctx.translate(-self.earth_horizontal_size / 2, -self.earth_vertical_size / 2 + (15 * self.earth_degree))
		biome_dir, biome_ext = self.biome_imgs
		biome_image, biome_image_width, biome_image_height = self.load_image(f'{biome_dir}/{self.biome_year}.{biome_ext}')
		ctx.scale(self.earth_horizontal_size / biome_image_width, self.earth_vertical_size / biome_image_height)
		ctx.set_source_surface(biome_image)
		ctx.rectangle(0, 0, biome_image_width, biome_image_height)
		ctx.clip()
		ctx.paint()
		ctx.restore()
		
		'''
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
		'''
		
		surface.flush()
		
		surface_r = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, None)
		ctx = cairo.Context(surface_r)
		ctx.translate(-(self.screen_width + 2 * self.scroll_redraw_rect_x) / 2 - self.terrain_x, -(self.screen_height + 2 * self.scroll_redraw_rect_y) / 2 - self.terrain_y)
		ctx.set_source_surface(surface)
		ctx.paint()
		surface_r.flush()
		return surface_r


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




