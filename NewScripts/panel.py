#!/usr/bin/env python3
"""
PMS -> AI   (Single EXE)
  panel.exe          ( 8080)
 python panel.py 9090   
"""
import sys, os, json, time, subprocess, http.server, urllib.parse, webbrowser, datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MP = getattr(sys, '_MEIPASS', '')
SYNC_SCRIPT = next((p for p in [
    os.path.join(MP, 'pms_sync.py'),
    os.path.join(SCRIPT_DIR, 'NewScripts', 'pms_sync.py'),
    os.path.join(SCRIPT_DIR, 'pms_sync.py'),
] if os.path.isfile(p)), os.path.join(SCRIPT_DIR, 'NewScripts', 'pms_sync.py'))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

HTML = '''<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>PMS  Sync Panel</title>
<style>
:root{--bg:#06080c;--ca:#0d1117;--bd:#1a2332;--tx:#bcc6d0;--di:#4a5568;--ac:#3b82f6;--a2:#06b6d4;--gr:#10b981;--rd:#ef4444;--am:#f59e0b;--pr:#8b5cf6}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;background:var(--bg);color:var(--tx);min-height:100vh}
.app{max-width:780px;margin:0 auto;padding:32px 18px 60px}
.hdr{display:flex;align-items:center;gap:14px;margin-bottom:28px}
.hdr .ico{width:42px;height:42px;border-radius:11px;background:linear-gradient(135deg,var(--ac),var(--pr));display:flex;align-items:center;justify-content:center;font-size:20px;box-shadow:0 4px 18px rgba(59,130,246,.22)}
.hdr h1{font-size:21px;font-weight:700;letter-spacing:-.4px;color:#e2e8f0}
.hdr .ver{font-size:11px;color:var(--di);margin-left:6px}
.c{background:var(--ca);border:1px solid var(--bd);border-radius:14px;padding:22px;margin-bottom:14px}
.ct{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:2px;color:var(--di);margin-bottom:16px;display:flex;align-items:center;gap:8px}
.ct i{width:3px;height:13px;border-radius:2px;background:var(--ac);display:inline-block}
.rw{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.rw+.rw{margin-top:10px}
.in{flex:1;min-width:140px;background:#06080c;border:1px solid var(--bd);border-radius:9px;padding:11px 14px;color:#e2e8f0;font-size:13px;outline:none;transition:.2s;font-family:inherit}.in:focus{border-color:var(--ac);box-shadow:0 0 0 3px rgba(59,130,246,.08)}.in::placeholder{color:#374151}
.is{width:80px;text-align:center;flex:none}.id{width:146px;flex:none}
.ms{display:flex;gap:5px;flex-wrap:wrap}
.mb{padding:9px 16px;border-radius:9px;border:1px solid var(--bd);background:transparent;color:var(--di);font-size:13px;cursor:pointer;transition:.2s;font-weight:500;font-family:inherit}
.mb:hover{border-color:#374151;color:var(--tx)}.mb.on{background:rgba(59,130,246,.08);border-color:var(--ac);color:var(--ac);font-weight:600}
.mx{display:none;animation:fI .25s ease}.mx.s{display:flex}
.bt{display:inline-flex;align-items:center;gap:7px;padding:11px 26px;border-radius:11px;font-size:14px;font-weight:600;cursor:pointer;border:none;transition:.3s;font-family:inherit}
.bt-go{background:linear-gradient(135deg,var(--ac),var(--a2));color:#fff;box-shadow:0 4px 16px rgba(59,130,246,.28)}.bt-go:hover{transform:translateY(-1px);box-shadow:0 6px 22px rgba(59,130,246,.36)}.bt-go:disabled{opacity:.35;transform:none;cursor:not-allowed;box-shadow:none}
.sta{display:inline-flex;align-items:center;gap:7px;font-size:13px;margin-left:12px}.sta .d{width:7px;height:7px;border-radius:50%}.d.i{background:var(--di)}.d.b{background:var(--ac);animation:pl 1.5s infinite}.d.o{background:var(--gr)}.d.e{background:var(--rd)}
@keyframes pl{0%,100%{opacity:1}50%{opacity:.25}}
.re{display:none}.re.s{display:block}
.gr{display:grid;grid-template-columns:repeat(auto-fill,minmax(105px,1fr));gap:7px;margin-bottom:12px}
.st{background:#06080c;border:1px solid var(--bd);border-radius:9px;padding:13px 8px;text-align:center}
.st .n{font-size:20px;font-weight:700}.st .l{font-size:10px;color:var(--di);margin-top:3px;text-transform:uppercase;letter-spacing:.4px}
.st.g .n{color:var(--gr)}.st.u .n{color:var(--ac)}.st.s .n{color:var(--am)}.st.r .n{color:var(--rd)}.st.p .n{color:var(--pr)}
.su{text-align:center;padding:8px 14px;border-radius:7px;font-size:12px;margin-top:6px}.su.ok{color:var(--gr);background:rgba(16,185,129,.06)}.su.er{color:var(--rd);background:rgba(239,68,68,.06)}
.lb{background:#06080c;border:1px solid #111827;border-radius:12px;padding:12px 14px;font-family:'Cascadia Code','Consolas',monospace;font-size:11px;line-height:1.65;max-height:320px;overflow-y:auto;display:none}.lb.s{display:block}
.lb .L{color:#4b5563}.lb .S{color:#10b981}.lb .W{color:#f59e0b}.lb .E{color:#ef4444}.lb .H{color:#60a5fa;font-weight:700}
.ck{display:flex;align-items:center;gap:7px;font-size:13px;color:var(--di);cursor:pointer}.ck input{accent-color:var(--ac);width:14px;height:14px}
.fa{animation:fI .35s ease}@keyframes fI{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
.ft{text-align:center;font-size:10px;color:#1e293b;padding-top:20px}
</style></head><body>
<div class="app">
<div class="hdr"><div class="ico">S</div><div><h1>PMS Sync Panel<span class="ver">v3</span></h1><div style="font-size:11px;color:var(--di);margin-top:1px">Alashan 152</div></div></div>

<div class="c"><div class="ct"><i></i>Token</div>
<div class="rw"><input class="in" id="tk" placeholder="Paste Bearer token..."></div></div>

<div class="c"><div class="ct"><i></i>Sync Config</div>
<div class="ms">
<button class="mb on" data-m="incr" onclick="sm('incr')">Daily</button>
<button class="mb" data-m="full" onclick="sm('full')">Full</button>
<button class="mb" data-m="date" onclick="sm('date')">Date</button>
<button class="mb" data-m="range" onclick="sm('range')">Range</button>
</div>
<div class="rw mx s" id="mxDays"><span style="font-size:12px;color:var(--di)">Last</span><input class="in is" id="da" value="3" min="1" max="90" type="number"><span style="font-size:12px;color:var(--di)">days</span></div>
<div class="rw mx" id="mxDate"><input class="in id" id="ds" type="date"></div>
<div class="rw mx" id="mxRange"><input class="in id" id="df" type="date"><span style="color:var(--di)">&rarr;</span><input class="in id" id="dt" type="date"></div>
<div class="rw" style="margin-top:12px"><label class="ck"><input type="checkbox" id="dr"> Dry-Run (preview only)</label></div>
<div class="rw" style="margin-top:14px"><button class="bt bt-go" id="bg" onclick="go()">Start</button><div class="sta"><span class="d i" id="dot"></span><span id="stx" style="color:var(--di)">Ready</span></div></div></div>

<div class="c re" id="rc"><div class="ct"><i></i>Results</div><div class="gr" id="g"></div><div class="su" id="su"></div></div>
<div class="lb" id="lb"></div>
<div class="ft">DingTalk AI BI &middot; Zuoqi Polaris</div>
</div>

<script>
const $=id=>document.getElementById(id);
let es=null, mo='incr';
(function(){const t=localStorage.getItem('pt');if(t)$('tk').value=t;$('mxDays').classList.add('s')})();

function sm(m){mo=m;
  document.querySelectorAll('.mb').forEach(b=>b.classList.toggle('on',b.dataset.m===m));
  $('mxDays').classList.toggle('s',m==='incr');
  $('mxDate').classList.toggle('s',m==='date');
  $('mxRange').classList.toggle('s',m==='range');
}

function go(){
  const tk=$('tk').value.trim();if(!tk){alert('Token required');return}
  localStorage.setItem('pt',tk);
  const p={token:tk,mode:mo,dryrun:$('dr').checked};
  if(mo==='incr')p.days=parseInt($('da').value)||3;
  if(mo==='date')p.date=$('ds').value;
  if(mo==='range'){p.date_start=$('df').value;p.date_end=$('dt').value}
  $('bg').disabled=true;$('dot').className='d b';$('stx').textContent='Running...';$('stx').style.color='var(--ac)';
  $('rc').classList.add('s','fa');$('lb').classList.add('s');$('lb').innerHTML='';$('g').innerHTML='';$('su').textContent='';
  if(es)es.close();
  es=new EventSource('/api/run?'+new URLSearchParams(p));
  es.onmessage=function(e){
    try{const d=JSON.parse(e.data);
    if(d.t==='l'){let c='L';const m=d.m;
      if(/===|Start/.test(m))c='H';else if(/pass|OK/.test(m))c='S';else if(/skip|WARN/.test(m))c='W';else if(/fail|ERROR|err/.test(m))c='E';
      $('lb').innerHTML+='<span class="'+c+'">'+m+'</span>\n';$('lb').scrollTop=$('lb').scrollHeight
    }else if(d.t==='d'){es.close();done(d)}
    }catch(ex){}
  };
  es.onerror=function(){es.close();done(null)}
}

function done(d){
  $('bg').disabled=false;
  if(d&&d.ok){$('dot').className='d o';$('stx').textContent='Done';$('stx').style.color='var(--gr)'}
  else if(d){$('dot').className='d e';$('stx').textContent='Failed';$('stx').style.color='var(--rd)'}
  else{$('dot').className='d i';$('stx').textContent='Stopped';$('stx').style.color='var(--di)'}
  if(d&&d.d){let h='';for(const[n,r]of Object.entries(d.d)){
    const nw=r.new||0,up=r.updated||0,sk=r.skipped||0,dl=r.deleted||0,er=r.error||(r.create_fail>0||r.update_fail>0||r.delete_fail>0);
    let c='g';if(er)c='r';else if(nw>0)c='g';else if(up>0)c='u';else c='s';
    h+='<div class="st '+c+'"><div class="n">'+(er?'!':(nw+'/'+up))+'</div><div class="l">'+n+'</div></div>'
  }$('g').innerHTML=h}
  if(d){$('su').textContent=(d.tm||'')+' '+(d.ok?'OK':'FAIL')+' '+(d.lg||'');$('su').className='su '+(d.ok?'ok':'er')}
}
</script></body></html>'''

