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
    as_ = bs.find_all(lambda tag: tag.name == 'a' and tag.has_attr('href') and '/heroes/' in tag.get('href'))[10:] # first 10 results are worthless atm
    heroes = []
    for a in list(filter(None,as_)): 
        heroes.append(a.get('href').replace('/heroes/',''))
    return heroes

def parse_hero_page(hero):
    url = 'https://www.dotabuff.com/heroes/' + hero + '/matchups'
    bs = BeautifulSoup(sess.get(url).text, 'lxml')
    lines = bs.find_all(lambda tag: tag.name == 'tr' and tag.has_attr('data-link-to'))
    i = 0
    for l in lines:
        other_hero = l.get('data-link-to').replace('/heroes/','')
        tds = l.find_all(lambda tag: tag.name == 'td')
        advtg = float(tds[2].text[:-1])
        print(other_hero, advtg)
        con.execute('INSERT OR REPLACE INTO HERO VALUES (?,?,?)', [hero, advtg, other_hero])
        i+=1
        if not i % len(heroes) - 5: con.commit()
    con.commit()

def update_advantages():
    heroes = list_heroes()
    for h in heroes:
        parse_hero_page(h)

def get_counters_for(heroes):
    hero_group = str(heroes).replace('"','\'').replace(']',')').replace('[','(')
    counters = con.execute('SELECT name,SUM(adv) as s_adv FROM HERO WHERE other IN ' + hero_group + ' AND name NOT IN ' + hero_group + ' GROUP BY name ORDER BY s_adv DESC').fetchall()
    print(counters[:10])

    


get_counters_for(['invoker','clockwerk','doom'])
#     for h in heroes:
#         select+=h
#     'SELECT h1.name,h1.adv,h1.other,h2.adv,h2.other,h3.adv,h3.other,(h1.adv+h2.adv+h3.adv) as adv_sum
#     FROM HERO h1
#     LEFT JOIN HERO h2 ON h1.name=h2.name
#     LEFT JOIN HERO h3 ON h2.name=h3.name
#     WHERE h1.other ='invoker' and h2.other='clockwerk' and h3.other='doom'
#     ORDER BY adv_sum DESC''')
#     LIMIT 50
