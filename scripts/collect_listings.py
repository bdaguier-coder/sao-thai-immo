#!/usr/bin/env python3
"""Collecte prudente de liens d'annonces publiques via flux RSS de recherche.
Les résultats ne sont pas garantis exhaustifs. Ne publie que ce que les sources permettent d'établir.
"""
import json, re, urllib.request, urllib.parse, xml.etree.ElementTree as ET, html, pathlib, datetime, time

QUERIES = [
    '"Angers" "local commercial" "vitrine" "m²"',
    '"Angers" "rez de chaussée" "local commercial" "m²"',
    '"Angers" "salon de coiffure" "droit au bail" "m²"',
    '"Angers" "institut de beauté" "à céder" "m²"',
    '"Angers" "boutique" "cession de bail" "m²"',
    '"Angers" "spa" "fonds de commerce" "m²"',
]
ALLOW = ('guilbeauchameroy-locauxpro.fr', 'alain-rousseau.com',
         'entreprises.nicole-joubert.fr', 'cessionpme.com', 'transentreprise.com',
         'ouestfrance-immo.com', 'seloger.com', 'bienici.com',
         'laforet.com', 'arthur-loyd.com', 'alentoor.fr')
UA = {'User-Agent': 'SaoThaiImmo/1.0 (public property research; browser RSS)'}
def text_only(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', s or ''))).strip()
def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=18) as r:
        return r.read(900000)
def number(s):
    return int(s.replace('\u202f','').replace('\xa0','').replace(' ', ''))
def parse_items(data):
    root = ET.fromstring(data)
    for item in root.findall('.//item'):
        yield {'title':text_only(item.findtext('title')), 'snippet':text_only(item.findtext('description')), 'url':item.findtext('link') or ''}
def extract(item, source):
    s=item['title']+' '+item['snippet']
    low=s.lower()
    if 'angers' not in low or ('bureau' in low and 'commerce' not in low and 'boutique' not in low):
        return None
    m=re.search(r'(?<!\d)(\d{2,3})(?:[,.]0+)?\s*(?:m²|m2|mètres carrés)',s,re.I)
    if not m: return None
    area=int(m.group(1))
    if not 60<=area<=140: return None
    # Les critères insuffisamment démontrés restent inconnus dans l'interface.
    front=True if 'vitrine' in low or 'devanture' in low else None
    ground=True if ('rez-de-chaussée' in low or 'rez de chaussée' in low or 'rdc' in low) else None
    commercial=True if any(x in low for x in ['local commercial','boutique','commerce','salon de coiffure','institut de beauté','spa']) else None
    if commercial is None: return None
    rents=re.findall(r'([\d\s\u202f\xa0]{3,8})\s*€\s*(?:/\s*mois|par mois|mensuel)',s,re.I)
    rent=number(rents[0]) if rents else None
    rent=rent if rent and rent<20000 else None
    u=source['url']
    return {'id':'rss-'+str(abs(hash(u))), 'title':item['title'][:140], 'area':area,
            'rdcArea':None, 'rent':rent, 'location':'Angers — adresse à vérifier',
            'type':'cession' if any(x in low for x in ['cession','céder','à céder','droit au bail','fonds de commerce']) else 'annonce',
            'agency':urllib.parse.urlparse(u).netloc, 'url':u, 'front':front,
            'ground':ground,'commercial':commercial,
            'note':'Signal provenant d’un flux RSS public. Surface et activité à vérifier sur l’annonce originale. '+item['snippet'][:220]}
def main():
    seen={}
    for q in QUERIES:
        url='https://www.bing.com/search?format=rss&q='+urllib.parse.quote(q)
        try:
            for it in parse_items(fetch(url)):
                host=urllib.parse.urlparse(it['url']).netloc.lower()
                if not any(host.endswith(x) for x in ALLOW): continue
                lead=extract(it,it)
                if lead: seen[lead['url']]=lead
        except Exception as e:
            print('RSS indisponible:',q,str(e)[:130])
        time.sleep(1)
    out=pathlib.Path('data/listings.json')
    out.parent.mkdir(parents=True,exist_ok=True)
    # On préserve les trouvailles précédentes. On évite de déduire qu'une offre est
    # toujours disponible d'une simple présence dans le fichier.
    prior=[]
    if out.exists():
        try: prior=json.loads(out.read_text(encoding='utf-8'))
        except Exception: pass
    for lead in prior:
        if lead.get('url') not in seen: seen[lead['url']]=lead
    result=list(seen.values())[:120]
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Pistes enregistrées :',len(result),'le',datetime.date.today())
if __name__=='__main__': main()
