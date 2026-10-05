import json,re,collections,statistics
BAD=re.compile(r'warrant|right|unit|preferred|depositary|notes due|debenture|\d+(\.\d+)?%|subordinated|baby bond|perpetual|fixed-to|series [a-z] |when issued',re.I)
FUND=re.compile(r"\bfund\b|\bmuni|municipal|income trust|equity trust|opportunit(y|ies) trust|royalty trust|closed[- ]end|blackrock|nuveen|eaton vance|gabelli|abrdn|virtus|pimco|calamos|royce|doubleline|cohen & steers|tri continental|general american investors|central securities|adams (diversified|natural)|liberty all-star|kayne anderson|western asset|invesco|flaherty|john hancock|mfs |putnam|templeton|tekla|ellsworth|bancroft|source capital|aberdeen|allspring|saba|clough|guggenheim|first trust|neuberger|pioneer|highland|special opportunities|strats|zones",re.I)
KEEP={'BLK','CNS','IVZ','BEN','NUV','GS'}
BANDS=[('t1','$1T+',1e12,1e20),('b100','$100B–$1T',1e11,1e12),('b10','$10B–$100B',1e10,1e11),('b1','$1B–$10B',1e9,1e10),('m100','$100M–$1B',1e8,1e9),('m10','$10M–$100M',1e7,1e8)]
def companies(rows):
    keep=[]
    for r in rows:
        try: mc=float(r.get('marketCap') or 0)
        except: continue
        sym=r['symbol']; n=r['name']
        if mc<=0 or r.get('industry')=='Blank Checks' or '^' in sym or BAD.search(n): continue
        if r.get('country')!='United States' and not sym.startswith('BRK'): continue
        if sym not in KEEP and FUND.search(n): continue
        keep.append(dict(sym=sym,name=n,mc=mc,sector=r.get('sector') or '',ex=r.get('_ex','')))
    def key(n): return ' '.join(re.sub(r'[^a-z0-9 ]','',n.lower()).split()[:2])
    g=collections.defaultdict(list)
    for k in keep: g[key(k['name'])].append(k)
    out=[]
    for v in g.values():
        v.sort(key=lambda x:-x['mc']); ch=[]
        for x in v:
            if any(abs(x['mc']-c['mc'])/c['mc']<0.06 for c in ch): continue
            ch.append(x)
        out+=ch
    return out
def band_stats(cos):
    allv=sum(c['mc'] for c in cos if c['mc']>=1e7); res=[]
    for bid,name,lo,hi in BANDS:
        caps=[c['mc'] for c in cos if lo<=c['mc']<hi]
        res.append(dict(id=bid,n=len(caps),median=statistics.median(caps) if caps else 0,total=sum(caps),share=sum(caps)/allv))
    return res,allv
