# =====================================================
#       SYOSETU.COM NOVEL CRAWLER — GUI VERSION 2.9
#               © Credit: Ali Santoso
# =====================================================
# ✅ RENAMED: CN → JP (Japanese) everywhere ✅
# ✅ FIXED: Split every — NOW PROPERLY SAVES & LOADS YOUR INPUT ✅
# ✅ FORMAT FIX: JP_c1-3.txt (removed extra "c" before end number) ✅
# ✅ ADDED: Novel URL at TOP of Synopsis file ✅
# ✅ Synopsis — id="novel_ex" pattern ✅
# ✅ No warnings — flags= keyword ✅
# ✅ EN files = EMPTY 0-byte (TXT + HTML) ✅
# ✅ CSS Header at TOP of JP files ✅
# =====================================================

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import time
import random
import re
import threading
from datetime import datetime, timedelta
import os
import json

try:
    from curl_cffi.requests import Session
    HAS_CURL_CFFI = True
except ImportError:
    Session = None
    HAS_CURL_CFFI = False

CONFIG_FILE = "syosetu_config.json"
LOG_FILE = "syosetu_logs.txt"
CSS_HEADER = '<link href="txtstyle.css" rel="stylesheet" type="text/css" />\n\n'

def write_log(text):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {text}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except: pass
    return line

def load_config():
    d = {"delay_min":2.0, "delay_max":4.0, "split_every":100, "create_en":True, "save_mode":"merge",
         "window_w":820, "window_h":880, "window_x":100, "window_y":100}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k in d:
                    if k in data: d[k] = data[k]
        except: pass
    return d

def save_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except: pass

def extract_ncode(url):
    m = re.search(r"(n\d+[a-z]+)/?", url, re.I)
    return m.group(1) if m else None

def get_domain_type(url):
    return "novel18" if "novel18." in url else "ncode"

def get_base_domain(url):
    return "https://novel18.syosetu.com" if "novel18." in url else "https://ncode.syosetu.com"

ses = None
def get_session():
    global ses
    if ses is None and HAS_CURL_CFFI:
        ses = Session(impersonate="chrome")
        ses.cookies.set("over18", "yes", domain=".syosetu.com")
        write_log("✅ Age-confirmation cookie set automatically")
    return ses

def fetch_page(url):
    ses = get_session()
    if not ses: return None, "Session not available"
    resp = ses.get(url, timeout=30)
    if resp.status_code != 200: return resp.status_code, resp.text
    if "年齢確認" in resp.text:
        ses.cookies.set("over18", "yes", domain="novel18.syosetu.com")
        resp = ses.get(url, timeout=30)
    return resp.status_code, resp.text

def parse_novel_info(html, domain_type):
    info = {"title":"", "author":"", "author_link":"", "status":"Unknown", "synopsis":"", "total_chapters":0}

    m = re.search(r'<h1 class="p-novel__title">([^<]+)</h1>', html, re.I)
    if not m: m = re.search(r'<title>([^<\n]+?)[ \-|]*(?:小説|novel)</title>', html, re.I)
    if m: info["title"] = m.group(1).strip()

    m = re.search(r'<div\s+class="p-novel__author">作者：([^<]+)</div>', html, re.S|re.I)
    if m:
        info["author"] = m.group(1).strip()
    else:
        patterns_author = [
            r'<div\s+class="p-novel__author">作者：<a[^>]*href="(https://(x)?mypage\.syosetu\.com/[^"]+)"[^>]*>([^<]+)</a>',
        ]
        for pat in patterns_author:
            m = re.search(pat, html, re.S|re.I)
            if m:
                info["author_link"] = m.group(1)
                raw_name = m.group(3).strip()
                raw_name = re.sub(r"作者|マイページ|／.*$", "", raw_name).strip()
                if raw_name and len(raw_name) > 1 and not info["author"]:
                    info["author"] = raw_name
                break

        m = re.search(r'href="(https://(x)?mypage\.syosetu\.com/[^"]+)"', html, re.I)
        if m: info["author_link"] = m.group(1).rstrip("/") + "/"

    patterns_syn = [
        r'<div\s+id="novel_ex"[^>]*class="[^"]*p-novel__summary[^"]*"[^>]*>(.*?)</div>',
        r'<div\s+id="novel_ex"[^>]*>(.*?)</div>',
        r'<div\s+class="p-novel__summary"[^>]*>(.*?)</div>',
        r'あらすじ[\s：:]*(.*?)(?:<div|<h2|<p)',
    ]
    for pat in patterns_syn:
        m = re.search(pat, html, re.S|re.I)
        if m:
            text = m.group(1)
            text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
            text = re.sub(r"</?p[^>]*>", "\n", text, flags=re.I)
            text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.S|re.I)
            text = re.sub(r"<[^>]+>", "", text)
            text = text.replace("&nbsp;"," ").replace("&amp;","&").strip()
            if len(text) > 5:
                info["synopsis"] = text
                break

    info["status"] = "Completed" if re.search(r"完結済|完結", html) else "Ongoing"
    return info

