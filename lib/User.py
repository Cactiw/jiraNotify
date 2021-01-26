
class User:
    def __init__(self, user_id, name, username):
        self.id: str = user_id
        self.name: str = name
        self.username: str = username

    @classmethod
    def from_message(cls, msg: dict) -> 'User':
        return User(msg['u']['_id'], msg['u']['name'], msg['u']['username'])