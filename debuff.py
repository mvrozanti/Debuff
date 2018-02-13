import requests
import os
import readline
import sqlite3
import re
from bs4 import BeautifulSoup
from lxml import html

sess = requests.session()
sess.headers.update({'User-Agent':'w3m/0.5.1'})
con = sqlite3.connect('dotabuff.sqlite')

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
    for i in range(len(lines)):
        advtg = float(lines[i].find_all(lambda tag: tag.name == 'td')[2].text[:-1])
        print(advtg)
        con.execute('INSERT OR REPLACE INTO HERO VALUES (?,?,?)',\
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
            ORDER BY s_adv ASC').fetchall()



class MyCompleter(object):  # Custom completer

    def __init__(self, options):
        self.options = sorted(options)

    def complete(self, text, state):
        if state == 0:  # on first trigger, build possible matches
            if text:  # cache matches (entries that start with entered text)
                self.matches = [s for s in self.options 
                                    if s and s.startswith(text)]
            else:  # no text entered, all matches possible
                self.matches = self.options[:]

        # return match indexed by state
        try: 
            return self.matches[state]
        except IndexError:
            return None

#update_advantages()
heroes = list_heroes()
completer = MyCompleter(heroes)
readline.set_completer(completer.complete)
readline.parse_and_bind('tab: complete')
heroes_to_counter = [] 

while True:
    hero_to_counter = input('Next hero:') 
    if hero_to_counter in heroes: heroes_to_counter.append(hero_to_counter)
    counters = get_counters_for(heroes_to_counter)
    [print(c) for c in counters]
    print('Are good against ', heroes_to_counter)


