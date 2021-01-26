
from api import RocketChatBot
from lib.Message import Message

import re

from config import BOTNAME, PASSWORD, SERVER_URL

bot = RocketChatBot(BOTNAME, PASSWORD, SERVER_URL)


def search_mentions(message):
    if "jira" in message.json.get("alias").lower():
        for attachment in message.attachments:
            mentions = re.findall("\\[~(\\w+)]", attachment.get("text"))
            print(mentions)
            if mentions:
                for mention in mentions:
                    user_response = bot.get_user(username=mention)
                    if user_response.status_code // 100 == 2:
                        user_id = user_response.json().get("user").get("_id")
                        to_send = message.json_to_send()
                        to_send.update({"roomId": user_id})
                        bot.post_new_message(to_send)


if __name__ == "__main__":
    bot.set_unknown_handler(search_mentions)
    user_response = bot.get_user(username="ratnikovin")

    print("Starting Rocket.Chat bot")
    bot.run()
