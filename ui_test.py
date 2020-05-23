import pyglet
import time

import ui

window = pyglet.window.Window(resizable=True)

def update(dt): pass
pyglet.clock.schedule_interval(update, 0.001)

pane1 = ui.Pane(content_width=200, background=(0, 255, 0))
pane2 = ui.Pane(background=(0, 0, 255))
pane3 = ui.Pane(content_width=100, background=(255, 0, 0))
layout = ui.StackLayout(ui.Orientation.HORIZONTAL, window, (pane1, pane2, pane3))

def on_mouse_press1(x, y, button, modifiers):
    print('on_mouse_press1', x, y, button, modifiers)
pane1.push_handlers(on_mouse_press=on_mouse_press1)

def on_mouse_press2(x, y, button, modifiers):
    print('on_mouse_press2', x, y, button, modifiers)
pane2.push_handlers(on_mouse_press=on_mouse_press2)

def on_mouse_press3(x, y, button, modifiers):
    print('on_mouse_press3', x, y, button, modifiers)
pane3.push_handlers(on_mouse_press=on_mouse_press3)


pyglet.app.run()
