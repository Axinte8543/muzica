import urllib.request, json
base='http://127.0.0.1:8000/api/search/?q=MGK666'
params=[('no_filter',''),('genre','rock'),('year','1999'),('country_ro','ro'),('country_intl','intl'),('min_rating_3','min_rating=3'),('reviewed_only','reviewed_only=1'),('followed_only','followed_only=1')]
for name,p in params:
    url=base+('&'+p if p else '')
    try:
        r=urllib.request.urlopen(url, timeout=10)
        data=json.loads(r.read().decode())
        albums=len(data.get('albums',[]))
        songs=len(data.get('songs',[]))
        print(name, '->', 'STATUS', r.getcode(), 'albums', albums, 'songs', songs)
        if albums>0:
            print('  sample albums:', [a['title'] for a in data['albums'][:5]])
    except Exception as e:
        print(name, 'ERROR', repr(e))
