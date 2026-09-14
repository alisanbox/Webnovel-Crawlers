# =====================================================
# 69SHUBA.COM NOVEL CRAWLER — GUI VERSION 8.0
# © Credit: Ali Santoso
# ✅ ONE shared synopsis function: preview OR save
# ✅ Editable scrollable window → easy copy-paste
# ✅ Single URL, Status fixed, Full synopsis from .navtxt
# ✅ Config: crawler_config_69shuba.json
# =====================================================
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import webbrowser
import time
import random
import re
import threading
from datetime import datetime
import os
import json
try:
    from curl_cffi import requests
except ImportError:
    requests = None
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

ALI_SANTOSO_LINK = ""
CONFIG_FILE = "crawler_config_69shuba.json"
LOG_FILE = "logs.txt"
SEPARATOR = "=============================="

# =====================================================
# CORE HELPERS
# =====================================================
def get_novel_id(url):
    m = re.search(r"/(?:book|txt)/(\d+)/?", url)
    if m: return m.group(1)
    return "unknown"

def build_book_url(novel_id):
    """Convert Novel ID → Main Book Page URL"""
    return f"https://www.69shuba.com/book/{novel_id}.htm"

def ensure_output_folder(novel_id):
    folder = f"69shuba_{novel_id}"
    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder

def load_config():
    d = {
        "start_ch":"1","start_url":"","ch_count":"499","split_every":"100",
        "delay":"2-3","endless":False,"create_en":True,
        "window_w":820,"window_h":840,"window_x":100,"window_y":100
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE,"r",encoding="utf-8") as f:
                data = json.load(f)
                for k in ["window_w","window_h","window_x","window_y"]:
                    if k in data:
                        try: data[k] = int(data[k])
                        except: data[k] = d[k]
                d.update(data)
        except:pass
    return d

def save_config(data):
    try:
        with open(CONFIG_FILE,"w",encoding="utf-8") as f: json.dump(data,f,indent=2)
    except:pass

def write_log_file(text):
    ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE,"a",encoding="utf-8") as f: f.write(f"[{ts}] {text}\n")
    except:pass

