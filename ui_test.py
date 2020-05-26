import pyglet
import time

import ui

window = pyglet.window.Window(resizable=True)

def update(dt): pass
pyglet.clock.schedule_interval(update, 0.001)

focus_manager = ui.FocusManager(window)

layout = ui.StackLayout(ui.Orientation.HORIZONTAL, window)
column1 = ui.StackLayout(
    ui.Orientation.VERTICAL, content_width=200, background=(0, 255, 0))
column1.add_child(ui.Pane(background=(64, 64, 64)))
text1 = ui.TextInput(content_height=200, background=(128, 128, 128))
focus_manager.add_input(text1)
column1.add_child(text1)
text2 = ui.TextInput(content_height=100, background=(160, 160, 160))
focus_manager.add_input(text2)
column1.add_child(text2)
layout.add_child(column1)
layout.add_child(ui.Pane(background=(0, 0, 255)))
layout.add_child(ui.Pane(content_width=100, background=(255, 0, 0)))

pyglet.app.run()
