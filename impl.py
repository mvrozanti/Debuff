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
# parser.add_argument('-n',metavar='request-count',default=50,help='amount of requests (default=50, 0=infinite)')
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

con.execute('CREATE TABLE IF NOT EXISTS `match` ( \
        `match_id` INTEGER NOT NULL, \
        `radiant_win` BOOLEAN NOT NULL, \
        `hero` TEXT NOT NULL, \
        `radiant_team` BOOLEAN NOT NULL, \
        PRIMARY KEY(`match_id`, `hero`))')
con.commit()

def get_tangent_match(newest=True):
    return con.execute('SELECT ' + ('MAX' if newest else 'MIN')  + '(match_id) FROM match').fetchone()[0]

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
            cur.execute('INSERT INTO match VALUES (?,?,?,?)', \
                    [match_id, radiant_win, h, h in radiant_heroes])
        con.commit()
        LOG.debug(str(match_id) + '\tOK') 
    except Exception as e:
        LOG.debug(str(match_id) + '\tFAILED')

def scrape(incremental=True, target_match=0):
    if not target_match:
        target_match = get_tangent_match(newest=incremental)
    target_match += 1 if incremental else -1
    insert_match(target_match)
    scrape(incremental=incremental, target_match=target_match)

if parsed.s or parsed.b: threading.Thread(target=scrape, kwargs=dict(incremental=False)).start()
if parsed.n or parsed.b: threading.Thread(target=scrape, kwargs=dict(incremental=True)).start()
