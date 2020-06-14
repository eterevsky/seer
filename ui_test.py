import pyglet
import time

import ui

window = pyglet.window.Window(resizable=True)

def update(dt): pass
pyglet.clock.schedule_interval(update, 1)

focus_manager = ui.FocusManager(window)

# layout = ui.RootLayout(window, ui.HStackLayout(
#     ui.Spacer().set_min_width(200).set_flex_width(False).set_background((127, 0, 0)),
#     ui.Spacer(background=(127, 127, 127)),
#     ui.Spacer(background=(0, 0, 127))
# ))

layout = ui.RootLayout(window, ui.HStackLayout(
    ui.VStackLayout(
        ui.Spacer(min_height=100, flex_height=False, background=(0, 0, 0)),
        ui.Spacer(background=(0, 127, 0)),
        ui.Spacer(background=(0, 0, 127))
    ).set_min_width(200).set_flex_width(False),
    ui.VStackLayout(
        ui.Spacer(min_width=200, min_height=200, flex_width=False,
                  flex_height=False, background=(127, 127, 127))
    ),
    ui.VStackLayout(
        ui.Spacer(background=(127, 127, 0)),
        ui.Spacer(min_height=200, flex_height=False, background=(0, 127, 127))
    )
))

print(layout)

pyglet.app.run()
