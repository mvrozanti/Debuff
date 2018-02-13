import requests
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
        con.execute('INSERT OR REPLACE INTO HERO VALUES (?,?,?)',\
                [hero, advtg, lines[i].get('data-link-to').replace('/heroes/','')])
        if not i % len(heroes) - 2: con.commit() # do not trash rest of computer
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

counters = get_counters_for(['invoker','leshrac','storm-spirit'])
[print(c) for c in counters]
