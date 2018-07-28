#!/usr/bin/env python3
import readline
import threading
import logging
import os
import dota2api
import code
import json
import sqlite3
import argparse
import time
import sys

parser      = argparse.ArgumentParser(description='debuff v2')
group       = parser.add_mutually_exclusive_group(required=len(sys.argv) != 1)
group.add_argument('-o', action='store_true', help='auto insert from oldest in record to oldest')
group.add_argument('-n', action='store_true', help='auto insert from newest in record to newest')
group.add_argument('-b', action='store_true', help='both [WIP]')
group.add_argument('-q', action='store_true', default=len(sys.argv) == 1, help='query picks')
parser.add_argument('-v', default=1, help='verbose')
parser.add_argument('-c',metavar='request-count', type=int, default=1,help='amount of concurrent requests (default=2)')
# parser.add_argument('-o',metavar='output-file',default='addresses.txt',help='file to output tested working ips')
parsed = parser.parse_args()

D2_API_KEY = os.environ['D2_API_KEY']
api = dota2api.Initialise(D2_API_KEY)

LOG_FILE='debuff2.log'
LOG_FORMAT = "%(levelname)s %(name)s %(asctime)s - %(message)s" 
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.getLevelName('DEBUG'))
if parsed.v: LOG.addHandler(logging.StreamHandler(sys.stdout))

SQLITE_DB_PATH = '/mnt/4ADE1465DE144C17/gdrive/Programming/python/dotabuff/dota_matches.sqlite'
con = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
cur = con.cursor()

lock = threading.Lock()
con.execute('CREATE TABLE IF NOT EXISTS `match` ( \
        `match_id` INTEGER NOT NULL, \
        `radiant_win` BOOLEAN NOT NULL, \
        `hero` TEXT NOT NULL, \
        `radiant_team` BOOLEAN NOT NULL, \
        PRIMARY KEY(`match_id`, `hero`))')
con.commit()

def get_tangent_match(newest=True):
    return con.execute('SELECT ' + ('MAX' if newest else 'MIN')  + '(match_id) FROM match').fetchone()[0]

newest_match=get_tangent_match(newest=True)
oldest_match=get_tangent_match(newest=False)
to_be_inserted=[]

def insert_match(match_id):
    try:
        lock.acquire()
        match = api.get_match_details(match_id=match_id)
        timestamp = match['start_time']
        if time.time() - timestamp < 1000*60: 
            LOG.debug('Done with newest matches')
            sys.exit(0)
        heroes = [p['hero_name'].lower() for p in match['players']]
        if len(heroes) != 10: raise Exception('Incomplete match')
        radiant_heroes = heroes[:5]
        radiant_win = match['radiant_win']
        match = [[match_id, radiant_win, h, h in radiant_heroes] for h in heroes]
        global to_be_inserted
        to_be_inserted.append(match)
        LOG.debug(str(match_id) + '\tOK') 
    except Exception as e:
        if str(e) not in ["'hero_name'", \
                "'radiant_win'", \
                "'Match ID not found'", \
                "'Practice matches are not available via GetMatchDetails'"\
                'Incomplete match']: print(e)
        LOG.debug(str(match_id) + '\tFAILED')
    finally:
        lock.release()


def scrape(incremental=True):
    if incremental: 
        global newest_match
        newest_match += 1
    else: 
        global oldest_match
        oldest_match -= 1
    insert_match(newest_match if incremental else oldest_match)
    time.sleep(1)
    scrape(incremental=incremental)

def print_best_picks_having(to_counter, to_combo):
    query = """
            SELECT hero, COUNT(*)
            FROM   match
            WHERE  match_id IN (SELECT match_id
                                FROM   match
                                WHERE  (radiant_win = 1 AND hero IN ($qm_count_to_counter))
                                       OR (radiant_win = 0 AND hero IN ($qm_count_to_combo))
                                GROUP BY match_id)
                   AND hero NOT IN ($qm_sum)
                   AND radiant_win = radiant_team 
            GROUP BY hero
            ORDER BY COUNT(*) ASC;
            """
    if not to_counter: to_counter.append('')
    if not to_combo: to_combo.append('')
    query = query.replace('$qm_count_to_counter',   ','.join('?'*len(to_counter)))
    query = query.replace('$qm_count_to_combo',     ','.join('?'*len(to_combo)))
    query = query.replace('$qm_sum',                ','.join('?'*len(to_counter+to_combo)))
    best_picks = cur.execute(query, to_counter+to_combo+to_counter+to_combo).fetchall()
    for p in best_picks: print(p)
    print('Are good against ' + str(to_counter))
    print('And good with ' + str(to_combo))

def get_distinct_heroes():
    return [tupl[0].lower() for tupl in cur.execute('SELECT DISTINCT hero FROM match').fetchall()]

if parsed.q:
    to_counter,to_combo,heroes=[],[],get_distinct_heroes()
    class MyCompleter(object):                                                            # Custom completer
        def __init__(self, options):
            self.options = sorted(options)
        def complete(self, text, state):
            if state == 0:                                                                    # on first trigger, build possible matches
                if text:  self.matches = [s for s in self.options if s and s.startswith(text)]# cache matches (entries that start with entered text)
                else:  self.matches = self.options[:]                                         # no text entered, all matches possible
            try: return self.matches[state]                                                   # return match indexed by state 
            except IndexError: return None

    readline.set_completer(MyCompleter(heroes).complete)
    readline.parse_and_bind('tab: complete')
    while True:
        print('Next hero [-|+]:',end=' ') # may omit '+'
        action = input().lower()
        if not action: continue
        if action[0] == '+': 
            hero = action[1:]
            if hero in heroes: to_combo.append(hero)
        elif action[0] != '-': 
            hero = action
            if hero in heroes: to_combo.append(hero)
            else: to_counter.append(action[1:]) # if action[0] == '-'
        if to_combo or to_counter: print_best_picks_having(to_counter,to_combo)
    sys.exit(0)

def insert_handler():
    global to_be_inserted
    while True:
        if to_be_inserted:
            con.executemany('INSERT OR IGNORE INTO match VALUES (?,?,?,?)', \
                    to_be_inserted.pop())
            con.commit()

threading.Thread(target=insert_handler).start()
if parsed.o or parsed.b: 
    for _ in range(parsed.c): 
        threading.Thread(target=scrape, kwargs=dict(incremental=False)).start()

if parsed.n or parsed.b: 
    for _ in range(parsed.c): 
        threading.Thread(target=scrape, kwargs=dict(incremental=True)).start()
