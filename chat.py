import campaign
import state
import ui


class ChatText(ui.Text):
    def __init__(self, c: campaign.Campaign, **kwargs):
        super().__init__(**kwargs)
        self.campaign = c
        self.campaign.push_handlers(self.on_new_chat)

    def on_new_chat(self, message):
        if message['player'] is None:
            player = 'GM'
        else:
            player = message['player']
        self.document.text += '{}: {}\n'.format(player, message['text'])


class ChatInput(ui.TextInput):
    def __init__(self, s: state.State, api_server,
                 focus_manager: ui.FocusManager, **kwargs):
        super().__init__(focus_manager=focus_manager, **kwargs)
        self.state = s
        self.api_server = api_server

    def on_return(self):
        message = {
            'player': self.state.player,
            'text': self.document.text.strip(),
        }
        self.document.text = ''

        if self.state.is_master:
            self.state.campaign.add_chat(message)
        else:
            notification = {
                'method': 'player_chat',
                'params': {'message': message}
            }
            print('*sending chat')
            self.api_server.notify(notification)