class API:
    def html(self,q): return 200,'text/html; charset=utf-8',HTML
    def sync(self,q):
        tk=q.get('token',[''])[0];mo=q.get('mode',['incr'])[0];dr='true'in q.get('dryrun',['false'])[0].lower()
        cmd=[sys.executable,SYNC_SCRIPT,'--token',tk]
        if mo=='full':cmd.append('--full')
        elif mo=='date':d=q.get('date',[''])[0];cmd.extend(['--date',d,'--days','1'])if d else None
        elif mo=='range':
            a=q.get('date_start',[''])[0];b=q.get('date_end',[''])[0]
            if a and b:
                try:
                    s=datetime.datetime.strptime(a,'%Y-%m-%d');e=datetime.datetime.strptime(b,'%Y-%m-%d')
                    cmd.extend(['--date',b,'--days',str(max(1,(e-s).days+1))])
                except:pass
        if mo=='incr':cmd.extend(['--days',str(int(q.get('days',['3'])[0])or 3)])
        if dr:cmd.append('--dry-run')

        def g():
            yield 'event: message\ndata: '+json.dumps({'t':'l','m':'Starting sync...'})+'\n\n'
            try:
                p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                for line in iter(p.stdout.readline,b''):
                    try:txt=line.decode('utf-8')
                    except:txt=line.decode('gbk',errors='replace')
                    for l in txt.split('\n'):
                        l=l.strip()
                        if l:yield 'event: message\ndata: '+json.dumps({'t':'l','m':l})+'\n\n'
                p.wait();ok=p.returncode==0
                yield 'event: message\ndata: '+json.dumps({'t':'d','ok':ok,'tm':'','lg':'','d':{}})+'\n\n'
            except Exception as ex:
                yield 'event: message\ndata: '+json.dumps({'t':'l','m':'Error: '+str(ex)})+'\n\n'
                yield 'event: message\ndata: '+json.dumps({'t':'d','ok':False})+'\n\n'
        b=g();h={'Content-Type':'text/event-stream','Cache-Control':'no-cache','Connection':'keep-alive'}
        return 200,h,b

    def route(self,m,p,q):
        if m=='GET'and p=='/':return self.html(q)
        if m=='GET'and p=='/api/run':return self.sync(q)
        return 404,'text/plain','Not Found'

def main():
    api=API()
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            u=urllib.parse.urlparse(self.path);q=urllib.parse.parse_qs(u.query)
            try:
                c,ct,body=api.route('GET',u.path,q)
                if c==200 and isinstance(body,type(iter([]))):
                    self.send_response(200)
                    if isinstance(ct,dict):
                        for k,v in ct.items():self.send_header(k,v)
                    else:self.send_header('Content-Type',ct)
                    self.end_headers()
                    for chunk in body:self.wfile.write(chunk.encode('utf-8')if isinstance(chunk,str)else chunk);self.wfile.flush()
                    return
                bd=body.encode('utf-8')if isinstance(body,str)else body
                self.send_response(c);self.send_header('Content-Type',ct);self.send_header('Content-Length',str(len(bd)))
                self.end_headers();self.wfile.write(bd)
            except:self.send_error(500)
        def log_message(self,*a):pass
    url=f'http://127.0.0.1:{PORT}'
    print(f'Panel: {url}');webbrowser.open(url)
    try:http.server.HTTPServer(('127.0.0.1',PORT),H).serve_forever()
    except KeyboardInterrupt:print('\nStopped')

if __name__=='__main__':main()
