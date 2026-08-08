#!/usr/bin/env python3
"""PMS Sync Panel v3 Enterprise Desktop Console"""
import sys, os, json, subprocess, threading, datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MP = getattr(sys, '_MEIPASS', '')
SYNC_SCRIPT = next((p for p in [os.path.join(MP,'pms_sync.py'),os.path.join(SCRIPT_DIR,'pms_sync.py'),os.path.join(SCRIPT_DIR,'NewScripts','pms_sync.py')] if os.path.isfile(p)), 'pms_sync.py')

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

BG='#0b0f15';CA='#131a24';BD='#1e2a3a';TX='#d1d5dc';DM='#5c6674'
AC='#4f8cf7';AD='#2563eb';GN='#22c55e';RD='#ef4444';AM='#f59e0b';LG='#10151d'

class App:
    def __init__(self):
        self.w=tk.Tk();self.w.title("PMS Sync Console");self.w.geometry("840x700")
        self.w.minsize(700,540);self.w.configure(bg=BG);self.proc=None
        self._style();self._ui();self.w.protocol("WM_DELETE_WINDOW",self._close)

    def _style(self):
        s=ttk.Style();s.theme_use('clam')
        s.configure('.',background=BG,foreground=TX,font=('Segoe UI',10))
        s.configure('TLabel',background=BG,foreground=DM,font=('Segoe UI',9))
        s.configure('TRadiobutton',background=BG,foreground=TX,font=('Segoe UI',10))
        s.map('TRadiobutton',foreground=[('selected',AC)])
        s.configure('TCheckbutton',background=BG,foreground=DM,font=('Segoe UI',9))

    def _card(self,p,title,**kw):
        f=tk.Frame(p,bg=CA,highlightthickness=1,highlightbackground=BD,**kw)
        f.pack(fill='x',pady=(0,10))
        h=tk.Frame(f,bg=CA);h.pack(fill='x',padx=18,pady=(14,2))
        tk.Label(h,text=title.upper(),font=('Segoe UI',9,'bold'),fg=DM,bg=CA,anchor='w').pack(side='left')
        return tk.Frame(f,bg=CA)

    def _ui(self):
        r=tk.Frame(self.w,bg=BG);r.pack(fill='both',expand=True,padx=20,pady=(20,10))
        hf=tk.Frame(r,bg=BG);hf.pack(fill='x',pady=(0,18))
        cv=tk.Canvas(hf,width=36,height=36,bg=BG,highlightthickness=0);cv.pack(side='left',padx=(0,12))
        cv.create_rectangle(0,0,36,36,fill=AC,outline='')
        cv.create_text(18,18,text='P',fill='#fff',font=('Segoe UI',15,'bold'))
        tk.Label(hf,text="PMS Sync Console",font=('Segoe UI',18,'bold'),fg='#e2e8f0',bg=BG).pack(side='left')
        tk.Label(hf,text="v3",font=('Segoe UI',9),fg=DM,bg=BG).pack(side='left',padx=(8,0))

        # TOKEN
        tc=self._card(r,"AUTH TOKEN")
        self.tv=tk.StringVar()
        xx=tk.Entry(tc,textvariable=self.tv,font=('Consolas',10),bg='#0d1117',fg=TX,relief='flat',insertbackground=TX,highlightthickness=1,highlightbackground=BD,highlightcolor=AC)
        xx.pack(fill='x',padx=18,pady=(0,14),ipady=6);xx.focus()

        # MODE
        mc=self._card(r,"SYNC CONFIG")
        rm=tk.Frame(mc,bg=CA);rm.pack(fill='x',padx=18,pady=(0,8))
        self.mv=tk.StringVar(value='incr')
        for v,t in [('incr','Daily'),('full','Full Sync'),('date','Date'),('range','Range')]:
            ttk.Radiobutton(rm,text=t,value=v,variable=self.mv,command=self._on_mode).pack(side='left',padx=(0,18))
        self.me=tk.Frame(mc,bg=CA);self.me.pack(fill='x',padx=18,pady=(0,10))
        self.dv=tk.StringVar(value='3')
        self.ds=ttk.Spinbox(self.me,from_=1,to=90,width=5,textvariable=self.dv)
        self.di=tk.Entry(self.me,width=14,font=('Segoe UI',10),bg='#0d1117',fg=TX,relief='flat',highlightthickness=1,highlightbackground=BD,highlightcolor=AC)
        self.di.insert(0,datetime.date.today().strftime('%Y-%m-%d'))
        self.rf=tk.Entry(self.me,width=14,font=('Segoe UI',10),bg='#0d1117',fg=TX,relief='flat',highlightthickness=1,highlightbackground=BD,highlightcolor=AC)
        self.rt=tk.Entry(self.me,width=14,font=('Segoe UI',10),bg='#0d1117',fg=TX,relief='flat',highlightthickness=1,highlightbackground=BD,highlightcolor=AC)
        self._on_mode()
        db=tk.Frame(mc,bg=CA);db.pack(fill='x',padx=18,pady=(0,8))
        self.dr=tk.BooleanVar()
        ttk.Checkbutton(db,text="Dry-Run (preview only)",variable=self.dr).pack(side='left')
        ab=tk.Frame(mc,bg=CA);ab.pack(fill='x',padx=18,pady=(8,14))
        self.bb=tk.Button(ab,text="Run Sync",command=self._start,bg=AC,fg='#fff',font=('Segoe UI',11,'bold'),relief='flat',activebackground=AD,activeforeground='#fff',padx=24,pady=8,cursor='hand2',borderwidth=0);self.bb.pack(side='left')
        self.sb=tk.Button(ab,text="Stop",command=self._stop,state='disabled',bg='#1a2233',fg=RD,font=('Segoe UI',11),relief='flat',activebackground='#2a1a1a',padx=16,pady=8,borderwidth=0);self.sb.pack(side='left',padx=(8,0))
        self.sl=tk.Label(ab,text=" Ready",font=('Segoe UI',10),fg=DM,bg=CA);self.sl.pack(side='left',padx=(16,0))

        # RESULTS
        self.rc=self._card(r,"RESULTS");self.rg=tk.Frame(self.rc,bg=CA);self.rg.pack(fill='x',padx=18,pady=(4,8))
        self.rs=tk.Label(self.rc,text="",font=('Segoe UI',9),bg=CA,fg=DM);self.rs.pack(padx=18,pady=(0,10))
        self._hide_res()

        # LOG
        lf=tk.Frame(r,bg=BG);lf.pack(fill='both',expand=True)
        tk.Label(lf,text="EXECUTION LOG",font=('Segoe UI',9,'bold'),fg=DM,bg=BG,anchor='w').pack(fill='x')
        self.lg=scrolledtext.ScrolledText(lf,height=14,bg=LG,fg=TX,insertbackground=TX,font=('Cascadia Code',9),relief='flat',borderwidth=1,highlightthickness=1,highlightbackground=BD)
        self.lg.pack(fill='both',expand=True,pady=(4,0))
        for t,c in [('H',AC),('S',GN),('W',AM),('E',RD),('D',DM)]:self.lg.tag_config(t,foreground=c)
        self.lg.tag_config('H',font=('Cascadia Code',9,'bold'))
        self.lg.insert('end','Ready.\n','D')

    def _on_mode(self):
        m=self.mv.get()
        for w in self.me.winfo_children():w.pack_forget()
        if m=='incr':tk.Label(self.me,text="Past",font=('Segoe UI',9),fg=DM,bg=CA).pack(side='left');self.ds.pack(side='left',padx=(4,6));tk.Label(self.me,text="days",font=('Segoe UI',9),fg=DM,bg=CA).pack(side='left')
        elif m=='date':tk.Label(self.me,text="Date",font=('Segoe UI',9),fg=DM,bg=CA).pack(side='left');self.di.pack(side='left',padx=(8,0))
        elif m=='range':tk.Label(self.me,text="From",font=('Segoe UI',9),fg=DM,bg=CA).pack(side='left');self.rf.pack(side='left',padx=(6,6));tk.Label(self.me,text="to",font=('Segoe UI',9),fg=DM,bg=CA).pack(side='left');self.rt.pack(side='left',padx=(6,0))

    def _hide_res(self):
        for w in self.rg.winfo_children():w.destroy();self.rs.configure(text='')

    def _start(self):
        t=self.tv.get().strip()
        if not t:messagebox.showwarning("Token","PMS Bearer token required.");return
        if not t.lower().startswith('bearer '):t='Bearer '+t
        mo,dr=self.mv.get(),self.dr.get()
        cmd=[sys.executable,SYNC_SCRIPT,'--token',t]
        if mo=='full':cmd.append('--full')
        elif mo=='date':cmd.extend(['--date',self.di.get(),'--days','1'])
        elif mo=='range':
            a,b=self.rf.get().strip(),self.rt.get().strip()
            if a and b:
                try:s=datetime.datetime.strptime(a,'%Y-%m-%d');e=datetime.datetime.strptime(b,'%Y-%m-%d');cmd.extend(['--date',b,'--days',str(max(1,(e-s).days+1))])
                except:pass
        if mo=='incr':cmd.extend(['--days',self.dv.get()])
        if dr:cmd.append('--dry-run')
        self.bb.configure(state='disabled');self.sb.configure(state='normal');self.sl.configure(text=' Running...',fg=AC)
        self.lg.delete('1.0','end');self._hide_res()
        def _d(b):
            try:return b.decode('utf-8')
            except:return b.decode('gbk',errors='replace')
        def run():
            try:
                self.proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                for ln in iter(self.proc.stdout.readline,b''):
                    for l in _d(ln).split('\n'):
                        l=l.strip()
                        if l:self._log(l)
                self.proc.wait()
                for l in _d(self.proc.stderr.read()).split('\n'):
                    l=l.strip()
                    if l:self._log('[stderr] '+l,'E')
                self.w.after(0,lambda:self._done(self.proc.returncode==0))
            except Exception as e:self.w.after(0,lambda:self._done_err(str(e)))
        threading.Thread(target=run,daemon=True).start()

    def _log(self,line,tag=None):
        if tag is None:
            if '===' in line or 'PMS ->' in line:tag='H'
            elif 'OK' in line or 'pass' in line:tag='S'
            elif 'skip' in line or 'WARN' in line:tag='W'
            elif 'fail' in line or 'ERROR' in line:tag='E'
            else:tag='D'
        self.lg.insert('end',line+'\n',tag);self.lg.see('end')

    def _done(self,ok):
        self.proc=None;self.bb.configure(state='normal');self.sb.configure(state='disabled');self.sl.configure(text=' Done' if ok else ' Failed',fg=GN if ok else RD)
    def _done_err(self,msg):self._log('Fatal: '+msg,'E');self._done(False)
    def _stop(self):
        if self.proc:
            try:self.proc.terminate()
            except:pass
        self._done(False)
    def _close(self):self._stop();self.w.destroy()
    def run(self):self.w.mainloop()

if __name__=='__main__':App().run()
