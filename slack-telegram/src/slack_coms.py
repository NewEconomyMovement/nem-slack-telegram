'''
Created on 26.09.2015

@author: root
'''
import time
import json
import re
from slackclient import SlackClient

CHANNEL_MATCHING = {'NEM::Red': 'nem_red',
                    'NEM::Tech': 'nem_tech'}

EMO_MATCHING = {':stuck_out_tongue:': ':P',
                ':smile:': ':D',
                ':simple_smile:': ':)',}


def resolve_user(bot, uid):
    user = json.loads(bot.api_call('users.info',
                                     user=uid))
    return user['user']


def replace_emos(text):
    for i, j in EMO_MATCHING.iteritems():
        text = text.replace(i, j)
    return text


def prep_message(bot, update):
    try:
        #resolve mentionings
        user = resolve_user(bot, update['user'])
        marked_users = set([m.group(1) for m in
                                        re.finditer('<@([A-Z0-9]+)>',
                                                    update['text'])])
        for marked_user in marked_users:
            username = resolve_user(bot, marked_user)['name']
            update['text'] = update['text'].replace(marked_user,
                                                    username)
        update['user'] = user
        update['text'] = replace_emos(update['text'])
    except:
        pass  # fuck anything
    return update


def listen_to_slack(token, queue):
    '''
    Queries Slack for Updates and puts them into a queue.
    '''
    slack = SlackClient(token)
    if slack.rtm_connect():
        print 'Listening to Slack'
        while True:
            try:
                updates = slack.rtm_read()
                for update in updates:
                    print 'Received from slack', update
                    if update.get('subtype') == 'bot_message':
                        #msg from a bot - move on
                        continue
                    if not update.get('text'):
                        #no text = move on
                        continue
                    else:
                        update = prep_message(slack, update)
                        queue.put(update)
                    time.sleep(1)
            except Exception, e:
                print 'Something went wrong - listening to Slack'  # fuck it so it won't crash ever
                print str(e)
                time.sleep(5)
    else:
        print 'Failed to establish a connection to Slack!'


def forward_to_slack(token, queue):
    '''
    Takes a message from a queue and posts it to slack.
    Messages are expected to be objects as returned from the
    Telegram API.
    '''
    slack = SlackClient(token)
    print 'Ready to forward to Slack'
    while True:
        try:
            update = queue.get()
            try:
                channel = CHANNEL_MATCHING[update.message.chat.title]
            except KeyError:
                print 'Got Message from unknown channel: %s ' % update.message.chat.title
            message = update.message.text.encode('utf-8')

            #resolve quotes
            if update.message.reply_to_message:
                reply_to_message = update.message.reply_to_message.text.encode('utf-8')
                reply_to_message = reply_to_message.replace('\n', '\n>')
                message = '>%s:\n>%s\n%s' % (update.message.reply_to_message.from_user.username,
                                           reply_to_message,
                                           message)

            slack.api_call('chat.postMessage',
                            channel=channel,
                            text=message,
                            username=update.message.from_user.username,
                            icon_url=update.message.from_user.avatar)
        except Exception, e:
            print 'Something went wrong - forwarding to Slack'  # fuck it so it won't crash ever
            print str(e)
            time.sleep(5)


def post_to_slack(token, message, user, channel):
    '''
    Another method to post to slack. Made id seperate so
    diagnostics will go through even if thread dies
    '''
    slack = SlackClient(token)
    slack.api_call('chat.postMessage',
                    channel=channel,
                    text=message,
                    username=user)
