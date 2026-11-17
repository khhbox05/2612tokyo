import zipfile,re,json,sys,os,urllib.request,tempfile,xml.etree.ElementTree as ET
SHEET='14hfJk3fqBotqKsSXL8p9Z4hlR-hldo9QP4YJI_OF5e4'
NS='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
RN='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
def load(path):
    z=zipfile.ZipFile(path)
    ss=[''.join(t.text or '' for t in si.iter(NS+'t')) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(NS+'si')]
    sh=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    rels={r.get('Id'):r.get('Target') for r in ET.fromstring(z.read('xl/worksheets/_rels/sheet1.xml.rels'))}
    links={h.get('ref'):rels.get(h.get(RN+'id')) for h in sh.iter(NS+'hyperlink') if h.get(RN+'id')}
    cells={}
    for c in sh.iter(NS+'c'):
        v=c.find(NS+'v');t=c.get('t')
        if t=='inlineStr':val=''.join(x.text or '' for x in c.iter(NS+'t'))
        elif v is None:continue
        elif t=='s':val=ss[int(v.text)]
        else:val=v.text
        cells[c.get('r')]=(val,t)
    return cells,links
def build(path):
    cells,links=load(path)
    rows=max(int(re.sub(r'\D','',k)) for k in cells)
    def g(col,r):return cells.get(f'{col}{r}',('',None))
    def s(col,r):return (g(col,r)[0] or '').strip()
    def money(col,r):
        v,t=g(col,r)
        if not v:return ''
        try:f=float(v);return f'{int(round(f)):,}'
        except:return v.strip()
    def tm(r):
        v,t=g('B',r)
        if not v:return ''
        try:
            f=float(v)
            if f<1:m=round(f*1440);return f'{m//60:02d}:{m%60:02d}'
        except:pass
        return v.strip()
    REF=['喫茶咖啡','餐廳','超市','錢湯','備案']
    days=[];refs=[];cur=None;total=''
    for r in range(2,rows+1):
        a=re.sub(r'\s+','',s('A',r));name=s('C',r)
        if re.match(r'\d+/\d+',a):cur={'date':a,'items':[]};days.append(cur)
        elif a in REF:cur={'title':a,'items':[]};refs.append(cur)
        if not name:
            if s('G',r) and not any(s(c,r) for c in 'ABDEFH'):total=money('G',r)
            continue
        if cur is None:continue
        cur['items'].append(dict(time=tm(r),name=name,via=s('D',r),note=s('E',r),hours=s('F',r),jpy=money('G',r),ntd=money('H',r),url=links.get(f'C{r}') or '',noteUrl=links.get(f'E{r}') or ''))
    return dict(name='行程',days=days,refs=refs,total=total)

def main():
    root=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    url=f'https://docs.google.com/spreadsheets/d/{SHEET}/export?format=xlsx'
    tmp=os.path.join(tempfile.mkdtemp(),'s.xlsx')
    urllib.request.urlretrieve(url,tmp)
    d=build(tmp)
    if len(d['days'])<1 or not d['total'] or sum(len(x['items']) for x in d['days'])<10:
        sys.exit('parsed data looks wrong, aborting')
    p=os.path.join(root,'index.html')
    h=open(p,encoding='utf-8').read()
    new,n=re.subn(r'var D=.*?;\nvar tabs',lambda m:'var D='+json.dumps(d,ensure_ascii=False)+';\nvar tabs',h,count=1,flags=re.S)
    if n!=1:sys.exit('data marker not found in index.html')
    if new!=h:
        open(p,'w',encoding='utf-8').write(new);print('updated')
    else:print('no change')
if __name__=='__main__':main()
