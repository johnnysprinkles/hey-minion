# Hey Minion

Python script to connect to app.hey.com and watch for events, then send out notifications to the
Pushover mobile app for iOS and Android.

https://hey.com/  
https://pushover.net/

Currently only offering these notifications:

* New contact to be screened

Imbox notifications were added natively on https://app.hey.com/my/notification_bells so not touching
that. Might consider adding Feed notifications just because the landing page of https://app.hey.com
doesn't give any hint at how much is new in the feed. Paper Trail, Screened Out, Spam, etc won't
ever need notifications.

---

## Getting started

Set up a Pushover account at https://pushover.net/ and create a new Application.

With Python 3.7 or greater, do:

    pip install -r requirements.txt
    python src/main.py

Then answer the provided prompts. You could run it on your local machine if it stays awake all the
time, or put it up on an EC2 instance perhaps running in a tmux session.
