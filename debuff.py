#!/usr/bin/python3
import argparse
import requests
import signal
import os
import readline
import sqlite3
import re
import sys
import inspect
from bs4 import BeautifulSoup
from lxml import html
signal.signal(signal.SIGINT | signal.SIGKILL, lambda x,y: print() or sys.exit(0))
sess = requests.session()
sess.headers.update({'User-Agent':'w3m/0.5.1'})
script_directory = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
sqlite_db_path = os.path.join(script_directory, 'dotabuff.sqlite')
con = sqlite3.connect(sqlite_db_path)
con.execute('CREATE TABLE IF NOT EXISTS HERO (name text primary key, adv real, other text)')
con.commit()

def list_heroes():
    res = sess.get('https://www.dotabuff.com/heroes').text
    bs = BeautifulSoup(res,'lxml')
    as_ = bs.find_all(lambda tag: tag.name == 'a' \
            and tag.has_attr('href') \
            and '/heroes/' in tag.get('href'))[10:] # first 10 results are worthless atm
    return [a.get('href').replace('/heroes/','') for a in list(filter(None, as_))]

def parse_hero_page(hero):
    bs = BeautifulSoup(sess.get('https://www.dotabuff.com/heroes/' + 
        hero + '/matchups').text, 'lxml')
    lines = bs.find_all(lambda tag: tag.name == 'tr' \
            and tag.has_attr('data-link-to'))
    print(hero)
    for i in range(len(lines)):
        advtg = float(lines[i].find_all(lambda tag: tag.name == 'td')[2].text[:-1])
        con.execute('INSERT OR REPLACE INTO hero VALUES (?,?,?)',\
                [hero, advtg, lines[i].get('data-link-to').replace('/heroes/','')])
    con.commit()

def update_advantages():
    for h in list_heroes(): parse_hero_page(h)

def get_counters_for(heroes):
    hero_group = str(heroes).replace('"','\'').replace(']',')').replace('[','(')
    return con.execute('SELECT name,SUM(adv) as s_adv \
            FROM HERO \
            WHERE other IN ' + hero_group + ' \
            AND name NOT IN ' + hero_group + ' \
            GROUP BY name \
            ORDER BY s_adv DESC').fetchall()


class MyCompleter(object):  # Custom completer
    def __init__(self, options):
        self.options = sorted(options)
    def complete(self, text, state):
        if state == 0:  # on first trigger, build possible matches
            if text:  self.matches = [s for s in self.options if s and s.startswith(text)]# cache matches (entries that start with entered text)
            else:  self.matches = self.options[:]# no text entered, all matches possible
        # return match indexed by state
        try: return self.matches[state]
        except IndexError: return None
parser = argparse.ArgumentParser(description='Calculate best advantages for Dota 2 heroes matchups')
parser.add_argument('-u',action='store_true', help='Update database first')
if parser.parse_args().u: update_advantages()
heroes = list_heroes()
readline.set_completer(MyCompleter(heroes).complete)
readline.parse_and_bind('tab: complete')
heroes_to_counter = [] 

while True:
    hero_to_counter = input('Next hero: ') 
    if hero_to_counter in heroes: heroes_to_counter.append(hero_to_counter)
    counters = get_counters_for(heroes_to_counter)
    [print(c) for c in counters]
    print('Are good against ', heroes_to_counter)
    if len(heroes_to_counter) == 5: heroes_to_counter.clear()
