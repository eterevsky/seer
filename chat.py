import campaign
import ui


class ChatText(ui.Text):
    def __init__(self, c: campaign.Campaign):
        super().__init__(content_height=None, background=(64, 64, 64))
        self.campaign = c
        self.campaign.push_handlers(self.on_new_chat)

    def on_new_chat(self, message):
        if message['player'] is None:
            player = 'GM'
        else:
            player = message['player']
        self.document.text += '{}: {}\n'.format(player, message['text'])


class ChatInput(ui.TextInput):
    def __init__(self, c: campaign.Campaign, api_server,
                 focus_manager: ui.FocusManager):
        super().__init__(focus_manager=focus_manager,
                         content_height=200, background=(128, 128, 128))
        self.campaign = c
        self.api_server = api_server

    def on_return(self):
        message = {
            'player': self.campaign.player,
            'text': self.document.text.strip(),
        }
        self.document.text = ''

        if self.campaign.is_master:
            self.campaign.add_chat(message)
        else:
            notification = {
                'method': 'player_chat',
                'params': {'message': message}
            }
            print('*sending chat')
            self.api_server.notify(notification)