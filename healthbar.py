import pyglet
from pyglet import gl

import ui

RED = (0xb7, 0x1c, 0x1c)
GREEN = (0x1b, 0x5e, 0x20)


class HealthBarImpl(ui.View):
    def __init__(self, get_char, padding=8, **kwargs):
        self._get_char = get_char
        self._padding = padding
        self._colors = GREEN * 6 + RED * 6
        super().__init__(**kwargs)

    def on_draw(self):
        char = self._get_char()
        if char is None:
            return
        width = self.pane.width - 2 * self._padding
        green_width = width * char.hp / char.maxhp
        x0 = self.pane.x0 + self._padding
        x1 = x0 + green_width
        x2 = self.pane.x1 - self._padding
        triangles = [
            x0, self.pane.y0, x1, self.pane.y0, x1, self.pane.y1,
            x0, self.pane.y0, x1, self.pane.y1, x0, self.pane.y1,
            x1, self.pane.y0, x2, self.pane.y0, x2, self.pane.y1,
            x1, self.pane.y0, x2, self.pane.y1, x1, self.pane.y1
        ]  # yapf: disable
        pyglet.graphics.draw(12, gl.GL_TRIANGLES, ('v2f', triangles),
                             ('c3B', self._colors))


class HealthText(ui.Text):
    def __init__(self, get_char, font_size=20, valign='center', align='center',
                 **kwargs):
        self.get_char = get_char
        super().__init__(get_text=self.health_text, font_size=font_size,
                         valign=valign, align=align, multiline=True, **kwargs)

    def health_text(self):
        char = self.get_char()
        if char is None: return '0 / 0'
        return '{} / {}'.format(char.hp, char.maxhp)

    def on_draw(self):
        super().on_draw()


class HealthBar(ui.VStackLayout):
    def __init__(self, get_char, padding=8, **kwargs):
        super().__init__(
            ui.Text(text='HIT POINTS', font_size=8, kerning=2, min_height=14,
                    align='center', color=(255, 255, 255, 255), padding=0,
                    multiline=True, flex_height=False),
            ui.LayersLayout(
                HealthBarImpl(get_char, padding=padding,
                              min_height=30, flex_height=False),
                HealthText(get_char)), min_height=50, flex_height=False,
            **kwargs)
