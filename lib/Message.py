
from lib.Chat import Chat
from lib.User import User

from config import SERVER_URL


class Message:
    SEND_PARAMS = {"roomId", "channel", "text", "alias", "emoji", "avatar", "attachments"}

    def __init__(self, message_id, text, chat, user, attachments, json=None):
        self.id = message_id
        self.text: str = text
        self.chat: 'Chat' = chat
        self.from_user: User = user
        self.attachments = attachments
        self.json = json
        if self.json:
            self.json.update({"text": self.json.get("msg")})

    def get_link(self) -> str:
        return "{}channel/{}?msg={}".format(SERVER_URL, self.chat.id, self.id)

    def json_to_send(self):
        return {k: v for k, v in filter(lambda key_value: key_value[0] in self.SEND_PARAMS, self.json.items())}


