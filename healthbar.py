import pyglet
from pyglet import gl

import colors
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
    def __init__(self, get_char, is_editing, font_size=20, valign='center',
                 align='center',
                 **kwargs):
        self.get_char = get_char
        self.is_editing = is_editing
        super().__init__(get_text=self.health_text, font_size=font_size,
                         valign=valign, align=align, multiline=False,
                         flex_width=False, **kwargs)

    def health_text(self):
        if self.is_editing():
            return '/'
        char = self.get_char()
        if char is None: return '0 / 0'
        return '{} / {}'.format(char.hp, char.maxhp)

    def on_draw(self):
        super().on_draw()


class HealthBar(ui.VStackLayout):
    def __init__(self, focus_manager, get_char, padding=8, **kwargs):
        self._editing = False
        self.hp_input = ui.TextInput(focus_manager, min_width=40, font_size=20, flex_width=0,
                                form_background=colors.GREY_900,
                                get_hidden=self.is_not_editing)
        self.maxhp_input = ui.TextInput(focus_manager, min_width=40, font_size=20, flex_width=0,
                                 form_background=colors.GREY_900,
                                 get_hidden=self.is_not_editing)
        self.health_text = HealthText(get_char, is_editing=self.is_editing)
        self.text_hstack = ui.HStackLayout(
                    ui.Spacer(),
                    self.hp_input,
                    self.health_text,
                    self.maxhp_input,
                    ui.Spacer()
                )
        super().__init__(
            ui.Text(text='HIT POINTS', font_size=8, kerning=2, min_height=14,
                    align='center', color=(255, 255, 255, 255), padding=0,
                    multiline=True, flex_height=False),
            ui.LayersLayout(
                HealthBarImpl(get_char, padding=padding,
                              min_height=30, flex_height=False),
                self.text_hstack
            ), min_height=50, flex_height=False, **kwargs)

    def on_mouse_press(self, *args):
        self._editing = True
        print(self.hp_input.min_width)
        self.hp_input._update_dims()
        self.maxhp_input._update_dims()
        self.health_text.set_content_width()
        self.hp_input.focus()
        # self.text_hstack._resize(debug=True)

    def is_editing(self):
        return self._editing

    def is_not_editing(self):
        return not self._editing
