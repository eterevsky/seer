import pyglet

from ui.view import View

class TextInput(View):
    def __init__(self, focus_manager, text_color=(192, 192, 192, 255),
                 form_background=None, font_size=None,
                 multiline=True, **kwargs):
        super().__init__(**kwargs)
        self.document = pyglet.text.document.UnformattedDocument('')
        self.document.set_style(0, 0, {
            'color': text_color,
            'font_size': font_size
        })
        self.layout = None
        self.caret = None
        self.multiline = multiline
        self.focus_manager = focus_manager
        self.text_color = text_color
        self.form_background = form_background

    def focus(self):
        self.focus_manager.focus(self)

    def attach(self, pane):
        # TODO: Override detach.
        super().attach(pane)
        self.layout = pyglet.text.layout.IncrementalTextLayout(
            self.document, pane.width - 10, pane.height - 10,
            multiline=self.multiline,
            wrap_lines=self.multiline)
        self.layout.x = pane.x0 + 5
        self.layout.y = pane.y0 + 5
        self.caret = pyglet.text.caret.Caret(self.layout,
                                             color=self.text_color[:3])
        self.caret.visible = False
        self.focus_manager.add_input(self)

    def on_mouse_enter(self, *args):
        self.pane.window.set_mouse_cursor(
            self.pane.window.get_system_mouse_cursor(
                pyglet.window.Window.CURSOR_TEXT))

    def on_resize(self, width, height, offset_x, offset_y):
        if width <= 0 or height <= 0:
            self.caret.visible = False
            return
        self.layout.width = width - 10
        self.layout.height = height - 10
        self.layout.x = offset_x + 5
        self.layout.y = offset_y + 5

    def on_draw(self):
        x0 = self.pane.x0 + 2.5
        y0 = self.pane.y0 + 2.5
        x1 = self.pane.x1 - 2.5
        y1 = self.pane.y1 - 2.5
        if self.form_background is not None:
            triangles = [
                x0, y0, x1, y0, x1, y1,
                x0, y0, x1, y1, x0, y1
            ]  # yapf: disable
            c = self.form_background * 6

            pyglet.graphics.draw(6, pyglet.gl.GL_TRIANGLES,
                                ('v2f', triangles), ('c3B', c))

        lines = [
            x0, y0, x1, y0,
            x1, y1, x0, y1
        ]  # yapf: disable
        if self.pane.mouseover:
            colors = [192, 192, 192] * (len(lines) // 2)
        else:
            colors = [128, 128, 128] * (len(lines) // 2)

        pyglet.gl.glLineWidth(1)
        pyglet.graphics.draw(
            len(lines) // 2, pyglet.gl.GL_LINE_LOOP, ('v2f', lines),
            ('c3B', colors))

        self.layout.draw()

    def on_return(self):
        # Has to be overriden by the class to handle the input text.
        pass


class Text(View):
    def __init__(self, text='', get_text=None, color=(255, 255, 255, 255),
                 font_size=None, valign='top', kerning=0, align='left',
                 padding=5, multiline=False, **kwargs):
        super().__init__(**kwargs)
        self.document = pyglet.text.document.UnformattedDocument(text)
        self._style = {
            'color': color,
            'font_size': font_size,
            'kerning': kerning,
            'align': align
        }
        self.document.set_style(0, 0, self._style)
        self.layout = None
        self.multiline = multiline
        self.padding = padding
        self.get_text = get_text
        self.document.text = text
        self.valign = valign

    def _create_layout(self, width, height, offset_x, offset_y):
        width -= 2 * self.padding
        if width <= 0: width = None
        self.layout = pyglet.text.layout.TextLayout(
            self.document, width, height - 2 * self.padding,
            multiline=self.multiline, wrap_lines=self.multiline)
        self.layout.content_valign = self.valign
        self.layout.x = offset_x + self.padding
        self.layout.y = offset_y + self.padding
        if not self.min_width_set() and not self.multiline:
            self.set_min_width(self.layout.content_width + 2 * self.padding)

    def attach(self, pane):
        super().attach(pane)
        if pane.width > 0 or not self.multiline:
            self._create_layout(pane.width, pane.height, pane.x0, pane.y0)

    def on_resize(self, width, height, offset_x, offset_y):
        if self.layout is None:
            self._create_layout(width, height, offset_x, offset_y)
            return
        self.layout.width = width - 2 * self.padding
        self.layout.height = height - 2 * self.padding
        self.layout.x = offset_x + self.padding
        self.layout.y = offset_y + self.padding

    def on_draw(self):
        assert self.layout is not None
        if self.get_text is not None:
            self.document.text = self.get_text()
        self.layout.draw()

    def set_content_width(self):
        print('document.text', self.document.text)
        print('self.layout.content_width', self.layout.content_width)
        self.layout.begin_update()
        if self.get_text is not None:
            self.document.text = self.get_text()
        self.layout.end_update()
        self.layout._update()
        print('document.text', self.document.text)
        print('self.layout.content_width', self.layout.content_width)
        self.set_min_width(self.layout.content_width)
