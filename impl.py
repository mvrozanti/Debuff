#!/usr/bin/env python3
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
group       = parser.add_mutually_exclusive_group(required=True)
group.add_argument('-s', action='store_true', help='smart auto insert from oldest in record to older')
group.add_argument('-n', action='store_true', help='auto insert from newest in record to newest')
group.add_argument('-b', action='store_true', help='both [WIP]')
parser.add_argument('-v', action='store_true', help='verbose')
parser.add_argument('-c',metavar='request-count', type=int, default=2,help='amount of concurrent requests (default=2)')
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

def insert_match(match_id):
    try:
        match = api.get_match_details(match_id=match_id)
        timestamp = match['start_time']
        if time.time() - timestamp < 1000*60: 
            LOG.debug('Done with newest matches')
            sys.exit(0)
        heroes = [p['hero_name'] for p in match['players']]
        if len(heroes) != 10: raise Exception('Incomplete match')
        radiant_heroes = heroes[:5]
        radiant_win = match['radiant_win']
        for h in heroes:
            cur.execute('INSERT OR IGNORE INTO match VALUES (?,?,?,?)', \
                    [match_id, radiant_win, h, h in radiant_heroes])
        con.commit()
        LOG.debug(str(match_id) + '\tOK') 
    except Exception as e:
        LOG.debug(str(match_id) + '\tFAILED')

def scrape(incremental=True):
    if incremental: 
        global newest_match
        newest_match += 1
    else: 
        global oldest_match
        oldest_match -= 1
    insert_match(newest_match if incremental else oldest_match)
    scrape(incremental=incremental)

if parsed.s or parsed.b: 
    for _ in range(parsed.c//2): threading.Thread(target=scrape, kwargs=dict(incremental=False)).start()

if parsed.n or parsed.b: 
    for _ in range(parsed.c//2): threading.Thread(target=scrape, kwargs=dict(incremental=True)).start()
