from pyglet import gl

from .view import View

class Image(View):
    def __init__(self, image=None, get_image=None, **kwargs):
        super().__init__(**kwargs)
        self.image = image
        self.get_image = get_image

    def on_draw(self):
        if self.get_image is not None:
            self.image = self.get_image()
        if self.image is not None:
            gl.glEnable(gl.GL_BLEND)
            gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
            self.image.blit(self.pane.x0, self.pane.y0, width=self.pane.width,
                            height=self.pane.height)


