

from pprint import pprint
from random import choice
from threading import Thread
from time import sleep

import logging

from typing import Callable

from rocketchat_API.rocketchat import RocketChat

from lib.Message import Message
from lib.Chat import Chat
from lib.User import User


class RocketChatBot(object):
    USE_BUTTONS = False
    def __init__(self, botname, passwd, server, command_character=None):
        self.botname = botname
        self.api = RocketChat(user=botname, password=passwd, server_url=server)
        self.commands = [(['echo', ], self.echo)]
        self.auto_answers = []
        self.direct_answers = []
        self.unknown_command = ['command not found', ]
        self.handle_unknown = None
        self.lastts = {}
        self.command_character = command_character

        self.conversations = {}
        self.button_variants = {}

        self.personal_ids: set = set()

    def echo(self, message: Message):
        self.send_message('@' + message.user.username + ' : ' + message.text, message.chat.id)

    def get_status(self, auser):
        return self.api.users_get_presence(username=auser)

    def send_photo(self, chat_id, file, *args, **kwargs):
        self.api.rooms_upload(rid=chat_id, file=file, *args, **kwargs)

    def send_chat_action(self, *args, **kwargs):
        # No such methods in Rocket.Chat
        pass

    def post_new_message(self, obj):
        response = self.api.call_api_post("chat.postMessage", **obj)
        print(response)

    def send_message(self, channel_id, msg, reply_markup=None):
        attachments, msg = self.get_attachments(reply_markup, channel_id, msg)
        # pprint(attachments)
        response = self.api.chat_post_message(channel=channel_id, text=msg, attachments=attachments)
        if response.status_code // 100 > 2:
            logging.error(response.json().get("error", "Error in sending message: {}".format(response.text)))

    def get_attachments(self, reply_markup, user_id, msg):
        if reply_markup is None:
            return None, msg
        if self.USE_BUTTONS:
            return reply_markup.to_json(), msg
        else:
            msg += reply_markup.get_text()
            self.button_variants.update({user_id: reply_markup.get_variants()})
            return None, msg

    def reply_to(self, message: Message, *args, **kwargs):
        return self.send_message(message.chat.id, *args, **kwargs)

    def register_next_step_handler(self, message: Message, f: Callable, *args, **kwargs):
        self.conversations.update({
            message.from_user.id: (f, args, kwargs)
        })

    def get_user(self, username: str):
        return self.api.users_info(username=username)

    def add_dm_handler(self, command, action):
        self.commands.append((command, action))

    def add_auto_answer(self, triggers, answers):
        self.auto_answers.append((triggers, answers))

    def add_direct_answer(self, triggers, answers):
        self.direct_answers.append((triggers, answers))

    def set_unknown_handler(self, action):
        self.handle_unknown = action

    def handle_command_character_message(self, message, channel_id):
        msg = message['msg'].lstrip(self.command_character)

        command = msg.split()[0].lower()
        arguments = " ".join(msg.split()[1:])
        user = message['u']['username']
        attachments = message['attachments']
        pass_message = Message(message_id=message["_id"], text=msg, chat=Chat(chat_id=channel_id),
                               user=User.from_message(message), attachments=attachments, json=message)
        for cmd_list in self.commands:
            if command.lower() in cmd_list[0]:
                cmd_list[1](pass_message)
                return

        if not self.handle_auto_answer(message, self.direct_answers, channel_id):
            self.send_message('@' + user + ' :' + choice(self.unknown_command), channel_id)

    def handle_direct_message(self, message, channel_id):
        msg = message['msg'].partition('@' + self.botname)[2].strip() if message["msg"].startswith('@' + self.botname) \
            else message["msg"].strip()
        if len(msg) > 0:
            command = msg.split()[0].lower()
            # arguments = " ".join(msg.split()[1:])
            user = User.from_message(message)
            attachments = message['attachments']
            pass_message = Message(message_id=message["_id"], text=msg, chat=Chat(chat_id=channel_id), user=user,
                                   attachments=attachments, json=message)

            conversation = self.conversations.get(user.id)
            variants = self.button_variants.get(channel_id)
            pass_message.text = variants.get(pass_message.text, pass_message.text) if variants else pass_message.text
            if conversation is not None:
                # Зарегистрирован следующий шаг
                f, args, kwargs = conversation
                self.conversations.pop(user.id)
                f(pass_message, *args, **kwargs)
            else:
                # Следующий шаг не найден, обработка как обычно
                for cmd_list in self.commands:
                    if command.lower() in cmd_list[0]:
                        cmd_list[1](pass_message)
                        return

                if not self.handle_auto_answer(message, self.direct_answers, channel_id):
                    if self.handle_unknown is not None:
                        self.handle_unknown(pass_message)
                    else:
                        self.send_message('@' + user.username + ' :' + choice(self.unknown_command), channel_id)
        else:
            user = User.from_message(message)
            attachments = message['attachments']
            pass_message = Message(message_id=message["_id"], text=msg, chat=Chat(chat_id=channel_id), user=user,
                                   attachments=attachments, json=message)
            self.handle_unknown(pass_message)

    def handle_auto_answer(self, message, answers, channel_id):
        for kind in answers:
            for k in kind[0]:
                if k in message['msg'].lower():
                    self.send_message(choice(kind[1]) + ' @' + message['u']['username'], channel_id)
                    return True
        return False

    def handle_messages(self, messages, channel_id):
        for message in messages['messages']:
            if message['u']['username'] != self.botname:
                pprint(message)
                pprint(channel_id)
                if message['u']['username'] == 'rocket.cat':
                    pass
                    # continue
                Thread(target=self.handle_direct_message, args=(message, channel_id)).start()
                # if message['msg'].startswith('@' + self.botname) or channel_id in self.personal_ids:
                #     Thread(target=self.handle_direct_message, args=(message, channel_id)).start()
                # elif self.command_character is not None and message['msg'].startswith(self.command_character):
                #     Thread(target=self.handle_command_character_message, args=(message, channel_id)).start()
                # elif 'mentions' not in message or message.get('mentions') == []:
                #     Thread(target=self.handle_auto_answer, args=(message, self.auto_answers, channel_id)).start()

    def load_ts(self, channel_id, messages):
        if len(messages) > 0:
            self.lastts[channel_id] = messages[0]['ts']
        else:
            self.lastts[channel_id] = ''

    def load_channel_ts(self, channel_id):
        self.load_ts(channel_id, self.api.channels_history(channel_id).json()['messages'])

    def load_group_ts(self, channel_id):
        self.load_ts(channel_id, self.api.groups_history(channel_id).json()['messages'])

    def load_im_ts(self, channel_id):
        response = self.api.im_history(channel_id).json()
        if response.get('success'):
            self.load_ts(channel_id, self.api.im_history(channel_id).json()['messages'])

    def process_messages(self, messages, channel_id):
        try:
            if "success" in messages:
                if messages['success'] == False:
                    raise RuntimeError(messages['error'])
            if len(messages['messages']) > 0:
                self.lastts[channel_id] = messages['messages'][0]['ts']
            self.handle_messages(messages, channel_id)
        except Exception as e:
            pprint(e)

    def process_channel(self, channel_id):
        if channel_id not in self.lastts:
            self.lastts[channel_id] = ''

        self.process_messages(self.api.channels_history(channel_id, oldest=self.lastts[channel_id]).json(),
                              channel_id)

    def process_group(self, channel_id):
        if channel_id not in self.lastts:
            self.lastts[channel_id] = ''

        self.process_messages(self.api.groups_history(channel_id, oldest=self.lastts[channel_id]).json(),
                              channel_id)

    def process_im(self, channel_id):
        if channel_id not in self.lastts:
            self.lastts[channel_id] = ''

        self.process_messages(self.api.im_history(channel_id, oldest=self.lastts[channel_id]).json(),
                              channel_id)

    def run(self):
        for channel in self.api.channels_list_joined().json().get('channels'):
            self.load_channel_ts(channel.get('_id'))

        for group in self.api.groups_list().json().get('groups'):
            self.load_group_ts(group.get('_id'))

        for im in self.api.im_list().json().get('ims'):
            self.load_im_ts(im.get('_id'))

        while 1:
            for channel in self.api.channels_list_joined().json().get('channels'):
                Thread(target=self.process_channel, args=(channel.get('_id'),)).start()

            for group in self.api.groups_list().json().get('groups'):
                Thread(target=self.process_group, args=(group.get('_id'),)).start()

            for im in self.api.im_list().json().get('ims'):
                if self.botname in im.get("usernames"):
                    self.personal_ids.add(im.get('_id'))
                Thread(target=self.process_im, args=(im.get('_id'),)).start()

            sleep(1)