#!/usr/bin/python3
#-*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject
from gi.repository import GLib as glib

import cairo
import math
from itertools import product
from time import monotonic



def quantize_down(x, m):
	return x - x % m


def quantize_up(x, m):
	return x - x % m + m


def float_range(start, stop, step):
	if not start < stop:
		raise ValueError
	if not step > 0:
		raise ValueError
	
	k = start
	while k < stop:
		yield k
		k += step

def quantized_float_range(start, stop, step):
	if not start < stop:
		raise ValueError
	if not step > 0:
		raise ValueError
	
	for n in range(math.floor(start / step), math.ceil(stop / step)):
		yield n * step


def surface(old_method):
	fname = old_method.__name__
	
	def new_method(self, *args):
		if args:
			key = (fname,) + args
		else:
			key = fname
		
		if key not in self.rendered_surface:
			surface = old_method(self, *args)
			self.rendered_surface[key] = surface
			return surface
		else:
			return self.rendered_surface[key]
	
	new_method.__name__ = fname
	return new_method


class GameWidget(gtk.DrawingArea):
	def __init__(self):
		super().__init__()
		self.set_can_focus(True)
		
		self.default_background_color = 1, 1, 1
		self.rendered_surface = {}
		
		self.terrain_x = 0
		self.terrain_y = 0
		self.terrain_scale = 1
		
		self.screen_width = 1
		self.screen_height = 1
		
		self.scroll_redraw_rect_x = 250
		self.scroll_redraw_rect_y = 250
		self.double_tap_interval = 0.2
		self.terrain_scale_min = 0.1
		self.terrain_scale_max = 10
		
		self.recalculate_viewport()
		
		self.pointer_primary_x = 0
		self.pointer_primary_y = 0
		self.pointer_secondary_x = 0
		self.pointer_secondary_y = 0
		
		self.mouse_buttons = set()
		self.double_click = False
		self.double_tap = False
		self.last_tap = -1000
		self.primary_sequence = None
		
		self.terrain_scrolling = False
		self.menu_showing = False
		self.default_menu_ring_color = 1, 1, 1, 0.15
		self.menu_positions = 12
		self.menu_start_angle = 0
		
		self.path_points = []
		self.default_path_width = 3
		self.default_path_color = 0, 1, 0, 1
		
		self.animation_freq = 0
		self.animation_event = False
		self.invalidate_event = False
		
		self.x11_fixes = True
		
		self.connect('configure-event', self.handle_configure_event)
		self.connect('draw', self.handle_draw)
		
		self.connect('motion-notify-event', self.handle_mouse_event)
		self.connect('button-press-event', self.handle_mouse_event)
		self.connect('button-release-event', self.handle_mouse_event)
		self.connect('touch-event', self.handle_touch_event)
		self.connect('scroll-event', self.handle_scroll_event)
		
		#self.connect('dblclick', self.handle_mouse_event)
		#self.connect('auxclicked', self.handle_auxclicked)
		#self.connect('clicked', self.handle_dblclicked)
		#self.connect('key-press-event', self.handle_key_press_event)
		#self.connect('key-release-event', self.handle_key_release_event)
		
		self.add_events(gdk.EventMask.POINTER_MOTION_MASK)
		self.add_events(gdk.EventMask.BUTTON_RELEASE_MASK)
		self.add_events(gdk.EventMask.BUTTON_PRESS_MASK)
		self.add_events(gdk.EventMask.SMOOTH_SCROLL_MASK)
		self.add_events(gdk.EventMask.TOUCH_MASK)
		
		#self.add_events(gdk.EventMask.KEY_PRESS_MASK)
		#self.add_events(gdk.EventMask.KEY_RELEASE_MASK)
	
	def invalidate(self, *keys):
		for key in keys:
			try:
				self.rendered_surface[key].finish()
				del self.rendered_surface[key]
			except KeyError:
				pass
		
		self.queue_draw()
		self.invalidate_event = True
	
	def animation(self, freq):
		if freq and not self.animation_freq:
			self.animation_timer = glib.timeout_add(1000 / freq, self.handle_animation)
			self.animation_freq = freq
		elif freq and self.animation_freq:
			gobject.source_remove(self.animation_timer)
			self.animation_timer = glib.timeout_add(1000 / freq, self.handle_animation)
			self.animation_freq = freq
		elif not freq and self.animation_freq:
			gobject.source_remove(self.animation_timer)
			self.animation_freq = 0
			del self.animation_timer
	
	def recalculate_viewport(self):
		self.viewport_width = self.screen_width * self.terrain_scale
		#print("recalculate_viewport", self.viewport_width, self.screen_width, self.terrain_scale)
		self.viewport_height = self.screen_height * self.terrain_scale
		self.viewport_left = (-self.screen_width / 2 - self.terrain_x) * self.terrain_scale
		self.viewport_right = (self.screen_width / 2 - self.terrain_x) * self.terrain_scale
		self.viewport_top = (-self.screen_height / 2 - self.terrain_y) * self.terrain_scale
		self.viewport_bottom = (self.screen_height / 2 - self.terrain_y) * self.terrain_scale
	
	def begin_terrain_scroll(self):
		assert not self.terrain_scrolling
		self.terrain_x_orig = self.terrain_x
		self.terrain_y_orig = self.terrain_y
		self.terrain_x_redrawn = 0
		self.terrain_y_redrawn = 0
		self.terrain_scrolling = True
	
	def continue_terrain_scroll(self):
		assert self.terrain_scrolling
		
		dx = self.pointer_secondary_x - self.pointer_primary_x
		dy = self.pointer_secondary_y - self.pointer_primary_y
		self.terrain_x = self.terrain_x_orig + dx
		self.terrain_y = self.terrain_y_orig + dy
		
		if abs(dx - self.terrain_x_redrawn) >= self.scroll_redraw_rect_x or abs(dy - self.terrain_y_redrawn) >= self.scroll_redraw_rect_y:
			self.invalidate('render_grid', 'render_items')
			self.terrain_x_redrawn = dx
			self.terrain_y_redrawn = dy
		
		self.recalculate_viewport()
		self.invalidate()
	
	def end_terrain_scroll(self):
		assert self.terrain_scrolling
		self.terrain_x = self.terrain_x_orig + self.pointer_secondary_x - self.pointer_primary_x
		self.terrain_y = self.terrain_y_orig + self.pointer_secondary_y - self.pointer_primary_y
		self.recalculate_viewport()
		self.invalidate('render_grid', 'render_items')
		del self.terrain_x_orig
		del self.terrain_y_orig
		del self.terrain_x_redrawn
		del self.terrain_y_redrawn
		self.terrain_scrolling = False
	
	def begin_menu_action(self):
		assert not self.menu_showing
		self.menu_showing = True
		self.invalidate('render_menu')
	
	def continue_menu_action(self):
		assert self.menu_showing
		self.invalidate('render_menu')
	
	def end_menu_action(self):
		assert self.menu_showing
		self.menu_showing = False
		self.invalidate('render_menu')
		self.select_action()
	
	def begin_path_follow(self):
		assert not self.path_points
		self.path_points.append((self.pointer_secondary_x, self.pointer_secondary_y))
		self.invalidate('render_path')
	
	def continue_path_follow(self):
		assert self.path_points
		self.path_points.append((self.pointer_secondary_x, self.pointer_secondary_y))
		self.invalidate('render_path')
	
	def end_path_follow(self):
		assert self.path_points
		self.path_points.append((self.pointer_secondary_x, self.pointer_secondary_y))
		self.invalidate('render_path')
		self.path_ready()
		self.path_points.clear()
		self.invalidate('render_path')
	
	def select_action(self):
		dx = self.pointer_secondary_x - self.pointer_primary_x
		dy = self.pointer_secondary_y - self.pointer_primary_y
		
		radius = self.menu_radius
		itno = self.menu_positions
		
		active_n = None
		if radius * 0.6 <= math.hypot(dx, -dy) <= radius:
			nn = (math.degrees(math.atan2(dx, -dy)) - self.menu_start_angle) % 360 * itno / 360
			n = round(nn)
			if abs(n - nn) <= 0.25:
				active_n = n % itno
		
		if active_n != None:
			self.execute_action(active_n)
	
	def execute_action(self, n):
		print("menu action:", n)
	
	def path_ready(self):
		print("path_ready", len(self.path_points))
		self.invalidate('render_path')
	
	@surface
	def render_path(self):
		surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, cairo.Rectangle(0, 0, self.screen_width, self.screen_height))
		ctx = cairo.Context(surface)
		
		ctx.move_to(*self.path_points[0])
		for p in self.path_points:
			ctx.line_to(*p)
		
		ctx.set_line_width(self.default_path_width)
		ctx.set_source_rgba(*self.default_path_color)
		ctx.stroke()
		
		surface.flush()
		return surface
	
	@surface
	def render_menu(self):
		dx = self.pointer_secondary_x - self.pointer_primary_x
		dy = self.pointer_secondary_y - self.pointer_primary_y
		
		radius = self.menu_radius
		
		surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, cairo.Rectangle(-radius, -radius, 2 * radius, 2 * radius))
		ctx = cairo.Context(surface)
		
		ctx.arc(0, 0, radius, 0, 2 * math.pi)
		if self.default_menu_ring_color:
			ctx.clip_preserve()
			ctx.arc(0, 0, radius * 0.6, 0, 2 * math.pi)
			ctx.set_fill_rule(cairo.FillRule.EVEN_ODD)
			ctx.set_source_rgba(*self.default_menu_ring_color)
			ctx.fill()
		else:
			ctx.clip()
		
		itno = self.menu_positions
		
		active_n = None
		if radius * 0.6 <= math.hypot(dx, -dy) <= radius:
			nn = (math.degrees(math.atan2(dx, -dy)) - self.menu_start_angle) % 360 * itno / 360
			n = round(nn)
			if abs(n - nn) <= 0.25:
				active_n = n % itno
		
		for n in range(itno):
			a = math.radians((self.menu_start_angle + n * 360 / itno) % 360)
			x = 0.8 * radius * math.sin(a)
			y = -0.8 * radius * math.cos(a)
			ctx.arc(x, y, 0.2 * radius, 0, 2 * math.pi)
			if n == active_n:
				ctx.set_source_surface(self.render_menu_item_active(n), x, y)
			else:
				ctx.set_source_surface(self.render_menu_item_inactive(n), x, y)
			ctx.fill()
		
		surface.flush()
		return surface
	
	@surface
	def render_menu_item_inactive(self, n):
		radius = self.menu_radius * 0.2
		palette = [(1, 0, 0), (1, 0.5, 0), (1, 1, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1), (1, 0, 1), (0.6, 0.5, 0.7), (0.6, 0.7, 0.8), (0.6, 0.8, 0.6), (0.7, 0.6, 0), (0.5, 0.2, 0.2)]
		surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, cairo.Rectangle(-radius, -radius, 2 * radius, 2 * radius))
		ctx = cairo.Context(surface)
		
		ctx.arc(0, 0, radius, 0, 2 * math.pi)
		ctx.set_source_rgb(*[_c / 2 for _c in palette[n]])
		ctx.fill()
		
		ctx.move_to(-15, 20)
		ctx.set_font_size(55)
		ctx.text_path(str(n))
		ctx.set_source_rgb(*[_c for _c in palette[n]])
		ctx.stroke()
		
		surface.flush()
		return surface
	
	@surface
	def render_menu_item_active(self, n):
		radius = self.menu_radius * 0.2
		palette = [(1, 0, 0), (1, 0.5, 0), (1, 1, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1), (1, 0, 1), (0.6, 0.5, 0.7), (0.6, 0.7, 0.8), (0.6, 0.8, 0.6), (0.7, 0.6, 0), (0.5, 0.2, 0.2)]
		surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, cairo.Rectangle(-radius, -radius, 2 * radius, 2 * radius))
		ctx = cairo.Context(surface)
		
		ctx.arc(0, 0, radius, 0, 2 * math.pi)
		ctx.set_source_rgb(*[_c for _c in palette[n]])
		ctx.fill_preserve()
		ctx.set_source_rgb(*[_c / 2 for _c in palette[n]])
		ctx.stroke()
		
		ctx.move_to(-15, 20)
		ctx.set_font_size(55)
		ctx.text_path(str(n))
		ctx.set_source_rgb(*[_c / 2 for _c in palette[n]])
		ctx.fill()
		
		surface.flush()
		return surface
	
	@surface
	def render_background(self):
		"Workaround for X11 backend where transparency is broken unless there is a pixmap behind."
		surface = cairo.ImageSurface(cairo.Format.RGB24, self.screen_width, self.screen_height)
		ctx = cairo.Context(surface)
		ctx.set_source_rgb(*self.default_background_color)
		ctx.paint()
		surface.flush()
		return surface
	
	def viewport_extents(self):
		viewport_width = self.viewport_width + 2 * self.scroll_redraw_rect_x * self.terrain_scale
		viewport_height = self.viewport_height + 2 * self.scroll_redraw_rect_y * self.terrain_scale
		viewport_left = self.viewport_left - self.scroll_redraw_rect_x * self.terrain_scale
		viewport_right = self.viewport_right + self.scroll_redraw_rect_x * self.terrain_scale
		viewport_top = self.viewport_top - self.scroll_redraw_rect_y * self.terrain_scale
		viewport_bottom = self.viewport_bottom + self.scroll_redraw_rect_y * self.terrain_scale
		return viewport_width, viewport_height, viewport_left, viewport_right, viewport_top, viewport_bottom
	
	#def grid_lines_horizontal(self, w, min_viewport_left=None, max_viewport_right=None):
	#	viewport_width, viewport_height, viewport_left, viewport_right, viewport_top, viewport_bottom = self.viewport_width, self.viewport_height, self.viewport_left, self.viewport_right, self.viewport_top, self.viewport_bottom
	#	if min_viewport_left is not None: viewport_left = max(viewport_left, min_viewport_left)
	#	if max_viewport_right is not None: viewport_right = min(viewport_right, max_viewport_right)
	#	yield from float_range(quantize_down(viewport_left, w), quantize_up(viewport_right, w), w)
	
	#def grid_lines_vertical(self, h, min_viewport_top=None, max_viewport_bottom=None):
	#	viewport_width, viewport_height, viewport_left, viewport_right, viewport_top, viewport_bottom = self.viewport_width, self.viewport_height, self.viewport_left, self.viewport_right, self.viewport_top, self.viewport_bottom
	#	if min_viewport_top is not None: viewport_top = max(viewport_top, min_viewport_top)
	#	if max_viewport_bottom is not None: viewport_bottom = min(viewport_bottom, max_viewport_bottom)
	#	yield from float_range(quantize_down(viewport_top, h), quantize_up(viewport_bottom, h), h)
	
	#def grid_points(self, w, h):
	#	viewport_width, viewport_height, viewport_left, viewport_right, viewport_top, viewport_bottom = self.viewport_width, self.viewport_height, self.viewport_left, self.viewport_right, self.viewport_top, self.viewport_bottom
	#	yield from product(float_range(quantize_down(viewport_left, w), quantize_up(viewport_right, w), w), float_range(quantize_down(viewport_top, h), quantize_up(viewport_bottom, h), h))
	
	def grid_lines_horizontal(self, w, min_viewport_left=None, max_viewport_right=None):
		viewport_width, viewport_height, viewport_left, viewport_right, viewport_top, viewport_bottom = self.viewport_width, self.viewport_height, self.viewport_left, self.viewport_right, self.viewport_top, self.viewport_bottom
		if min_viewport_left is not None: viewport_left = max(viewport_left, min_viewport_left)
		if max_viewport_right is not None: viewport_right = min(viewport_right, max_viewport_right)
		yield from float_range(quantize_down(viewport_left, w), quantize_up(viewport_right, w), w)
	
	def grid_lines_vertical(self, h, min_viewport_top=None, max_viewport_bottom=None):
		viewport_width, viewport_height, viewport_left, viewport_right, viewport_top, viewport_bottom = self.viewport_width, self.viewport_height, self.viewport_left, self.viewport_right, self.viewport_top, self.viewport_bottom
		if min_viewport_top is not None: viewport_top = max(viewport_top, min_viewport_top)
		if max_viewport_bottom is not None: viewport_bottom = min(viewport_bottom, max_viewport_bottom)
		yield from float_range(quantize_down(viewport_top, h), quantize_up(viewport_bottom, h), h)
	
	def grid_points(self, w, h):
		viewport_width, viewport_height, viewport_left, viewport_right, viewport_top, viewport_bottom = self.viewport_width, self.viewport_height, self.viewport_left, self.viewport_right, self.viewport_top, self.viewport_bottom
		yield from product(quantized_float_range(viewport_left, viewport_right, w), quantized_float_range(viewport_top, viewport_bottom, h))
	
	@surface
	def render_grid(self):
		surface = cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, None)
		ctx = cairo.Context(surface)
		ctx.scale(1 / self.terrain_scale, 1 / self.terrain_scale)
		
		ctx.set_source_rgb(0, 1, 0)
		for x, y in self.grid_points(512, 512):
			ctx.rectangle(x - 10, y - 10, 20, 20)
		ctx.fill()
		
		if self.terrain_scale < 3:
			ctx.set_source_rgb(0.5, 1, 0.5)
			for x, y in self.grid_points(32, 32):
				ctx.rectangle(x - 1, y - 1, 2, 2)
			ctx.fill()
		
		ctx.set_line_width(1)
		ctx.set_source_rgb(0, 0, 0)
		ctx.rectangle(-1024, -1024, 2048, 2048)
		ctx.stroke()
		
		surface.flush()
		return surface
	
	@surface
	def render_items(self):
		return cairo.RecordingSurface(cairo.Content.COLOR_ALPHA, None)
	
	@staticmethod
	def rectangles_intersect(one, two):
		a = one.x <= two.x <= one.x + one.width
		b = one.x <= two.x + two.width <= one.x + one.width

		c = two.x <= one.x <= two.x + two.width
		d = two.x <= one.x + one.width <= two.x + two.width

		e = one.y <= two.y <= one.y + one.height
		f = one.y <= two.y + two.height <= one.y + one.height

		g = two.y <= one.y <= two.y + two.height
		h = two.y <= one.y + one.height <= two.y + two.height
		
		return (a or b or c or d) and (e or f or g or h)
	
	def list_animated_objects(self):
		return []
	
	def draw_animations(self, ctx):
		pass
	
	def handle_configure_event(self, drawingarea, event):
		rect = self.get_allocation()
		self.screen_width = rect.width
		self.screen_height = rect.height
		self.menu_radius = min([self.screen_width / 4, self.screen_height / 4, 250])
		self.recalculate_viewport()
		self.invalidate('render_grid', 'render_items', 'render_background')
	
	def handle_draw(self, drawingarea, ctx):
		clip_rectangles = ctx.copy_clip_rectangle_list()
		if len(clip_rectangles) == 1 and clip_rectangles[0] == cairo.Rectangle(0, 0, self.screen_width, self.screen_height):
			fullscreen_event = True
		else:
			fullscreen_event = False
		
		if self.x11_fixes:
			ctx.set_source_surface(self.render_background())
			ctx.paint()
		else:
			ctx.set_source_rgb(*self.default_background_color)
			ctx.paint()
		
		ctx.save()
		
		ctx.translate(self.screen_width / 2 + self.terrain_x, self.screen_height / 2 + self.terrain_y)
		#ctx.scale(1 / self.terrain_scale, 1 / self.terrain_scale)
		
		if (not self.animation_event) or fullscreen_event or self.invalidate_event:
			ctx.set_source_surface(self.render_grid())
			ctx.paint()
			
			ctx.set_source_surface(self.render_items())
			ctx.paint()
		
		if self.animation_freq:
			self.draw_animations(ctx)
		
		ctx.restore()
		
		if self.path_points:
			ctx.save()
			ctx.set_source_surface(self.render_path())
			ctx.paint()	
			ctx.restore()
		
		if self.menu_showing:
			ctx.save()
			ctx.set_source_surface(self.render_menu(), self.pointer_primary_x, self.pointer_primary_y)
			ctx.paint()	
			ctx.restore()
		
		self.animation_event = False
		self.invalidate_event = False
	
	def handle_animation(self):
		self.animation_event = True
		tx = self.screen_width / 2 + self.terrain_x
		ty = self.screen_height / 2 + self.terrain_y
		for x, y, w, h in self.list_animated_objects():
			self.queue_draw_area(tx + x / self.terrain_scale, ty + y / self.terrain_scale, w / self.terrain_scale, h / self.terrain_scale)
		return True
	
	def handle_mouse_event(self, drawingarea, event):
		event_type = event.get_event_type()
		input_source = event.get_source_device().get_source()
		
		#if event_type != gdk.EventType.MOTION_NOTIFY:
		#	print("mouse event", repr(event_type), repr(source), event.button if hasattr(event, 'button') else "")
		
		if input_source == gdk.InputSource.TOUCHSCREEN:
			return
		
		button = event.button if hasattr(event, 'button') else None
		
		if input_source == gdk.InputSource.PEN:
			if button == 1:
				button = 2
			elif button == 2:
				button = 3
		
		if event_type == gdk.EventType.BUTTON_PRESS:
			if not self.terrain_scrolling and not self.menu_showing:
				self.pointer_primary_x = self.pointer_secondary_x = event.x
				self.pointer_primary_y = self.pointer_secondary_y = event.y
				
				if button == 1:
					self.begin_terrain_scroll()
				elif button == 2:
					self.begin_path_follow()
				elif button == 3:
					self.begin_menu_action()
			else:
				self.pointer_secondary_x = event.x
				self.pointer_secondary_y = event.y
				
				if self.terrain_scrolling:
					self.continue_terrain_scroll()
				
				if self.path_points:
					self.continue_path_follow()
				
				if self.menu_showing:
					self.continue_menu_action()
			
			self.mouse_buttons.add(button)
		
		elif event_type == gdk.EventType._2BUTTON_PRESS:
			if button == 1:
				if self.menu_showing:
					self.end_menu_action()
				
				if self.terrain_scrolling:
					self.end_terrain_scroll()
				
				self.double_click = True
				self.pointer_primary_x = self.pointer_secondary_x = event.x
				self.pointer_primary_y = self.pointer_secondary_y = event.y
				self.begin_menu_action()
		
		elif event_type == gdk.EventType.MOTION_NOTIFY:
			self.pointer_secondary_x = event.x
			self.pointer_secondary_y = event.y
			
			if self.terrain_scrolling:
				self.continue_terrain_scroll()
			
			if self.path_points:
				self.continue_path_follow()
			
			if self.menu_showing:
				self.continue_menu_action()
		
		elif event_type == gdk.EventType.BUTTON_RELEASE:
			self.pointer_secondary_x = event.x
			self.pointer_secondary_y = event.y
			
			if self.double_click:
				self.double_click = False
			else:
				if self.terrain_scrolling:
					self.end_terrain_scroll()
				
				if self.path_points:
					self.end_path_follow()
				
				if self.menu_showing:
					self.end_menu_action()
			
			self.mouse_buttons.remove(button)
	
	def handle_touch_event(self, drawingarea, event):
		#print("touch event", str(event.get_event_type()), str(event.get_source_device().get_source()))
		
		if event.get_source_device().get_source() != gdk.InputSource.TOUCHSCREEN:
			return
		
		event_type = event.get_event_type()
		
		if event_type == gdk.EventType.TOUCH_BEGIN:
			if self.primary_sequence == None:
				self.primary_sequence = event.sequence

				mt = monotonic()
				self.double_tap = (mt - self.last_tap < self.double_tap_interval)
				self.last_tap = mt
				
				self.pointer_secondary_x = event.x
				self.pointer_secondary_y = event.y
				
				#if self.menu_showing:
				#	self.end_menu_action()
				
				if self.terrain_scrolling:
					self.end_terrain_scroll()
								
				if self.menu_showing:
					self.continue_menu_action()
				elif self.double_tap:
					self.pointer_primary_x = event.x
					self.pointer_primary_y = event.y
					self.begin_menu_action()
				else:
					self.pointer_primary_x = event.x
					self.pointer_primary_y = event.y
					self.begin_terrain_scroll()
			
			else:
				if self.terrain_scrolling:
					self.end_terrain_scroll()
					self.pointer_primary_x = self.pointer_secondary_x
					self.pointer_primary_y = self.pointer_secondary_y
				
				self.pointer_secondary_x = event.x
				self.pointer_secondary_y = event.y
				
				if self.menu_showing:
					self.continue_menu_action()
				else:
					self.begin_menu_action()
		
		elif event_type == gdk.EventType.TOUCH_UPDATE:
			self.pointer_secondary_x = event.x
			self.pointer_secondary_y = event.y
			
			if event.sequence == self.primary_sequence and self.terrain_scrolling:
				self.continue_terrain_scroll()
			elif self.menu_showing:
				self.continue_menu_action()
		
		elif event_type == gdk.EventType.TOUCH_END:
			if event.sequence == self.primary_sequence:
				if self.terrain_scrolling or self.menu_showing:
					self.pointer_secondary_x = event.x
					self.pointer_secondary_y = event.y
					
					if self.terrain_scrolling:
						self.end_terrain_scroll()
					
					if self.menu_showing and not self.double_tap:
						self.end_menu_action()
					
					#self.pointer_secondary_x = self.pointer_primary_x
					#self.pointer_secondary_y = self.pointer_primary_y
					#self.pointer_primary_x = event.x
					#self.pointer_primary_y = event.y
				
				self.primary_sequence = None
				self.double_tap = None
			else:
				self.pointer_secondary_x = event.x
				self.pointer_secondary_y = event.y
				
				if self.menu_showing:
					self.end_menu_action()
		
		elif event_type == gdk.EventType.TOUCH_CANCEL:
			pass
	
	def handle_scroll_event(self, drawingarea, event):
		dy = event.get_scroll_deltas().delta_y
		x = event.x
		y = event.y
		
		factor = 1 + dy / 50
		scale = self.terrain_scale * factor
		if scale < self.terrain_scale_min:
			factor = self.terrain_scale_min / self.terrain_scale
			scale = self.terrain_scale_min
		if scale > self.terrain_scale_max:
			factor = self.terrain_scale_max / self.terrain_scale
			scale = self.terrain_scale_max
		
		self.terrain_x = -(event.x - self.terrain_x - self.screen_width / 2) / factor - self.screen_width / 2 + event.x
		self.terrain_y = -(event.y - self.terrain_y - self.screen_height / 2) / factor - self.screen_height / 2 + event.y
		self.terrain_scale = scale
		#print("terrain_scale =", scale)
		self.recalculate_viewport()
		self.invalidate('render_grid', 'render_items')


if __name__ == '__main__':
	import signal
	import sys
	import os
	
	window = gtk.Window(type=gtk.WindowType.TOPLEVEL)
	window.set_name('main_window')
	
	widget = GameWidget()
	
	window.add(widget)
	
	header_bar = gtk.HeaderBar()
	window.set_titlebar(header_bar)
	window.show_all()
	window.get_titlebar().hide()
	window.maximize()
	
	mainloop = glib.MainLoop()
	signal.signal(signal.SIGTERM, lambda signum, frame: mainloop.quit())	
	window.connect('destroy', lambda window: mainloop.quit())
	
	if os.environ.get('GDK_BACKEND', None) == 'broadway':
		widget.x11_fixes = False
	
	widget.animation(10)
	
	try:
		mainloop.run()
	except KeyboardInterrupt:
		print()



