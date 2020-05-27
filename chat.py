import campaign
import ui


class ChatText(ui.Text):
    def __init__(self, c: campaign.Campaign, ):
        super().__init__(content_height=None, background=(64, 64, 64))
        self.campaign = c
        self.campaign.push_handlers(self.on_new_chat)

    def on_new_chat(self, message):
        if message['player'] is None:
            player = 'GM'
        else:
            player = message['player']
        self.document.text +=  '{}: {}\n'.format(player, message['text'])


class ChatInput(ui.TextInput):
    def __init__(self, c: campaign.Campaign):
        super().__init__(content_height=200, background=(128, 128, 128))
        self.campaign = c

    def on_return(self):
        if self.campaign.is_master:
            self.campaign.add_chat(self.document.text)
            self.document.text = ''
