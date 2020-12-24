#!/usr/bin/env python3
# -*- coding: ascii -*-

"""
A Euphoria bot that watches for the disappearance of a user.
"""

import re, time
import bisect
import threading

import basebot

DEFAULT_TIMEOUT = 604800 # 1 week
WAITER_FUZZ = 1 # 1 second

def match_check(msg, check):
    if check['type'] == 'nick':
        return msg.sender.name == check['nick']
    elif check['type'] == 'nick-regex':
        return bool(check['regex'].search(msg.sender.name))
    elif check['type'] == 'uid':
        return msg.sender.id == check['id']
    else:
        raise RuntimeError('Unrecognized check %r' % (check['type'],))

def do_warning(bot, text):
    if text is None:
        bot.logger.info('Main timeout expired.')
    else:
        bot.send_chat(text)

def waiter(bot):
    sorted_warnings = [(bot.main_timeout, None)]
    sorted_warnings.extend((w['timeout'], w['text']) for w in bot.warnings)
    sorted_warnings.sort()
    timeouts = [w[0] for w in sorted_warnings]
    warning_count = len(sorted_warnings)
    cur_index, last_last_seen = None, None
    with bot.cond:
        while 1:
            if bot.last_seen is None:
                bot.cond.wait()
                continue
            now = time.time() - bot.last_seen
            if bot.last_seen != last_last_seen:
                last_last_seen = bot.last_seen
                cur_index = bisect.bisect_left(timeouts, now - WAITER_FUZZ)
            while cur_index < warning_count and now <= timeouts[cur_index]:
                do_warning(bot, sorted_warnings[cur_index][1])
                cur_index += 1
            if cur_index == warning_count:
                bot.cond.wait()
                continue
            delay = bot.last_seen + timeouts[cur_index] - time.time()
            if delay <= 0:
                continue
            bot.cond.wait(delay)

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
