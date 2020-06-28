import math
import pyglet
from pyglet.window import key, mouse
from pyglet import gl
import time

import ui


class Map(ui.View):
    def __init__(self, state, background=(0, 0, 0), **kwargs):
        super().__init__(background=background, **kwargs)
        self.state = state
        self._tx = 0
        self._ty = 0
        self._scale = 70
        self._screen_width = None
        self._screen_height = None
        self._pan_speed_x = 0
        self._pan_speed_y = 0
        self._show_grid = True
        self._last_pan_update = time.time()
        self.show_veils = False
        self._veil_lines = []

    def _bounding_box(self):
        minx, maxx = 1E6, -1E6
        miny, maxy = 1E6, -1E6
        for token in self.state.current_page.tokens:
            x0, y0 = token.position
            if x0 < minx: minx = x0
            if y0 < miny: miny = y0
            w, h = token.fragment.size
            if x0 + w > maxx: maxx = x0 + w
            if y0 + h > maxy: maxy = y0 + h
        return minx, maxx, miny, maxy

    def screen_to_map(self, screen_x, screen_y):
        """Convert screen coordinates to map coordinates."""
        return ((screen_x - self._tx) / self._scale,
                (screen_y - self._ty) / self._scale)

    def screen_to_map_delta(self, screen_dx, screen_dy):
        """Convert screen coordinates to map coordinates."""
        return screen_dx / self._scale, screen_dy / self._scale

    def map_to_screen(self, x, y):
        return x * self._scale + self._tx, y * self._scale + self._ty

    def scale_to_fit(self):
        if self.pane.width <= 0: return

        pane_width = self.pane.width
        pane_height = self.pane.height
        offset_x = self.pane.x0
        offset_y = self.pane.y0

        minx, maxx, miny, maxy = self._bounding_box()

        width = maxx - minx
        height = maxy - miny
        scalex = pane_width / width
        scaley = pane_height / height
        self._scale = min(scalex, scaley)
        self._tx = ((pane_width - width * self._scale) / 2 -
                    minx * self._scale + offset_x)
        self._ty = ((pane_height - height * self._scale) / 2 -
                    miny * self._scale + offset_y)

    def zoom(self, screen_x, screen_y, zoom):
        self._scale *= zoom
        self._tx = screen_x - zoom * (screen_x - self._tx)
        self._ty = screen_y - zoom * (screen_y - self._ty)

    def _update_pan(self):
        t = time.time()
        self._tx += (t - self._last_pan_update) * self._pan_speed_x
        self._ty += (t - self._last_pan_update) * self._pan_speed_y
        self._last_pan_update = t

    def pan_vertical(self, speed):
        self._update_pan()
        self._pan_speed_y = speed

    def pan_horizontal(self, speed):
        self._update_pan()
        self._pan_speed_x = speed

    def toggle_grid(self):
        self._show_grid = not self._show_grid

    def _draw_grid(self):
        x0, y0 = self.pane.x0, self.pane.y0
        x1, y1 = self.pane.x1, self.pane.y1

        minx, miny = self.screen_to_map(x0, y0)
        maxx, maxy = self.screen_to_map(x1, y1)

        def draw_lines(check, width):
            lines = []

            for x in range(math.ceil(minx), math.floor(maxx) + 1):
                if not check(x): continue
                screenx, _ = self.map_to_screen(x, 0)
                lines.extend([screenx, y0,
                              screenx, y1])

            for y in range(math.ceil(miny), math.floor(maxy) + 1):
                if not check(y): continue
                _, screeny = self.map_to_screen(0, y)
                lines.extend([x0, screeny,
                              x1, screeny])

            colors = [127, 127, 127] * (len(lines) // 2)
            gl.glLineWidth(width)
            pyglet.graphics.draw(len(lines) // 2, gl.GL_LINES,
                ('v2f', lines),
                ('c3B', colors)
            )

        draw_lines(lambda x: x % 5 != 0, 1)
        draw_lines(lambda x: x % 10 == 5, 2)
        draw_lines(lambda x: x % 10 == 0, 3)

        if self._veil_lines:
            gl.glLineWidth(2)
            colors = [255, 255, 255] * (len(self._veil_lines) // 2 )
            pyglet.graphics.draw(len(self._veil_lines) // 2, gl.GL_LINES,
                ('v2f', self._veil_lines),
                ('c3B', colors)
            )

    def _draw_veils(self):
        triangles = []
        colors = []
        self._veil_lines = []

        for veil in self.state.current_page.veils:
            if (not veil['covered'] and
                (not self.state.is_master or
                 not self.show_veils)): continue
            minx, miny = self.map_to_screen(veil['minx'], veil['miny'])
            maxx, maxy = self.map_to_screen(veil['maxx'], veil['maxy'])
            if (minx >= self.pane.x1 or maxx <= self.pane.x0 or
                miny >= self.pane.y1 or maxy <= self.pane.y0):
                continue
            clamp_x0 = max(self.pane.x0, minx)
            clamp_y0 = max(self.pane.y0, miny)
            clamp_x1 = min(self.pane.x1, maxx)
            clamp_y1 = min(self.pane.y1, maxy)
            triangles.extend([
                clamp_x0, clamp_y0, clamp_x1, clamp_y0, clamp_x1, clamp_y1,
                clamp_x0, clamp_y1, clamp_x0, clamp_y0, clamp_x1, clamp_y1
            ])
            if self.state.is_master:
                if veil['covered']:
                    if self.show_veils:
                        colors.extend([128] * 18)
                    else:
                        colors.extend([64] * 18)
                else:
                    colors.extend([64] * 18)
                if self.show_veils:
                    for x0, y0, x1, y1 in (
                        (clamp_x0, clamp_y0, clamp_x1, clamp_y0),
                        (clamp_x1, clamp_y0, clamp_x1, clamp_y1),
                        (clamp_x1, clamp_y1, clamp_x0, clamp_y1),
                        (clamp_x0, clamp_y1, clamp_x0, clamp_y0)
                    ):
                        if not (x0 <= self.pane.x0 and x1 <= self.pane.x0 or
                                x0 >= self.pane.x1 and x1 >= self.pane.x1 or
                                y0 <= self.pane.y0 and y1 <= self.pane.y0 or
                                y1 >= self.pane.y1 and y1 >= self.pane.y1):
                            self._veil_lines.extend([x0, y0, x1, y1])
            else:
                colors.extend([255] * 18)

        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_ONE, gl.GL_ONE)
        gl.glBlendEquation(gl.GL_FUNC_REVERSE_SUBTRACT)

        pyglet.graphics.draw(len(triangles) // 2, gl.GL_TRIANGLES,
            ('v2f', triangles),
            ('c3B', colors))
        gl.glDisable(gl.GL_BLEND)
        gl.glBlendEquation(gl.GL_FUNC_ADD)

    def _draw_token(self, token):
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        x, y = token.temp_position
        w, h = token.fragment.size

        x0, y0 = self.map_to_screen(x, y)
        screen_w, screen_h = w * self._scale, h * self._scale
        x1, y1 = x0 + screen_w, y0 + screen_h

        clamp_x0 = max(self.pane.x0, x0)
        clamp_y0 = max(self.pane.y0, y0)
        clamp_x1 = min(self.pane.x1, x1)
        clamp_y1 = min(self.pane.y1, y1)

        if clamp_x0 >= clamp_x1 or clamp_y0 >= clamp_y1:
            # Token out of the visible part of the screen.
            return

        image = token.fragment.image
        if clamp_x0 != x0 or clamp_y0 != y0 or clamp_x1 != x1 or clamp_y1 != y1:
            texture_scale = token.fragment.resolution / self._scale
            image = image.get_region(
                (clamp_x0 - x0) * texture_scale,
                (clamp_y0 - y0) * texture_scale,
                (clamp_x1 - clamp_x0) * texture_scale,
                (clamp_y1 - clamp_y0) * texture_scale)

        image.blit(
            clamp_x0, clamp_y0,
            width=(clamp_x1 - clamp_x0), height=(clamp_y1 - clamp_y0))

    def on_draw(self):
        assert self.pane.width > 0
        self._update_pan()
        # Draw non-player tokens
        for token in self.state.current_page.tokens:
            if token.player is None:
                self._draw_token(token)
        self._draw_veils()
        if self._show_grid:
            self._draw_grid()
        # Draw player tokens
        for token in self.state.current_page.tokens:
            if token.player is not None:
                self._draw_token(token)

        return True

    def on_resize(self, *args):
        self.scale_to_fit()

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self.zoom(x, y, 1.1 ** (-scroll_y))

    def on_mouse_press(self, screenx, screeny, button, modifiers):
        if button != mouse.LEFT:
            print('left button not pressed')
            return

        x, y = self.screen_to_map(screenx, screeny)

        if modifiers & key.MOD_ACCEL:
            if self.state.is_master:
                self.state.current_page.toggle_veil(x, y)
            return

        token = self.state.current_page.find_token(x, y)
        if token is not None and token.controlled_by(self.state.player):
            self.state.dragged_token = token
            tx, ty = token.position
            self._dragged_token_offset = (x - tx, y - ty)

    def on_mouse_drag(self, screen_x, screen_y, dx, dy, buttons, modifiers):
        if self.state.dragged_token is None: return
        if not (buttons & mouse.LEFT):
            # left button not pressed
            return
        if not self.pane.contains(screen_x, screen_y):
            # exited the pane
            return

        x, y = self.screen_to_map(screen_x, screen_y)
        ox, oy = self._dragged_token_offset
        tx, ty = x - ox, y - oy

        self.state.dragged_token.set_temp_position(tx, ty)
        return True

    def on_mouse_release(self, x, y, button, modifiers):
        if button == mouse.LEFT and self.state.dragged_token is not None:
            align = modifiers & (key.LSHIFT | key.RSHIFT)
            self.state.dragged_token.position_from_temp(align=align)
            self.state.dragged_token = None



