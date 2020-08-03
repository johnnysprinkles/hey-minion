import asyncio
from bs4 import BeautifulSoup
import getpass
import json
import os
import requests
import socket
import sys
import websockets

if sys.version_info < (3, 7):
    print('This script requires Python 3.7 or greater') or sys.exit()

from hey import HeySession

COOKIE_FILE = '~/heyminion-cookies.json'
COOKIE_FILE_EXPANDED = os.path.expanduser(COOKIE_FILE) # expands the tilde
PUSHOVER_FILE = '~/heyminion-pushover.json'
PUSHOVER_FILE_EXPANDED = os.path.expanduser(PUSHOVER_FILE)

def confirm(message):
    while True:
        text = input(message).lower() or 'y'
        if text[0] in ('y', 'n'):
            return text[0] == 'y'

def interactive_hey_setup():
    if os.path.exists(COOKIE_FILE_EXPANDED):
        if confirm(f'Found {COOKIE_FILE}, would you like to use that? [Y/n]: '):
            with open(COOKIE_FILE_EXPANDED) as f:
                hey.apply_cookies(json.loads(f.read()))
            if hey.get('/').url == 'https://app.hey.com/':
                print('Saved hey.com credentials worked successfully.')
                return

    email = input('HEY.com email address (@hey.com is optional): ')
    if not '@' in email:
        email += '@hey.com'
    password = getpass.getpass('Password: ')

    # GET request here sets some session cookies
    hey.get('/sign_in')
    response = hey.sign_in(email, password)

    while response.url != 'https://app.hey.com/':
        if 'sign_in' in response.url:
            password = getpass.getpass('Wrong password, try again: ')
            response = hey.sign_in(email, password)
        elif 'two_factor' in response.url:
            # Grab CSRF token from the page. Can't use kwargs for
            # "name" attribute because name is a special identifer for
            # "tagName".
            soup = BeautifulSoup(response.content, 'html.parser')
            csrf = soup.find('meta', {'name': 'csrf-token'})['content']
            code = input('Two factor authentication code: ')
            response = hey.respond_to_challenge(code, csrf)
        else:
            print(f'Redirected to unexpected location: {response.url}')
            sys.exit()

    print('Successfully authenticated with app.hey.com!')

    if confirm(f'Would you like to save your session cookies in {COOKIE_FILE}? [Y/n]: '):
        with open (COOKIE_FILE_EXPANDED, 'w') as f:
            f.write(json.dumps(hey.get_cookies()))
        print(f'Wrote new {COOKIE_FILE} file.')

def interactive_pushover_setup():
    if os.path.exists(PUSHOVER_FILE_EXPANDED):
        if confirm(f'Found {PUSHOVER_FILE}, would you like to use that? [Y/n]: '):
            with open(PUSHOVER_FILE_EXPANDED) as f:
                pushover_credentials = json.loads(f.read())
                r = requests.post('https://api.pushover.net/1/users/validate.json',
                    data=pushover_credentials)
                if r.status_code == 200:
                    print('Pushover credentials worked successfully.')
                    return pushover_credentials

    pushover_credentials = {
        'user': input('Pushover User Key: '),
        'token': input('Pushover Application Key: ')
    }

    response = requests.post('https://api.pushover.net/1/users/validate.json',
        data=pushover_credentials)

    while response.status_code != 200:
        print('Bad credentials, try again')
        pushover_credentials = {
            'user': input('Pushover User Key: '),
            'token': input('Pushover Application Key: ')
        }
        response = requests.post('https://api.pushover.net/1/users/validate.json',
            data=pushover_credentials)

    print('Successfully authenticated with the Pushover API!')

    if confirm(f'Would you like to save your Pushover credentials in {PUSHOVER_FILE}? [Y/n]: '):
        with open (PUSHOVER_FILE_EXPANDED, 'w') as f:
            f.write(json.dumps(pushover_credentials))
        print(f'Wrote new {PUSHOVER_FILE} file.')

    return pushover_credentials

def process(msg):
    if 'message' in msg:
        fragment = BeautifulSoup(msg['message'], 'html.parser')
        if fragment.find(id='clearances_button'):
            # New person to be screened
            latest_unscreened = hey.get_unscreened_senders()
            n = len(latest_unscreened)
            new_unscreened = latest_unscreened - unscreened
            unscreened.clear()
            unscreened.update(latest_unscreened)
            if new_unscreened:
                sender = list(new_unscreened)[0]
                data = {
                    'title': f'{n} sender{"s" * (n != 1)} to be screened',
                    'message': sender,
                }
                data.update(pushover_credentials)
                print(data)
                response = requests.post("https://api.pushover.net/1/messages.json", data=data)

async def listen_on_hey_websocket_forever():
    headers = {
        'User-Agent': HeySession.USER_AGENT,
        'Origin': HeySession.ORIGIN,
        'Cookie': hey.get_cookie()
    }
    retry_delay = 0.1 # seconds
    channels = hey.get_channels()

    while True:
        try:
            async with websockets.connect(HeySession.WEB_SOCKET_URL, extra_headers=headers) as ws:
                print(f'Connected to {HeySession.WEB_SOCKET_URL}')
                retry_delay = 0
                for channel in channels:
                    msg = {
                        'command': 'subscribe',
                        'identifier': channel,
                    }
                    print(f'Subscribing to channel {channel}')
                    await ws.send(json.dumps(msg))
                # Forever loop, or at least until whatever basecamp machine we're connected to is
                # bounced for a deployment.
                print('Waiting for messages...')
                async for message in ws:
                    message = json.loads(message)
                    if message.get('type') != 'ping':
                        process(message)
        except (websockets.exceptions.ConnectionClosed, socket.gaierror):
            # Server closed the socket, or general network problem
            await asyncio.sleep(retry_delay)
            retry_delay *= 2

if __name__ == '__main__':
    hey = HeySession()
    interactive_hey_setup()
    pushover_credentials = interactive_pushover_setup()
    unscreened = hey.get_unscreened_senders()
    asyncio.run(listen_on_hey_websocket_forever())
