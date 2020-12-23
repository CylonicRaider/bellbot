#!/usr/bin/env python3
# -*- coding: ascii -*-

"""
A Euphoria bot that watches for the disappearance of a user.
"""

def match_check(msg, check):
    if check['type'] == 'nick':
        return msg.sender.name == check['nick']
    elif check['type'] == 'nick-regex':
        return bool(check['regex'].search(msg.sender.name))
    elif check['type'] == 'uid':
        return msg.sender.id == check['id']
    else:
        raise RuntimeError('Unrecognized check %r' % (check['type'],))

def main():
    raise NotImplementedError

if __name__ == '__main__': main()
