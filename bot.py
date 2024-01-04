import slack
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, Response, request
from slackeventsapi import SlackEventAdapter
from datetime import datetime, timedelta

message_counts = {}
welcome_messages = {}

SCHEDULED_MESSAGES = [
    {'channel': 'C06C5GG28LE', 'post_at': int((datetime.now() + timedelta(seconds=30)).timestamp()), 'text': 'Scheduled Message'}
]

SCHEDULED_MESSAGE_IDS = []

class WelcomeMessage:
    START_TEXT = {
        'type': 'section',
        'text' : {
            'type': 'mrkdwn',
            'text': (
                'Welcome to the channel \n\n'
                '*Get started by completing the tasks*'
                )
        }
    }

    DIVIDER = {
        'type': 'divider'
    }

    def __init__(self, channel, user):
        self.channel = channel
        self.user = user
        self.timestamp =  ''
        self.completed = False

    def get_message(self):
        return {
            'ts': self.timestamp,
            'channel': self.channel,
            'blocks': [
                self.START_TEXT,
                self.DIVIDER,
                self._get_reaction_task()
            ]
        }
    
    def _get_reaction_task(self):
        checkmark = ':white_check_mark:'
        if not self.completed:
            checkmark = ':white_large_square:'

        text = f'{checkmark} *React to this message'

        return {'type': 'section', 'text': {'type': 'mrkdwn', 'text': text}}

def send_welcome_message(channel, user):
    if channel not in welcome_messages:
        welcome_messages[channel] = {}

    if user in welcome_messages[channel]:
        return

    welcome = WelcomeMessage(channel, user)
    message = welcome.get_message()
    response = client.chat_postMessage(**message)
    welcome.timestamp = response['ts']
    
    welcome_messages[channel][user] = welcome

def schedule_messages(messages):
    
    for message in messages:
        response = client.chat_scheduleMessage(**message)
        id = response.get('scheduled_message_id')
        SCHEDULED_MESSAGE_IDS.append(id)

def delete_scheduled_messages(ids, channel):
    for id in ids:
        client.chat_deleteScheduledMessage(channel=channel, scheduled_message_id=id)

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
slack_events_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], '/slack/events', app)

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])
BOT_ID = client.api_call("auth.test")["user_id"]

# client.chat_postMessage(channel='#testing-bot', text="I Live!")

@slack_events_adapter.on('reaction_added')
def reaction_added(payload):
    event = payload.get('event', {})
    channel_id = event.get('item', {}).get('channel')
    user_id = event.get('user')

    if f'@{user_id}' not in welcome_messages:
        return

    welcome = welcome_messages[f'@{user_id}'][user_id]
    welcome.completed = True
    # blegh the reference of dm channel id is weird so hard coding it here
    welcome.channel = channel_id
    message = welcome.get_message()
    updated_message = client.chat_update(channel=message['channel'], post_at=message['post_at'], text=message['text'])
    welcome.timestamp = updated_message['ts']

@slack_events_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')

    if user_id != None and user_id != BOT_ID:
        if user_id in message_counts:
            message_counts[user_id] += 1
        else:
            message_counts[user_id] = 1

        if text.lower() == 'start':
            send_welcome_message(f'@{user_id}', user_id)
        elif text.lower() == 'reply':
            ts = event.get('ts')
            client.chat_postMessage(channel=channel_id, thread_ts=ts, text="Replying in thread")
        elif text.lower() == 'schedule':
            schedule_messages(SCHEDULED_MESSAGES)
        elif text.lower() == 'delete':
            delete_scheduled_messages(SCHEDULED_MESSAGE_IDS, channel_id)

@app.route('/message-count', methods=['POST'])
def message_count():
    data = request.form
    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    message_count = message_counts.get(user_id, 0)

    client.chat_postMessage(channel=channel_id, text=f"Messges: {message_count}")
    return Response(), 200

if __name__ == '__main__':

    app.run(debug=True)
    print(SCHEDULED_MESSAGES)