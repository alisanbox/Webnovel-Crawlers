# Webnovel-Crawlers
Python-based GUI crawlers for downloading webnovels — built for **69shuba.com** (Chinese) and **Syosetu / Syosetu Novel18** (Japanese).  ---

---

## ✨ Features

### 🇨🇳 69shuba Crawler (`Crawl_69shuba_GUI_v7.9`)
- ✅ Bypasses Cloudflare automatically
- ✅ Auto-detect novel ID & create output folder `69shuba_[ID]/`
- ✅ Resume from ANY chapter — set start chapter + start URL
- ✅ Split files by chapter range: `CN_c1-100.txt`, `EN_c1-100.txt`
- ✅ Separator at START of each chapter → clean readable format
- ✅ 2 title lines: Official Title + Website Title (for comparison)
- ✅ Create empty EN files for manual translation later
- ✅ Pause / Resume / Stop & Save
- ✅ Progress bar + ETA countdown
- ✅ Save window size, position & all settings automatically
- ✅ Logs saved with timestamps

### 🇯🇵 Syosetu Crawler
- ✅ Supports `syosetu.com` AND `novel18.syosetu.com` (auto age-verify)
- ✅ Fetch novel info: Title, Author, Total Chapters, Status, Synopsis
- ✅ Auto-scan multi-page TOC (handles >100 chapters)
- ✅ Split file naming: `JP_c1-100.txt`, `EN_c1-100.txt/.html`
- ✅ Delay control (0s allowed)
- ✅ Same GUI features: pause, progress, settings, logs

---

## 📥 Requirements
```bash
pip install curl_cffi beautifulsoup4