# =====================================================
# ✅ ONE SHARED SYNOPSIS FUNCTION — Preview OR Save
# =====================================================
def fetch_synopsis_common(book_url, log_fn, save_to_file=False, output_folder=None):
    """Call with save_to_file=False → Preview only
       Call with save_to_file=True → Show + Save to file"""
    HEADERS={
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.8,*/*;q=0.8",
        "Accept-Language":"zh-CN,zh;q=0.9,en;q=0.8",
        "Referer":"https://www.69shuba.com/","DNT":"1"
    }
    try:
        log_fn(f"📖 Fetching synopsis: {book_url}")
        resp=requests.get(book_url, headers=HEADERS, impersonate="chrome131", timeout=30)
        if resp.status_code != 200:
            log_fn(f"⚠️ Synopsis page status: {resp.status_code}")
            return False
        resp.encoding="gbk"
        soup=BeautifulSoup(resp.text,"html.parser")
        info_text = soup.get_text()

        # --- Extract fields ---
        title = soup.find("h1")
        title = title.get_text(strip=True) if title else "Unknown Title"

        author_match = re.search(r"作者[：:]\s*([^\s\n]+)", info_text)
        author = author_match.group(1).strip() if author_match else "Unknown"

        # Status: extract ONLY "全本" or "连载"
        status_match = re.search(r"[\d.]+\s*万字\s*[｜|]\s*(\S+)", info_text)
        book_status = status_match.group(1).strip() if status_match else "Unknown"

        chapter_match = re.search(r"(\d+)章节数", info_text)
        chapter_count = chapter_match.group(1) if chapter_match else "Unknown"
        
        # Tags: extract from <script> bookinfo.tags → COMMA-SEPARATED format
        tags = ""  # ✅ Initialize FIRST
        raw_html = str(soup)
        
        # Pattern: find tags: 'xxx|yyy|zzz|' inside JavaScript
        tags_match = re.search(r"tags:\s*'([^']+)'", raw_html, re.S)
        if tags_match:
            pipe_separated = tags_match.group(1).strip()
            # Replace | with ", " → clean trailing comma
            tags = pipe_separated.replace('|', ', ').rstrip(', ')
        
        #log_fn(f"🔍 FINAL Tags found: [{tags}]")

        # Synopsis from <div class="navtxt"> — skip "小说关键词" line
        synopsis_div = soup.find("div", class_="navtxt")
        if synopsis_div:
            synopsis_lines = [l.strip() for l in synopsis_div.get_text("\n").split("\n")
                              if l.strip() and "小说关键词" not in l]
            synopsis_text = "\n".join(synopsis_lines).strip()
        else:
            synopsis_text = "Synopsis not found"

        # --- Build clean format: SINGLE URL only ---
        synopsis_content = f"""{book_url}

{title}

Author:{author}

{book_status}

Tags:{tags}

chapter:{chapter_count}

=== Synopsis ===
{synopsis_text}"""

        # --- ALWAYS show in editable scrollable window ---
        top = tk.Toplevel()
        top.title("📖 Novel Synopsis — Copy & Translate Easily")
        top.geometry("600x500")
        txt = scrolledtext.ScrolledText(top, wrap=tk.WORD, font=("Consolas", 10))
        txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        txt.insert("1.0", synopsis_content)
        txt.focus_set()
        ttk.Button(top, text="CLOSE", command=top.destroy).pack(pady=5)
        top.grab_set()

        # --- Save to file ONLY if flag = True ---
        if save_to_file and output_folder:
            novel_id = get_novel_id(book_url)
            synopsis_path = os.path.join(output_folder, f"synopsis_69shuba_{novel_id}.txt")
            with open(synopsis_path,"w",encoding="utf-8") as f:
                f.write(synopsis_content)
            log_fn(f"✅ Synopsis saved → {synopsis_path}")

        return True

    except Exception as e:
        log_fn(f"⚠️ Synopsis error: {e}")
        return False
# =====================================================
# MAIN CRAWLER GUI CLASS
# =====================================================
class NovelCrawlerGUI:
    def __init__(self,root):
        self.root=root
        self.cfg=load_config()
        w,h,x,y = (self.cfg[k] for k in ["window_w","window_h","window_x","window_y"])
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.title("69shuba.com Novel Crawler v8.0 — by Ali Santoso")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.running=False; self.paused=False; self.stop_flag=False
        self.pause_lock=threading.Condition()
        self.TEMP_FILE="_crawling_temp.txt"
        self.novel_id=None; self.output_folder=None

        # STATUS BAR
        status_frame=ttk.Frame(root); status_frame.pack(fill="x",padx=10,pady=3)
        self.status_canvas=tk.Canvas(status_frame,width=22,height=22,bg="#f0f0f0",highlightthickness=0)
        self.status_canvas.pack(side="left",padx=(0,8))
        self.status_indicator=self.status_canvas.create_oval(4,4,18,18,fill="#cc3333",outline="#991111")
        self.status_text=ttk.Label(status_frame,text="Status: Stopped"); self.status_text.pack(side="left")
        credit_label=ttk.Label(status_frame,text="© Ali Santoso",foreground="#0066cc",cursor="hand2")
        credit_label.pack(side="right"); credit_label.bind("<Button-1>",self.open_credit_link)

        # INPUTS — URL box SHRUNK + PREVIEW BUTTON beside it
        input_frame=ttk.LabelFrame(root,text="Crawl Settings"); input_frame.pack(fill="x",padx=10,pady=5)
        ttk.Label(input_frame,text="Start Chapter Number:").grid(row=0,column=0,sticky="w",padx=5,pady=3)
        self.start_ch_num=ttk.Entry(input_frame,width=12); self.start_ch_num.grid(row=0,column=1,sticky="w",padx=5,pady=3)
        self.start_ch_num.insert(0,self.cfg.get("start_ch","1"))

        ttk.Label(input_frame,text="Start Chapter URL:").grid(row=1,column=0,sticky="w",padx=5,pady=3)
        self.start_url=ttk.Entry(input_frame,width=60)
        self.start_url.insert(0,self.cfg.get("start_url",""))  # ✅ LOAD VALUE FIRST
        self.start_url.grid(row=1,column=1,padx=5,pady=3,sticky="w")  # ✅ THEN DRAW
        self.preview_btn=ttk.Button(input_frame,text="Preview Synopsis",command=self.preview_synopsis)
        self.preview_btn.grid(row=1,column=2,padx=5,pady=3)

        ttk.Label(input_frame,text="Chapters to Crawl:").grid(row=2,column=0,sticky="w",padx=5,pady=3)
        self.ch_count=ttk.Entry(input_frame,width=12); self.ch_count.grid(row=2,column=1,sticky="w",padx=5,pady=3)
        self.ch_count.insert(0,self.cfg.get("ch_count","499"))

        self.endless_mode=tk.BooleanVar(value=self.cfg.get("endless",False))
        ttk.Checkbutton(input_frame,text="Crawl until END",variable=self.endless_mode,command=self.toggle_endless).grid(row=2,column=1,sticky="w",padx=(120,5),pady=3)

        ttk.Label(input_frame,text="Split File Every:").grid(row=3,column=0,sticky="w",padx=5,pady=3)
        self.split_num=ttk.Entry(input_frame,width=12); self.split_num.grid(row=3,column=1,sticky="w",padx=5,pady=3)
        self.split_num.insert(0,self.cfg.get("split_every","100"))

        ttk.Label(input_frame,text="Delay Between Chapters:").grid(row=4,column=0,sticky="w",padx=5,pady=3)
        self.ch_delay=ttk.Entry(input_frame,width=12); self.ch_delay.grid(row=4,column=1,sticky="w",padx=5,pady=3)
        self.ch_delay.insert(0,self.cfg.get("delay","2-3"))

        # OPTIONS
        opt_frame=ttk.LabelFrame(root,text="Save Options"); opt_frame.pack(fill="x",padx=10,pady=5)
        self.create_en=tk.BooleanVar(value=self.cfg.get("create_en",True))
        ttk.Checkbutton(opt_frame,text="✅ Create EN empty files (.txt + .html)",variable=self.create_en).pack(anchor="w",padx=10,pady=3)
        ttk.Label(opt_frame,text="CN = always TXT only | EN = empty .txt + .html").pack(anchor="w",padx=10)

        # BUTTONS
        btn_frame=ttk.Frame(root); btn_frame.pack(fill="x",padx=10,pady=8)
        self.start_btn=ttk.Button(btn_frame,text="START CRAWL",command=self.start_process)
        self.start_btn.pack(side="left",padx=3)
        self.pause_btn=ttk.Button(btn_frame,text="PAUSE",command=self.toggle_pause,state="disabled")
        self.pause_btn.pack(side="left",padx=3)
        self.stop_btn=ttk.Button(btn_frame,text="STOP & SAVE",command=self.stop_process,state="disabled")
        self.stop_btn.pack(side="left",padx=3)
        self.clear_btn=ttk.Button(btn_frame,text="CLEAR LOG",command=self.clear_log)
        self.clear_btn.pack(side="right",padx=3)

        # PROGRESS
        prog_frame=ttk.LabelFrame(root,text="Progress & Estimated Time"); prog_frame.pack(fill="x",padx=10,pady=5)
        self.progress=ttk.Progressbar(prog_frame,length=780,mode="determinate"); self.progress.pack(pady=5)
        self.status_label=ttk.Label(prog_frame,text="Ready — Paste URL → Preview or START CRAWL")
        self.status_label.pack(anchor="w",padx=5)
        self.eta_label=ttk.Label(prog_frame,text="Estimated Time Remaining: --:--:--",font=("",10,"bold"))
        self.eta_label.pack(anchor="w",padx=5,pady=3)

        # LOG
        log_frame=ttk.LabelFrame(root,text="Log / Status"); log_frame.pack(fill="both",expand=True,padx=10,pady=5)
        self.log_box=scrolledtext.ScrolledText(log_frame,height=14,wrap="word")
        self.log_box.pack(fill="both",expand=True,padx=5,pady=5)
        self.log("v8.0 — Shared synopsis function ✅ | Editable window ✅ | Preview button ✅")

    # =====================================================
    # GUI HELPERS
    # =====================================================
    def on_close(self):
        try:
            geo = self.root.geometry()
            w,h,x,y = re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", geo).groups()
            self.cfg["window_w"]=int(w); self.cfg["window_h"]=int(h)
            self.cfg["window_x"]=int(x); self.cfg["window_y"]=int(y)
            save_config(self.cfg)
        except: pass
        self.root.destroy()

    def open_credit_link(self,event):
        if ALI_SANTOSO_LINK: webbrowser.open_new(ALI_SANTOSO_LINK); self.log(f"Opening link: {ALI_SANTOSO_LINK}")
        else: self.log("Link not set — edit ALI_SANTOSO_LINK at top")

    def toggle_endless(self):
        self.ch_count.config(state="disabled" if self.endless_mode.get() else "normal")

    def set_status(self,state):
        c={"running":"#33cc33","paused":"#ffcc00","blocked":"#ff6600"}
        self.status_canvas.itemconfig(self.status_indicator,fill=c.get(state,"#cc3333"))
        self.status_text.config(text=f"Status: {state.title()}"); self.root.update_idletasks()

    def toggle_pause(self):
        if not self.running: return
        with self.pause_lock:
            self.paused=not self.paused
            if self.paused: self.set_status("paused"); self.pause_btn.config(text="RESUME"); self.log("PAUSED")
            else: self.set_status("running"); self.pause_btn.config(text="PAUSE"); self.pause_lock.notify_all(); self.log("RESUMED")

    def check_pause(self):
        while self.paused and not self.stop_flag:
            with self.pause_lock: self.pause_lock.wait(0.5)

    def log(self,text):
        ts=datetime.now().strftime("%H:%M:%S"); line=f"[{ts}] {text}"
        self.log_box.insert("end",line+"\n"); self.log_box.see("end")
        write_log_file(text); self.root.update_idletasks()

    def update_eta(self,completed,total,avg_delay):
        if completed==0 or total==999999:
            self.eta_label.config(text="Estimated Time Remaining: Calculating...")
            return
        sec=int((total-completed)*avg_delay); h,m,s=sec//3600,(sec%3600)//60,sec%60
        self.eta_label.config(text=f"Estimated Time Remaining: {h:02d}:{m:02d}:{s:02d}")

    def update_status(self,text,pct=None):
        self.status_label.config(text=text)
        if pct is not None: self.progress["value"]=pct
        self.root.update_idletasks()

    # ✅ PREVIEW BUTTON → SHOW ONLY, NO SAVE
    def preview_synopsis(self):
        start_url=self.start_url.get().strip()
        if not start_url or "http" not in start_url:
            messagebox.showwarning("Warning","Paste Start Chapter URL first!"); return
        novel_id=get_novel_id(start_url)
        book_url=build_book_url(novel_id)
        fetch_synopsis_common(book_url, self.log, save_to_file=False)

    def clear_log(self): self.log_box.delete(1.0,"end")

    def save_temp_as_part(self,part_start,last_ch,top_url,create_en):
        if not os.path.exists(self.TEMP_FILE): self.log("No temp file — nothing to save"); return
        with open(self.TEMP_FILE,"r",encoding="utf-8") as f: content=f.read()
        css_line='<link href="txtstyle.css" rel="stylesheet" type="text/css" />'+"\n\n"
        cn_path=os.path.join(self.output_folder,f"CN_c{part_start}-{last_ch}.txt")
        with open(cn_path,"w",encoding="utf-8") as f: f.write(css_line+content)
        self.log(f"SAVED → {cn_path} ({os.path.getsize(cn_path)} bytes)")
        if create_en:
            en_txt_path=os.path.join(self.output_folder,f"EN_c{part_start}-{last_ch}.txt")
            en_html_path=os.path.join(self.output_folder,f"EN_c{part_start}-{last_ch}.html")
            try:
                with open(en_txt_path,"w",encoding="utf-8"): pass
            except:
                with open(en_txt_path,"w",encoding="utf-8") as f: f.write(" ")
            try:
                with open(en_html_path,"w",encoding="utf-8"): pass
            except:
                with open(en_html_path,"w",encoding="utf-8") as f: f.write(" ")
            self.log(f"CREATED → {en_txt_path} (EMPTY 0 bytes)")
            self.log(f"CREATED → {en_html_path} (EMPTY 0 bytes)")
        os.remove(self.TEMP_FILE); self.log("Temp file cleared\n")

    def stop_process(self):
        if not self.running: return
        self.log("STOP requested — SAVING PROGRESS...")
        self.stop_flag=True; self.paused=False
        with self.pause_lock: self.pause_lock.notify_all()

    def parse_delay(self,s):
        try:
            if '-' in s: a,b=s.split('-'); return float(a.strip()),float(b.strip())
            n=float(s.strip()); return n,n
        except: return 2.0,3.0

    def temp_append(self,top_url,ch_title,ch_content):
        entry=f"{SEPARATOR}\n{ch_title}\n{ch_content}\n\n"
        if not os.path.exists(self.TEMP_FILE) or os.path.getsize(self.TEMP_FILE)==0:
            with open(self.TEMP_FILE,"w",encoding="utf-8") as f: f.write(top_url+"\n\n"+entry)
        else:
            with open(self.TEMP_FILE,"a",encoding="utf-8") as f: f.write(entry)

    def clean_text(self,text,ch_title):
        skip=["加入书架","上一章","下一章","返回目录","无弹窗","本章完","作者：","2023-12-","2023-10-"]
        lines=[l.strip() for l in text.split("\n") if l.strip() and not any(p in l for p in skip) and len(l.strip())>3]
        if lines and lines[0] == ch_title:
            lines = lines[1:]
        return "\n".join(lines)

    def get_chapter_with_retry(self,url):
        HEADERS={
            "Accept":"text/html,application/xhtml+xml,application/xml;q=0.8,*/*;q=0.8",
            "Accept-Language":"zh-CN,zh;q=0.9,en;q=0.8",
            "Referer":"https://www.69shuba.com/","DNT":"1"
        }
        attempt=0
        while not self.stop_flag:
            attempt+=1
            try:
                resp=requests.get(url,headers=HEADERS,impersonate="chrome131",timeout=30)
                if resp.status_code==403:
                    self.set_status("blocked"); wait=min(30*attempt,120)
                    self.log(f"CLOUDFLARE — wait {wait}s...")
                    for _ in range(wait*2):
                        if self.stop_flag: return None,None,None
                        self.check_pause(); time.sleep(0.5)
                    continue
                if resp.status_code!=200:
                    self.log(f"Status {resp.status_code} — retry in 5s...")
                    for _ in range(10):
                        if self.stop_flag: return None,None,None
                        self.check_pause(); time.sleep(0.5)
                    continue
                resp.encoding="gbk"; soup=BeautifulSoup(resp.text,"html.parser")
                title_tag=soup.find("h1"); title=title_tag.get_text(strip=True) if title_tag else ""
                title=re.sub(r"^\d+\.","",title).strip()
                content_div=soup.find("div",class_="txtnav"); content=""
                if content_div:
                    for ad in content_div.select(".page1, .tools, script, .ad"): ad.decompose()
                    content=content_div.get_text("\n").strip()
                if not title or len(title)<2 or not content or len(content)<20:
                    self.log("EMPTY CONTENT → REACHED END OF NOVEL!"); return None,None,None
                next_link=None
                for a in soup.select("a"):
                    t=a.get_text(strip=True)
                    if "下一章" in t and a.get("href"):
                        next_link=a["href"]
                        if not next_link.startswith("http"): next_link="https://www.69shuba.com"+next_link
                        break
                self.set_status("running"); return title,content,next_link
            except Exception as e:
                self.log(f"Error: {e} — retry in 5s...")
                for _ in range(10):
                    if self.stop_flag: return None,None,None
                    self.check_pause(); time.sleep(0.5)
        return None,None,None
    # =====================================================
    # MAIN CRAWL THREAD — SYNOPSIS FIRST + SAVE TO FILE
    # =====================================================
    def crawl_thread(self,start_ch_num,start_url,ch_count,split_every,delay_min,delay_max,endless,create_en):
        avg_delay=(delay_min+delay_max)/2; self.log(f"Delay: {delay_min:.1f}-{delay_max:.1f}s\n")

        # ✅ START CRAWL → SHOW SYNOPSIS + SAVE TO FILE
        self.novel_id=get_novel_id(start_url)
        self.output_folder=ensure_output_folder(self.novel_id)
        book_url=build_book_url(self.novel_id)
        fetch_synopsis_common(book_url, self.log, save_to_file=True, output_folder=self.output_folder)

        if os.path.exists(self.TEMP_FILE): os.remove(self.TEMP_FILE); self.log("Cleared old temp file")
        part_start=start_ch_num; part_top_url=start_url; current_url=start_url; completed=0
        end_ch_num=start_ch_num+ch_count-1; last_success_ch=start_ch_num-1

        while current_url and completed<ch_count and not self.stop_flag:
            self.check_pause(); ch_num=start_ch_num+completed; t0=time.time()
            if not endless and ch_count<999999:
                pct=int((completed/ch_count)*100)
                self.update_eta(completed,ch_count,avg_delay)
                self.update_status(f"Ch{ch_num}/{end_ch_num} downloading...",pct)
            else:
                self.eta_label.config(text="Estimated Time Remaining: ∞")
                self.update_status(f"Ch{ch_num} downloading...",0)

            self.log(f"[{ch_num}] Fetching...")
            title,content,next_url=self.get_chapter_with_retry(current_url)

            if not title or not content:
                reason="USER STOPPED" if self.stop_flag else "REACHED END OF NOVEL"
                self.log(f"{reason} at Ch{last_success_ch} → SAVING...")
                self.save_temp_as_part(part_start,last_success_ch,part_top_url,create_en)
                self.update_status(f"✅ ALL DONE! {last_success_ch} chapters saved",100)
                self.log(f"DONE! Files saved to: {self.output_folder}/\n")
                self.finish_process(); return

            cleaned=self.clean_text(content,title)
            self.temp_append(part_top_url,title,cleaned); last_success_ch=ch_num
            self.log(f"  Saved to temp | Time: {time.time()-t0:.1f}s")
            completed+=1

            if not endless and ch_count<999999:
                pct=int((completed/ch_count)*100)
                self.update_status(f"Ch{ch_num}/{end_ch_num} saved",pct)

            if (ch_num-part_start+1)>=split_every:
                self.save_temp_as_part(part_start,ch_num,part_top_url,create_en)
                part_start=ch_num+1; part_top_url=next_url

            current_url=next_url
            if current_url and completed<ch_count and not self.stop_flag:
                wait=random.uniform(delay_min,delay_max); self.log(f"  Waiting {wait:.1f}s..."); time.sleep(wait)

        if self.stop_flag: self.log(f"USER STOPPED at Ch{last_success_ch} → SAVING...")
        self.save_temp_as_part(part_start,last_success_ch,part_top_url,create_en)
        self.update_status(f"✅ ALL DONE! {last_success_ch} chapters saved",100)
        self.log(f"ALL DONE! {last_success_ch} chapters saved to: {self.output_folder}/")
        self.finish_process()

    # =====================================================
    # START / FINISH
    # =====================================================
    def start_process(self):
        if self.running: return
        if not requests or not BeautifulSoup:
            messagebox.showerror("Missing Library","Run:\npip install curl_cffi beautifulsoup4"); return

        start_ch=self.start_ch_num.get().strip(); start_url=self.start_url.get().strip()
        split_every=self.split_num.get().strip(); delay_str=self.ch_delay.get().strip()
        endless=self.endless_mode.get(); create_en=self.create_en.get()

        if not start_url or "http" not in start_url:
            messagebox.showwarning("Warning","Paste Start Chapter URL first!"); return

        try:
            start_ch=int(start_ch); split_every=int(split_every)
            delay_min,delay_max=self.parse_delay(delay_str)
            ch_count=999999 if endless else int(self.ch_count.get().strip())
            if ch_count<1: raise ValueError()
        except: messagebox.showerror("Error","All numbers must be valid integers ≥ 1!"); return

        save_config({"start_ch":str(start_ch),"start_url":start_url,"ch_count":"499" if ch_count==999999 else str(ch_count),"split_every":str(split_every),"delay":delay_str,"endless":endless,"create_en":create_en})
        self.log("Settings saved\n")

        self.running=True; self.stop_flag=False; self.paused=False; self.set_status("running")
        self.start_btn.config(state="disabled"); self.pause_btn.config(state="normal"); self.stop_btn.config(state="normal"); self.progress["value"]=0

        threading.Thread(target=self.crawl_thread,args=(start_ch,start_url,ch_count,split_every,delay_min,delay_max,endless,create_en),daemon=True).start()

    def finish_process(self):
        self.running=False; self.paused=False; self.set_status("stopped")
        self.eta_label.config(text="Estimated Time Remaining: --:--:--")
        self.start_btn.config(state="normal"); self.pause_btn.config(state="disabled"); self.stop_btn.config(state="disabled")

# =====================================================
# LAUNCH
# =====================================================
if __name__=="__main__":
    try: root=tk.Tk(); app=NovelCrawlerGUI(root); root.mainloop()
    except Exception as e:
        print("-"*50); print("GUI FAILED TO START:"); print(str(e)); print("-"*50); input("Press Enter to close...")