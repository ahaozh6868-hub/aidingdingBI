#!/usr/bin/env python3
"""PMS Sync Panel - Native Desktop GUI (Tkinter, zero-dependency)"""
import sys, os, json, subprocess, threading, datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MP = getattr(sys, '_MEIPASS', '')
SYNC_SCRIPT = next((p for p in [
    os.path.join(MP, 'pms_sync.py'),
    os.path.join(SCRIPT_DIR, 'NewScripts', 'pms_sync.py'),
    os.path.join(SCRIPT_DIR, 'pms_sync.py'),
] if os.path.isfile(p)), 'pms_sync.py')

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

BG='#0d1117';FG='#c9d1d9';DM='#8b949e';AC='#3b82f6';GR='#10b981';RD='#ef4444'
AM='#f59e0b';LBG='#0a0e14';LBD='#1a2332'

class PanelApp:
    def __init__(self):
        self.w=tk.Tk()
        self.w.title("PMS Sync Panel v3")
        self.w.geometry("780x680");self.w.minsize(640,520)
        self.w.configure(bg=BG)
        self.proc=None
        self._build()
        self.w.protocol("WM_DELETE_WINDOW",self._close)

    def _build(self):
        c=tk.Frame(self.w,bg=BG);c.pack(fill='both',expand=True,padx=18,pady=18)
        h=tk.Frame(c,bg=BG);h.pack(fill='x',pady=(0,16))
        tk.Label(h,text="PMS Sync Panel",font=('',16,'bold'),fg='#e2e8f0',bg=BG).pack(side='left')
        tk.Label(h,text="v3  Alashan 152",fg=DM,bg=BG,font=('',9)).pack(side='left',padx=10)
        tk.Label(c,text="Token",fg=DM,bg=BG,font=('',10,'bold')).pack(anchor='w')
        ft=tk.Frame(c,bg=BG);ft.pack(fill='x',pady=(4,16))
        self.tv=tk.StringVar(value=os.environ.get('PMS_TOKEN',''))
        self.ti=tk.Entry(ft,textvariable=self.tv,font=('Consolas',10),bg=LBG,fg=FG,insertbackground=FG,relief='flat',highlightthickness=1,highlightbackground=LBD,highlightcolor=AC)
        self.ti.pack(fill='x',ipady=5);self.ti.focus()
        tk.Label(c,text="Mode",fg=DM,bg=BG,font=('',10,'bold')).pack(anchor='w')
        fm=tk.Frame(c,bg=BG);fm.pack(fill='x',pady=6)
        self.mv=tk.StringVar(value='incr')
        for v,t in [('incr','Daily'),('full','Full'),('date','Date'),('range','Range')]:
            ttk.Radiobutton(fm,text=t,value=v,variable=self.mv,command=self._on_mode).pack(side='left',padx=(0,14))
        self.mx=tk.Frame(c,bg=BG);self.mx.pack(fill='x',pady=(0,6))
        self.dv=tk.StringVar(value='3');self.ds=ttk.Spinbox(self.mx,from_=1,to=90,width=5,textvariable=self.dv)
        self.dv_date=tk.StringVar(value=datetime.date.today().strftime('%Y-%m-%d'))
        self.di=tk.Entry(self.mx,textvariable=self.dv_date,width=13,font=('',10),bg=LBG,fg=FG,relief='flat',highlightthickness=1,highlightbackground=LBD,highlightcolor=AC)
        self.rf=tk.Entry(self.mx,width=13,font=('',10),bg=LBG,fg=FG,relief='flat',highlightthickness=1,highlightbackground=LBD,highlightcolor=AC)
        self.rt=tk.Entry(self.mx,width=13,font=('',10),bg=LBG,fg=FG,relief='flat',highlightthickness=1,highlightbackground=LBD,highlightcolor=AC)
        self._on_mode()
        self.dr=tk.BooleanVar()
        ttk.Checkbutton(c,text="Dry-Run (preview only, no write)",variable=self.dr).pack(anchor='w',pady=(4,6))
        fb=tk.Frame(c,bg=BG);fb.pack(fill='x',pady=(10,16))
        self.bb=tk.Button(fb,text="Start Sync",command=self._start,bg=AC,fg='#fff',font=('',11,'bold'),relief='flat',activebackground='#2563eb',activeforeground='#fff',padx=20,pady=6,cursor='hand2');self.bb.pack(side='left')
        self.sb=tk.Button(fb,text="Stop",command=self._stop,state='disabled',bg='#1f2937',fg=RD,font=('',11),relief='flat',padx=16,pady=6);self.sb.pack(side='left',padx=8)
        self.sl=tk.Label(fb,text=" Ready",fg=DM,bg=BG,font=('',10));self.sl.pack(side='left',padx=16)
        tk.Label(c,text="Execution Log",fg=DM,bg=BG,font=('',10,'bold')).pack(anchor='w')
        self.lg=scrolledtext.ScrolledText(c,height=16,bg=LBG,fg=FG,insertbackground=FG,font=('Cascadia Code',9),relief='flat',borderwidth=1,highlightthickness=1,highlightbackground=LBD)
        self.lg.pack(fill='both',expand=True,pady=(4,0))
        for tag,color in [('H','#60a5fa'),('S',GR),('W',AM),('E',RD),('D','#4b5563')]:
            self.lg.tag_config(tag,foreground=color)
        self.lg.tag_config('H',font=('Cascadia Code',9,'bold'))
        self.lg.insert('end','Ready.\n','D')

    def _on_mode(self):
        m=self.mv.get()
        for w in self.mx.winfo_children():w.pack_forget()
        if m=='incr':
            tk.Label(self.mx,text="Last  ",fg=DM,bg=BG,font=('',9)).pack(side='left')
            self.ds.pack(side='left',padx=2)
            tk.Label(self.mx,text="  days",fg=DM,bg=BG,font=('',9)).pack(side='left')
        elif m=='date':
            tk.Label(self.mx,text="Date  ",fg=DM,bg=BG,font=('',9)).pack(side='left')
            self.di.pack(side='left')
        elif m=='range':
            self.rf.pack(side='left',padx=(0,4))
            tk.Label(self.mx,text=" -> ",fg=DM,bg=BG,font=('',9)).pack(side='left')
            self.rt.pack(side='left',padx=(4,0))

    def _start(self):
        tk_=self.tv.get().strip()
        if not tk_:messagebox.showwarning("Token","Please enter PMS Bearer token.");return
        if not tk_.lower().startswith('bearer '):tk_='Bearer '+tk_
        mo=self.mv.get();dr=self.dr.get()
        # PyInstaller exe: 同目录找 pms_sync.exe；开发环境用 python
        if getattr(sys,'frozen',False):
            sync_exe = os.path.join(SCRIPT_DIR,'pms_sync.exe')
            cmd = [sync_exe,'--token',tk_]
        else:
            cmd = [sys.executable,SYNC_SCRIPT,'--token',tk_]
        if mo=='full':cmd.append('--full')
        elif mo=='date':cmd.extend(['--date',self.dv_date.get(),'--days','1'])
        elif mo=='range':
            a=self.rf.get().strip();b=self.rt.get().strip()
            if a and b:
                try:
                    s=datetime.datetime.strptime(a,'%Y-%m-%d');e=datetime.datetime.strptime(b,'%Y-%m-%d')
                    cmd.extend(['--date',b,'--days',str(max(1,(e-s).days+1))])
                except:pass
        if mo=='incr':cmd.extend(['--days',self.dv.get()])
        if dr:cmd.append('--dry-run')
        self.bb.configure(state='disabled');self.sb.configure(state='normal')
        self.sl.configure(text=' Running...',fg=AC);self.lg.delete('1.0','end')
        def _dec(b):
            try:return b.decode('utf-8')
            except:return b.decode('gbk',errors='replace')
        def run():
            try:
                self.proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                for line in iter(self.proc.stdout.readline,b''):
                    for l in _dec(line).split('\n'):
                        l=l.strip()
                        if l:self._log(l)
                self.proc.wait()
                for l in _dec(self.proc.stderr.read()).split('\n'):
                    l=l.strip()
                    if l:self._log('[stderr] '+l,'E')
                self.w.after(0,lambda:self._done(self.proc.returncode==0))
            except Exception as e:
                self.w.after(0,lambda:self._done_err(str(e)))
        threading.Thread(target=run,daemon=True).start()

    def _log(self,line,tag=None):
        if tag is None:
            if '===' in line or 'PMS ->' in line:tag='H'
            elif 'pass' in line or 'OK' in line:tag='S'
            elif 'skip' in line or 'WARN' in line:tag='W'
            elif 'fail' in line or 'err' in line or 'ERROR' in line:tag='E'
            else:tag='D'
        self.lg.insert('end',line+'\n',tag);self.lg.see('end')

    def _done(self,ok):
        self.proc=None
        self.bb.configure(state='normal');self.sb.configure(state='disabled')
        self.sl.configure(text=' Done' if ok else ' Failed',fg=GR if ok else RD)
    def _done_err(self,msg):
        self._log('Fatal: '+msg,'E');self._done(False)
    def _stop(self):
        if self.proc:
            try:self.proc.terminate()
            except:pass
        self._done(False)
    def _close(self):self._stop();self.w.destroy()
    def run(self):self.w.mainloop()

if __name__=='__main__':
    PanelApp().run()