def parse_toc_page(html, domain_type):
    chapters = []
    items = re.findall(r'<a[^>]*href="(/n\d+[a-z]+/(\d+)/)"[^>]*>([^<]{3,})</a>', html, re.I)
    for link, num, title in items:
        chapters.append({"num": int(num), "link": link, "title": title.strip()})
    next_match = re.search(r'<a[^>]*href="([^"]+)"[^>]*>(次へ|≫)</a>', html, re.I)
    return chapters, next_match.group(1) if next_match else None

def parse_chapter_content(html, domain_type):
    title = "Chapter"
    for pat in [
        r'<h3 class="p-novel__subtitle">([^<]+)</h3>',
        r'<p class="p-novel__subtitle">([^<]+)</p>',
    ]:
        m = re.search(pat, html, re.I)
        if m:
            title = m.group(1).strip()
            break

    body = ""
    m = re.search(r'class="p-novel__text">(.*?)</div>', html, re.S|re.I)
    if not m:
        m = re.search(r'p-novel__text["\s>]+>(.*?)$', html, re.S|re.I)
    if m:
        raw = m.group(1)
        raw = re.sub(r"<br\s*/?>", "\n", raw, flags=re.I)
        raw = re.sub(r"</?p\s*>", "\n", raw, flags=re.I)
        raw = re.sub(r"<script[^>]*>.*?</script>", "", raw, flags=re.S|re.I)
        raw = re.sub(r"<[^>]+>", "", raw)
        body = raw.replace("&nbsp;"," ").replace("&amp;","&").replace("&lt;","<").replace("&gt;",">").strip()
    return title, body

