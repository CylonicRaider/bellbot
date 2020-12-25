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
DEFAULT_WARNING = '/me *Dong*...'
WAITER_FUZZ = 1 # 1 second

TIME_TOKEN_RE = re.compile(r'\s*([0-9]+(\.[0-9]+)?)([wdhms])\s*')
TIME_TOKEN_VALUES = {'w': 604800, 'd': 86400, 'h': 3600, 'm': 60, 's': 1}

def parse_duration(s):
    if not s:
        raise ValueError('Invalid empty duration (use something like "0s" '
                         'instead)')
    index, total = 0, 0
    while index < len(s):
        m = TIME_TOKEN_RE.match(s, index)
        if not m:
            raise ValueError('Invalid duration (syntax error around '
                             'character %s)' % index)
        index = m.end()
        value = float(m.group(1)) if m.group(2) else int(m.group(1))
        total += value * TIME_TOKEN_VALUES[m.group(3)]
    return total

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
    sorted_warnings.sort(key=lambda w: w[0])
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
            while cur_index < warning_count and now >= timeouts[cur_index]:
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
        if not any(match_check(msg, check) for check in self.checks):
            return False
        if self.last_seen is not None and self.last_seen >= msg.time:
            return False
        self.last_seen = msg.time
        self.cond.notifyAll()
        return True

    def handle_chat(self, msg, meta):
        with self.cond:
            if self._process_post(msg):
                self.logger.info('Quarry posted: <%s> %r' % (msg.sender.name,
                                                             msg.content))

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
                self.logger.info('Quarry located (at %s); log search done.' %
                                 basebot.format_datetime(self.last_seen))
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

class BellBotManager(basebot.BotManager):
    @classmethod
    def create_parser(cls, config, kwds=None):
        if kwds is None: kwds = {}
        kwds['fromfile_prefix_chars'] = '@'
        return basebot.BotManager.create_parser(config, kwds)

    @classmethod
    def prepare_parser(cls, parser, config):
        def check(s):
            tp, sep, pattern = s.partition(':')
            if not sep:
                raise ValueError('Invalid check (missing colon)')
            elif tp == 'nick':
                pattern_key = 'nick'
            elif tp == 'nick-regex':
                pattern_key = 'regex'
                pattern = re.compile(pattern)
            elif tp == 'uid':
                pattern_key = 'uid'
            else:
                raise ValueError('Unrecognized check type %s' % (tp,))
            return {'type': tp, pattern_key: pattern}

        def timeout(s):
            return parse_duration(s)

        def warning(s):
            timeout, sep, text = s.partition(':')
            if not sep:
                raise ValueError('Invalid warning (missing colon)')
            return {'timeout': parse_duration(timeout), 'text': text}

        basebot.BotManager.prepare_parser(parser, config)
        parser.add_argument('--check', metavar='TYPE:PATTERN',
                            action='append', type=check, dest='checks',
                            default=[],
                            help='Add a rule for identifying the user to '
                                 'watch (one of nick:NICKNAME, '
                                 'nick-regex:PATTERN, or uid:UID; '
                                 'no default)')
        parser.add_argument('--timeout', metavar='DURATION', type=timeout,
                            dest='main_timeout', default=DEFAULT_TIMEOUT,
                            help='The "primary" timeout, associated with a '
                                 'default warning (default %s)' %
                                 basebot.format_delta(DEFAULT_TIMEOUT,
                                                      False))
        parser.add_argument('--no-default-warning', action='store_true',
                            help='Suppress the default warning (which is %r '
                            'at the main timeout)' % DEFAULT_WARNING)
        parser.add_argument('--warn', metavar='DURATION:TEXT',
                            action='append', type=warning, dest='warnings',
                            default=[],
                            help='Configure a custom announcement to be '
                                 'posted a custom time after the user\'s '
                                 'last post (no default)')

    @classmethod
    def interpret_args(cls, arguments, config):
        bots, config = basebot.BotManager.interpret_args(arguments, config)
        config['checks'] = arguments.checks
        config['main_timeout'] = arguments.main_timeout
        if not arguments.no_default_warning:
            dw = {'timeout': arguments.main_timeout,
                  'text': DEFAULT_WARNING}
            arguments.warnings.insert(0, dw)
        config['warnings'] = arguments.warnings
        return (bots, config)

def main():
    basebot.run_main(BellBot, mgrcls=BellBotManager)

if __name__ == '__main__': main()
