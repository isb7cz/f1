"""Previously verified Seznam TV programme: conservative secondary source."""
from datetime import datetime, timedelta
import gzip
import json
import re
import time
from urllib.request import Request, urlopen

from app import PRAGUE, session

SOURCE = 'https://tv.seznam.cz/'


def get(path):
    request = Request('https://tv.seznam.cz/api' + path, headers={'User-Agent':'F1-vikend/1.0'})
    with urlopen(request, timeout=25) as response:
        body = response.read(5_000_001)
        if len(body)>5_000_000:
            raise ValueError('Seznam response too large')
        if body[:2]==b'\x1f\x8b':
            body=gzip.decompress(body)
        return json.loads(body)


def convert(p):
    title = p['name']
    description = p.get('short_description') or ''
    if not re.match(r'^Formule\s*1\b',title,re.I) or p.get('live') is not True or re.search(r'záznam|repríz',description,re.I):
        return None
    kind=session(title)
    if kind=='other':
        return None
    start=datetime.fromtimestamp(p['time_from'],PRAGUE)
    end=datetime.fromtimestamp(p['time_to'],PRAGUE)
    if end<=start:
        raise ValueError('Invalid Seznam programme duration')
    return {'title':title, 'start':start.isoformat(), 'end':end.isoformat(), 'kind':kind,
            'grand_prix':re.sub(r'\s*\([^)]*\)\s*$','',re.sub(r'^Formule\s*1\s*[-–:]\s*','',title,flags=re.I)).strip() if kind!='intro' else None}


def fetch_seznam():
    channels=get('/broadcast')['_embedded']['tv:channel']
    channels=[c for c in channels if c['name'].casefold()=='nova sport 5']
    if len(channels)!=1:
        raise ValueError('Nova Sport 5 not uniquely identified on Seznam')
    today=datetime.now(PRAGUE).date()
    rows={}
    for offset in range(-3,16):
        day=today+timedelta(days=offset)
        data=get(f'/schedule/{channels[0]["id"]}?day={day}')
        programmes=data.get('_embedded',{}).get('tv:programme')
        if programmes is None and '_embedded' not in data and '_links' in data:
            programmes=[]
        if not isinstance(programmes,list):
            raise ValueError('Unexpected Seznam schedule schema')
        for p in programmes:
            row=convert(p)
            if row:
                rows[p['id']]=row
        time.sleep(0.3)
    return sorted(rows.values(),key=lambda p:p['start'])