class SyosetuCrawlerGUI:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.ncode = ""
        self.folder_path = ""
        w,h,x,y = (self.cfg[k] for k in ["window_w","window_h","window_x","window_y"])
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.title("Syosetu Crawler v2.9 — by Ali Santoso")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.running = self.paused = self.stop_flag = False
        self.chapters = []
        self.novel_info = {}
        self.base_url = self.domain_type = self.base_domain = ""

        f_top = ttk.LabelFrame(root, text="🔍 Step 1: Paste Novel URL & Fetch Info")
        f_top.pack(fill="x", padx=10, pady=5)
        ttk.Label(f_top, text="URL:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.url_entry = ttk.Entry(f_top, width=70)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.url_entry.insert(0, "https://novel18.syosetu.com/n6382hq/")
        self.url_entry.bind("<Return>", lambda e: self.fetch_info())
        self.fetch_btn = ttk.Button(f_top, text="📋 Fetch Novel Info", command=self.fetch_info)
        self.fetch_btn.grid(row=0, column=2, padx=5, pady=5)
        f_top.grid_columnconfigure(1, weight=1)

        f_info = ttk.LabelFrame(root, text="📖 Novel Information")
        f_info.pack(fill="x", padx=10, pady=5)
        self.info_text = tk.Text(f_info, height=6, wrap="word", state="disabled")
        self.info_text.pack(fill="x", padx=5, pady=5)

        f_set = ttk.LabelFrame(root, text="⚙️ Step 2: Download Settings")
        f_set.pack(fill="x", padx=10, pady=5)
        ttk.Label(f_set, text="Start Ch:").grid(row=0, column=0, padx=5, pady=3, sticky="w")
        self.start_ch = ttk.Entry(f_set, width=8)
        self.start_ch.insert(0, "1")
        self.start_ch.grid(row=0, column=1, padx=5, pady=3)
        ttk.Label(f_set, text="End Ch:").grid(row=0, column=2, padx=5, pady=3, sticky="w")
        self.end_ch = ttk.Entry(f_set, width=8)
        self.end_ch.grid(row=0, column=3, padx=5, pady=3)
        ttk.Label(f_set, text="Split every:").grid(row=0, column=4, padx=5, pady=3, sticky="w")
        self.split_entry = ttk.Entry(f_set, width=8)
        self.split_entry.insert(0, str(self.cfg.get("split_every", 100)))
        self.split_entry.grid(row=0, column=5, padx=5, pady=3)

        ttk.Label(f_set, text="Delay min:").grid(row=1, column=0, padx=5, pady=3, sticky="w")
        self.delay_min = ttk.Entry(f_set, width=8)
        self.delay_min.insert(0, str(self.cfg.get("delay_min", 2.0)))
        self.delay_min.grid(row=1, column=1, padx=5, pady=3)
        ttk.Label(f_set, text="max:").grid(row=1, column=2, padx=0, pady=3, sticky="e")
        self.delay_max = ttk.Entry(f_set, width=8)
        self.delay_max.insert(0, str(self.cfg.get("delay_max", 4.0)))
        self.delay_max.grid(row=1, column=3, padx=5, pady=3)

        self.save_mode_var = tk.StringVar(value=self.cfg.get("save_mode","merge"))
        ttk.Radiobutton(f_set, text="Merge & Split", variable=self.save_mode_var, value="merge").grid(row=2, column=0, columnspan=3, padx=5, pady=3, sticky="w")
        ttk.Radiobutton(f_set, text="Individual files", variable=self.save_mode_var, value="individual").grid(row=2, column=3, columnspan=4, padx=5, pady=3, sticky="w")

        self.create_en_var = tk.BooleanVar(value=self.cfg.get("create_en",True))
        ttk.Checkbutton(f_set, text="Create EMPTY EN files (Merge only)", variable=self.create_en_var).grid(row=3, column=0, columnspan=6, padx=5, pady=3, sticky="w")

        f_btn = ttk.Frame(root)
        f_btn.pack(fill="x", padx=10, pady=5)
        self.run_btn = ttk.Button(f_btn, text="▶ START DOWNLOAD", command=self.start_crawl)
        self.run_btn.pack(side="left", padx=5)
        self.pause_btn = ttk.Button(f_btn, text="⏸ PAUSE", command=self.pause_crawl, state="disabled")
        self.pause_btn.pack(side="left", padx=5)
        self.stop_btn = ttk.Button(f_btn, text="■ STOP", command=self.stop_crawl, state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        self.status_light = tk.Label(f_btn, text="●", fg="gray", font=("",14))
        self.status_light.pack(side="right", padx=15)

        f_prog = ttk.LabelFrame(root, text="📊 Progress")
        f_prog.pack(fill="x", padx=10, pady=5)
        self.prog_bar = ttk.Progressbar(f_prog, length=780, mode="determinate")
        self.prog_bar.pack(fill="x", padx=5, pady=3)
        self.status_label = ttk.Label(f_prog, text="Ready — Paste URL, press Enter or click Fetch")
        self.status_label.pack(anchor="w", padx=5, pady=2)
        self.eta_label = ttk.Label(f_prog, text="Estimated time remaining: --:--:--")
        self.eta_label.pack(anchor="w", padx=5, pady=1)

        f_log = ttk.LabelFrame(root, text="📋 Log")
        f_log.pack(fill="both", expand=True, padx=10, pady=5)
        self.log_box = scrolledtext.ScrolledText(f_log, height=8, wrap="word", state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=5, pady=5)

        self.url_entry.focus_set()
        write_log("Syosetu Crawler v2.9 — URL at TOP of Synopsis ✅")

    def set_light(self, color):
        self.status_light.config(fg={"red":"red","yellow":"orange","green":"green"}.get(color,"gray"))

    def log_line(self, text):
        line = write_log(text)
        self.log_box.config(state="normal")
        self.log_box.insert("end", line)
        self.log_box.see("end")
        self.log_box.config(state="disabled")
        self.root.update_idletasks()

    def update_status(self, text):
        self.status_label.config(text=text)
        self.root.update_idletasks()

    def fetch_info(self):
        url = self.url_entry.get().strip()
        if not url: messagebox.showwarning("Warning", "Enter URL first!"); return
        if not HAS_CURL_CFFI: messagebox.showerror("Error", "curl_cffi not installed!"); return
        self.fetch_btn.config(state="disabled")
        self.set_light("green")
        threading.Thread(target=self._fetch_task, args=(url,), daemon=True).start()

    def _fetch_task(self, url):
        try:
            self.log_line("🔍 Fetching Novel Info...")
            self.base_url = url.split("?")[0].rstrip("/") + "/"
            self.domain_type = get_domain_type(url)
            self.base_domain = get_base_domain(url)
            self.ncode = extract_ncode(url)
            self.log_line(f"   ✅ n-code: {self.ncode}")

            self.folder_path = f"syosetu_{self.ncode}"
            os.makedirs(self.folder_path, exist_ok=True)
            self.log_line(f"   📁 Folder: {self.folder_path}/")

            code, html = fetch_page(self.base_url)
            if code != 200: raise ValueError(f"Page load failed: Status {code}")

            info = parse_novel_info(html, self.domain_type)
            self.novel_info = info
            self.log_line(f"   ✅ Title: {info['title']}")
            self.log_line(f"   ✅ Author: {info['author'] or '(Not found)'}")
            self.log_line(f"   ✅ Author Link: {info['author_link'] or '(Not found)'}")
            if info['synopsis']:
                self.log_line(f"   ✅ SYNOPSIS FOUND! {len(info['synopsis'])} chars")
            else:
                self.log_line("   ❌ Synopsis: Not found")

            if not info["title"] or "年齢確認" in info["title"]:
                raise ValueError("❌ Still on age-verification page!")

            toc_chapters, next_url = parse_toc_page(html, self.domain_type)
            all_chapters = toc_chapters[:]
            page_num = 2
            while next_url:
                self.log_line(f"   📄 Loading TOC page {page_num}...")
                if not next_url.startswith("http"): next_url = self.base_domain + next_url
                c, h = fetch_page(next_url)
                if c != 200: break
                chs, next_url = parse_toc_page(h, self.domain_type)
                all_chapters.extend(chs)
                page_num += 1
                time.sleep(0.5)

            all_chapters.sort(key=lambda x: x["num"])
            self.chapters = all_chapters
            self.log_line(f"✅ FOUND {len(all_chapters)} CHAPTERS!")

            toc_text_list = [f"Ch{ch['num']:03d}. {ch['title']}" for ch in all_chapters]
            toc_full = "\n".join(toc_text_list)

            display = f"""📌 Title: {info['title']}
✍ Author: {info['author'] or '(Not found)'}
🔗 Author Link: {info['author_link'] or '(Not found)'}
📚 Total Chapters: {len(all_chapters)}
🚦 Status: {info['status']}

📝 Synopsis:
{info['synopsis'] or '(Not found)'}

📋 TOC:
{toc_full}
"""
            self.info_text.config(state="normal")
            self.info_text.delete("1.0", "end")
            self.info_text.insert("1.0", display)
            self.info_text.config(state="disabled")

            syn_filename = os.path.join(self.folder_path, f"Synopsis_{self.ncode}.txt")
            with open(syn_filename, "w", encoding="utf-8") as f:
                # ✅ === ADDED: Write novel URL FIRST, before everything ===
                f.write(f"{self.base_url}\n\n")
                f.write(f"Title: {info['title']}\n")
                f.write(f"Author: {info['author'] or '(Not found)'}\n")
                f.write(f"Author Link: {info['author_link'] or '(Not found)'}\n")
                f.write(f"Chapters: {len(all_chapters)}\n")
                f.write(f"Status: {info['status']}\n\n")
                f.write("=== SYNOPSIS ===\n")
                f.write(info['synopsis'] or '(Not found)')
                f.write("\n\n=== TOC ===\n")
                f.write(toc_full)
                f.write("\n")
            self.log_line(f"💾 Saved → {syn_filename}")

            if all_chapters:
                self.end_ch.delete(0, "end")
                self.end_ch.insert(0, str(all_chapters[-1]["num"]))

        except Exception as e:
            import traceback
            self.log_line(f"❌ Error: {e}")
            self.log_box.config(state="normal")
            self.log_box.insert("end", f"--- Debug ---\n{traceback.format_exc()}\n-----------\n")
            self.log_box.config(state="disabled")
            messagebox.showerror("Error", str(e))
        finally:
            self.fetch_btn.config(state="normal")
            self.set_light("gray")

    def start_crawl(self):
        if not self.chapters: messagebox.showwarning("Warning", "Fetch Novel Info first!"); return
        try:
            start = int(self.start_ch.get().strip())
            end = int(self.end_ch.get().strip()) if self.end_ch.get().strip() else self.chapters[-1]["num"]
            split = int(self.split_entry.get().strip())
            dmin = float(self.delay_min.get().strip())
            dmax = float(self.delay_max.get().strip())
            if dmin < 0: dmin = 0; self.delay_min.delete(0,"end"); self.delay_min.insert(0,"0")
            if dmax < dmin: dmax = dmin; self.delay_max.delete(0,"end"); self.delay_max.insert(0,str(dmax))
        except Exception as e: messagebox.showerror("Error", f"Invalid number: {e}"); return
        if start<1 or end<start or split<1: messagebox.showerror("Error", "Check numbers!"); return

        self.running = True; self.paused = False; self.stop_flag = False
        self.run_btn.config(state="disabled"); self.fetch_btn.config(state="disabled")
        self.pause_btn.config(state="normal"); self.stop_btn.config(state="normal")
        self.set_light("green")
        threading.Thread(target=self._crawl_task, args=(start,end,split,dmin,dmax), daemon=True).start()

    def pause_crawl(self):
        self.paused = not self.paused
        if self.paused: self.pause_btn.config(text="▶ RESUME"); self.set_light("yellow"); self.log_line("⏸ PAUSED")
        else: self.pause_btn.config(text="⏸ PAUSE"); self.set_light("green"); self.log_line("▶ RESUMED")

    def stop_crawl(self):
        self.stop_flag = True; self.log_line("⏹ STOPPING...")

    def _save_split_file(self, folder, start_num, end_num, jp_buffer, first_link, create_en):
        if not jp_buffer: return
        rng = f"c{start_num}-{end_num}"

        jp_path = os.path.join(folder, f"JP_{rng}.txt")
        with open(jp_path, "w", encoding="utf-8") as f:
            f.write(CSS_HEADER)
            f.write(first_link + "\n\n")
            f.write("".join(jp_buffer))
        self.log_line(f"💾 Saved → JP_{rng}.txt ({len(jp_buffer)} ch)")

        if create_en:
            en_txt_path = os.path.join(folder, f"EN_{rng}.txt")
            with open(en_txt_path, "wb"): pass
            self.log_line(f"📄 EMPTY → EN_{rng}.txt (0 bytes)")

            en_html_path = os.path.join(folder, f"EN_{rng}.html")
            with open(en_html_path, "wb"): pass
            self.log_line(f"🌐 EMPTY → EN_{rng}.html (0 bytes)")

    def _crawl_task(self, start, end, split, dmin, dmax):
        try:
            mode = self.save_mode_var.get()
            create_en = self.create_en_var.get() and (mode == "merge")
            ch_list = [c for c in self.chapters if start <= c["num"] <= end]
            total = len(ch_list)
            if total == 0: self.log_line("❌ No chapters in range!"); return

            self.log_line(f"📖 Ch{start}→Ch{end} | Total: {total} | Split every {split}")
            self.log_line(f"📂 Output folder: {self.folder_path}/")
            self.log_line(f"⏱ Delay: {dmin}–{dmax}s | EN: {'EMPTY TXT+HTML' if create_en else 'No'}")

            temp_path = os.path.join(self.folder_path, "_TEMP_buffer.txt")
            if os.path.exists(temp_path): os.remove(temp_path)

            start_time = time.time()
            processed = 0
            current_split_start = start
            jp_buffer = []
            first_link_in_split = ""

            for idx, ch in enumerate(ch_list, 1):
                while self.paused and not self.stop_flag: time.sleep(0.2)
                if self.stop_flag: self.log_line("⏹ STOPPED"); break

                self.update_status(f"[{idx}/{total}] Ch{ch['num']}: {ch['title'][:30]}...")
                self.prog_bar["value"] = (idx/total)*100

                full_link = self.base_domain + ch["link"]
                if not first_link_in_split: first_link_in_split = full_link

                t0 = time.time()
                code, html = fetch_page(full_link)
                t1 = time.time()

                ch_title, ch_body = "", ""
                if code == 200:
                    ch_title, ch_body = parse_chapter_content(html, self.domain_type)

                if not ch_body:
                    self.log_line(f"   ⚠ Ch{ch['num']} — EMPTY or NOT FOUND")
                    ch_body = f"[Ch{ch['num']} content not retrieved]\n"
                else:
                    self.log_line(f"   ✅ Ch{ch['num']} | {len(ch_body)} chars | {round(t1-t0,1)}s")

                jp_text = f"=== {ch_title} ===\n{ch_title}\n{ch_body}\n\n"
                jp_buffer.append(jp_text)

                with open(temp_path, "a", encoding="utf-8") as f:
                    f.write(jp_text)

                processed += 1
                elapsed = t1 - start_time
                eta_s = (elapsed/processed)*(total-processed) if processed>0 else 0
                self.eta_label.config(text=f"Estimated remaining: {str(timedelta(seconds=int(eta_s)))}")

                if (ch["num"] - current_split_start + 1) >= split or idx == total:
                    self._save_split_file(self.folder_path, current_split_start, ch["num"], jp_buffer, first_link_in_split, create_en)
                    jp_buffer = []
                    first_link_in_split = ""
                    current_split_start = ch["num"] + 1

                if dmax > 0: time.sleep(random.uniform(dmin, dmax))

            if os.path.exists(temp_path):
                os.remove(temp_path)
                self.log_line("🧹 Temp buffer cleared")

            if not self.stop_flag:
                elapsed_total = time.time() - start_time
                self.log_line(f"🎉 ALL DONE! {processed} chapters in {round(elapsed_total/60,1)} min")
                self.eta_label.config(text="✅ Completed!")

        except Exception as e:
            import traceback
            self.log_line(f"❌ FATAL: {e}")
            self.log_box.config(state="normal")
            self.log_box.insert("end", f"--- Debug ---\n{traceback.format_exc()}\n-----------\n{traceback.format_exc()}")
            self.log_box.config(state="disabled")
        finally:
            self.running = False
            self.run_btn.config(state="normal"); self.fetch_btn.config(state="normal")
            self.pause_btn.config(state="disabled"); self.stop_btn.config(state="disabled")
            self.set_light("gray")
            save_config({
                "delay_min": self.delay_min.get().strip(),
                "delay_max": self.delay_max.get().strip(),
                "split_every": self.split_entry.get().strip(),
                "create_en": self.create_en_var.get(),
                "save_mode": self.save_mode_var.get()
            })

    def on_close(self):
        self.stop_flag = True
        self.cfg["window_w"] = self.root.winfo_width()
        self.cfg["window_h"] = self.root.winfo_height()
        self.cfg["window_x"] = self.root.winfo_x()
        self.cfg["window_y"] = self.root.winfo_y()
        save_config({
            "delay_min": self.delay_min.get().strip(),
            "delay_max": self.delay_max.get().strip(),
            "split_every": self.split_entry.get().strip(),
            "create_en": self.create_en_var.get(),
            "save_mode": self.save_mode_var.get(),
            "window_w": self.cfg["window_w"],
            "window_h": self.cfg["window_h"],
            "window_x": self.cfg["window_x"],
            "window_y": self.cfg["window_y"]
        })
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SyosetuCrawlerGUI(root)
    root.mainloop()