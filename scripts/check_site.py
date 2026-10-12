"""Verify built Hugo pages and preview isolation. Run after a Hugo build."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import sys

class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.links=[]; self.ids=set(); self.h1=0; self.noindex=False
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if 'id' in a: self.ids.add(a['id'])
        if tag=='h1': self.h1+=1
        if tag in ('a','link','script','img'):
            v=a.get('href') or a.get('src')
            if v: self.links.append(v)
        if tag=='meta' and a.get('name')=='robots' and 'noindex' in a.get('content',''): self.noindex=True

root=Path(sys.argv[1]); preview='--preview' in sys.argv
required=['','business','technical','services','how-we-work','pricing','about','contact','privacy']
for route in required:
    f=root/route/'index.html'
    assert f.exists(),f'Missing page: {route}'
    t=f.read_text(); p=Page(t)
    assert p.h1==1,f'{route}: must have one h1'
    assert p.noindex==preview,f'{route}: wrong indexing policy'
    assert 'mailto:' not in t, f'{route}: pending email must not be live'
    for href in p.links:
        u=urlsplit(href)
        if u.scheme or u.netloc or not u.path: continue
        target=(root/unquote(u.path).lstrip('/')) if u.path.startswith('/') else (f.parent/unquote(u.path))
        if target.is_dir(): target=target/'index.html'
        assert target.exists(),f'{route}: broken link {href}'
        if u.fragment and target.suffix=='.html':
            assert u.fragment in Page(target.read_text()).ids,f'{route}: missing anchor {href}'
print(f'PASS: {len(required)} pages; links, headings, preview indexing, pending email')
