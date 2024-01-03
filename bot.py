import slack
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from slackeventsapi import SlackEventAdapter

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
slack_events_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], '/slack/events', app)

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])
print(client.api_call("auth.test"))
BOT_ID = client.api_call("auth.test")["user_id"]

# client.chat_postMessage(channel='#testing-bot', text="I Live!")

@slack_events_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')

    if user_id != BOT_ID:
        client.chat_postMessage(channel=channel_id, text=text)

if __name__ == '__main__':

    app.run(debug=True)