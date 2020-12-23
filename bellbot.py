#!/usr/bin/env python3
# -*- coding: ascii -*-

"""
A Euphoria bot that watches for the disappearance of a user.
"""

import re, time
import threading

import basebot

DEFAULT_TIMEOUT = 604800 # 1 week

def match_check(msg, check):
    if check['type'] == 'nick':
        return msg.sender.name == check['nick']
    elif check['type'] == 'nick-regex':
        return bool(check['regex'].search(msg.sender.name))
    elif check['type'] == 'uid':
        return msg.sender.id == check['id']
    else:
        raise RuntimeError('Unrecognized check %r' % (check['type'],))

def waiter(bot):
    sorted_warnings = [(bot.main_timeout, None)]
    sorted_warnings.extend((w['timeout'], w['text']) for w in bot.warnings)
    sorted_warnings.sort()
    with bot.cond:
        while 1:
            bot.cond.wait()

class BellBot(basebot.BaseBot):
    BOTNAME = 'BellBot'
    NICKNAME = ':bell::bot:'

    def __init__(self, *args, **kwds):
        basebot.BaseBot.__init__(self, *args, **kwds)
        self.cond = threading.Condition()
        self.checks = kwds.get('checks', ())
        self.main_timeout = kwds.get('main_timeout', DEFAULT_TIMEOUT)
        self.warnings = kwds.get('warnings', ())
        self._max_timeout = max([self.main_timeout] +
                                [w['timeout'] for w in self.warnings])
        self.last_seen = None

    def _process_post(self, msg):
        if not any(match_check(msg, check) for check in self.checks): return
        if self.last_seen is not None and self.last_seen >= msg.time: return
        self.last_seen = msg.time
        self.cond.notifyAll()

    def handle_chat(self, msg, meta):
        with self.cond:
            self._process_post(msg)

    def handle_logs(self, msglist, meta):
        if not msglist:
            self.logger.info('Reached end of room logs; giving up search.')
            return
        with self.cond:
            oldest, oldest_id = None, None
            for msg in msglist:
                if oldest is None or msg.time < oldest:
                    oldest = msg.time
                    oldest_id = msg.id
                self._process_post(msg)
            if self.last_seen is not None:
                self.logger.info('Quarry located; log search done.')
                return
            if oldest + self._max_timeout < time.time():
                self.logger.info('Quarry not located within max timeout; '
                    'giving up.')
                return
            self.logger.info('Quarry not located up to %s; '
                'looking further...' % basebot.format_datetime(oldest))
            self.send_packet('log', n=1000, before=oldest_id)

    def main(self):
        basebot.spawn_thread(waiter, self)
        basebot.BaseBot.main(self)

def main():
    basebot.run_main(BellBot)

if __name__ == '__main__': main()
