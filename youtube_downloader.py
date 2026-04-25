"""
YTDROP v5 — YouTube Downloader (All functions working)

INSTALL:
    pip install customtkinter yt-dlp Pillow requests

FOR 1080p/4K (ffmpeg):
    winget install ffmpeg      (Windows — run in cmd, then RESTART cmd/app)
    brew install ffmpeg        (Mac)
    sudo apt install ffmpeg    (Linux)

RUN:
    python youtube_downloader.py
"""

import customtkinter as ctk
import yt_dlp
import threading
import os
import re
import ssl
import sys
import shutil
import subprocess
import requests
import urllib3
from PIL import Image
from io import BytesIO
from tkinter import filedialog, messagebox

# Suppress SSL warnings (needed for some restricted networks)
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
C = {
    "bg":      "#080810",
    "card":    "#0F0F1A",
    "surface": "#161625",
    "hover":   "#1E1E30",
    "accent":  "#E63946",
    "accent2": "#C1121F",
    "primary": "#EEF0FF",
    "muted":   "#6B6B8A",
    "dim":     "#32324A",
    "border":  "#232338",
    "green":   "#2ECC71",
    "amber":   "#F4A261",
    "blue":    "#4CC9F0",
    "purple":  "#9D4EDD",
    "teal":    "#2EC4B6",
}

# ---------------------------------------------------------------------------
# FFmpeg detection — finds winget / scoop / choco / manual installs
# even when ffmpeg is NOT added to the system PATH yet.
# ---------------------------------------------------------------------------
def _find_ffmpeg():
    p = shutil.which("ffmpeg")
    if p:
        return p
    local       = os.environ.get("LOCALAPPDATA", "")
    userprofile = os.path.expanduser("~")

    winget_root = os.path.join(local, "Microsoft", "WinGet", "Packages")
    if os.path.isdir(winget_root):
        for dirpath, dirnames, filenames in os.walk(winget_root):
            depth = dirpath[len(winget_root):].count(os.sep)
            if depth > 5:
                dirnames.clear()
                continue
            if "ffmpeg.exe" in filenames:
                candidate = os.path.join(dirpath, "ffmpeg.exe")
                try:
                    r = subprocess.run(
                        [candidate, "-version"],
                        capture_output=True, timeout=5,
                        creationflags=subprocess.CREATE_NO_WINDOW
                        if sys.platform == "win32" else 0,
                    )
                    if r.returncode == 0:
                        return candidate
                except Exception:
                    pass

    winapps = os.path.join(local, "Microsoft", "WindowsApps")
    if os.path.isdir(winapps):
        candidate = os.path.join(winapps, "ffmpeg.exe")
        if os.path.isfile(candidate):
            try:
                r = subprocess.run(
                    [candidate, "-version"],
                    capture_output=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                    if sys.platform == "win32" else 0,
                )
                if r.returncode == 0:
                    return candidate
            except Exception:
                pass

    candidates = [
        os.path.join("C:\\", "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join("C:\\", "Program Files", "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join("C:\\", "Program Files (x86)", "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(userprofile, "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(userprofile, "scoop", "apps", "ffmpeg", "current", "bin", "ffmpeg.exe"),
        os.path.join("C:\\", "ProgramData", "chocolatey", "bin", "ffmpeg.exe"),
        os.path.join("C:\\", "tools", "ffmpeg", "bin", "ffmpeg.exe"),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            try:
                r = subprocess.run(
                    [candidate, "-version"],
                    capture_output=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                    if sys.platform == "win32" else 0,
                )
                if r.returncode == 0:
                    return candidate
            except Exception:
                pass
    return None

FFMPEG_PATH = _find_ffmpeg()
FFMPEG_OK   = FFMPEG_PATH is not None

CLIENTS = [
    ["tv_embedded"], ["web_embedded"], ["ios"], ["android"], ["mweb"], ["web"],
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fmt_bytes(b):
    if not b: return "?"
    if b >= 1_073_741_824: return f"{b / 1_073_741_824:.1f} GB"
    if b >= 1_048_576: return f"{b / 1_048_576:.1f} MB"
    return f"{b / 1024:.0f} KB"

def fmt_dur(s):
    if not s: return "0:00"
    s = int(s); h, r = divmod(s, 3600); m, sec = divmod(r, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

def clean(n):
    return re.sub(r'[\\/*?:"<>|]', "_", n)[:80]

def base_opts(extra=None):
    opts = {
        "quiet": True, "no_warnings": True, "nocheckcertificate": True,
        "socket_timeout": 30, "retries": 5,
        "abort_on_unavailable_fragments": False,
        "http_headers": {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0.0.0 Safari/537.36"),
            "Accept-Language": "en-US,en;q=0.9",
        },
    }
    if FFMPEG_PATH:
        opts["ffmpeg_location"] = os.path.dirname(FFMPEG_PATH)
    if extra:
        opts.update(extra)
    return opts

def fetch_robust(url):
    last = None
    for client in CLIENTS:
        opts = base_opts({"extractor_args": {"youtube": {"player_client": client}}})
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if info and info.get("title"):
                return info, client[0]
        except Exception as e:
            last = e
    try:
        with yt_dlp.YoutubeDL(base_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
        if info and info.get("title"):
            return info, "default"
    except Exception as e:
        last = e
    raise last or Exception("All strategies failed.")

RES = {
    2160: ("4K · 2160p",    "4K",  C["amber"]),
    1440: ("2K · 1440p",    "2K",  C["amber"]),
    1080: ("1080p Full HD", "FHD", C["blue"]),
    720:  ("720p HD",       "HD",  C["green"]),
    480:  ("480p SD",       "SD",  C["teal"]),
    360:  ("360p Low",      "360", C["muted"]),
    240:  ("240p Lower",    "240", C["dim"]),
    144:  ("144p Minimum",  "144", C["dim"]),
}

def extract_formats(info):
    out, seen = [], set()
    fmts = info.get("formats", [])
    all_video  = [f for f in fmts if f.get("vcodec","none") != "none" and f.get("height")]
    combined   = [f for f in all_video if f.get("acodec","none") != "none"]
    video_only = [f for f in all_video if f.get("acodec","none") == "none"]
    audio_only = sorted(
        [f for f in fmts if f.get("vcodec","none")=="none" and f.get("acodec","none")!="none"],
        key=lambda x: x.get("abr",0) or 0, reverse=True)
    best_audio_id = audio_only[0]["format_id"] if audio_only else "bestaudio"

    combined_by_h = {}
    for f in sorted(combined, key=lambda x: (x.get("height",0), x.get("tbr",0) or 0), reverse=True):
        h = f.get("height",0)
        if h not in combined_by_h: combined_by_h[h] = f
    vidonly_by_h = {}
    for f in sorted(video_only, key=lambda x: (x.get("height",0), x.get("tbr",0) or 0), reverse=True):
        h = f.get("height",0)
        if h not in vidonly_by_h: vidonly_by_h[h] = f

    all_heights = sorted(set(list(combined_by_h)+list(vidonly_by_h)), reverse=True)
    for h in all_heights:
        if h not in RES or h in seen: continue
        label, badge, color = RES[h]
        cf, vf = combined_by_h.get(h), vidonly_by_h.get(h)
        best_f = vf or cf
        fps = best_f.get("fps",0) or 0
        vcodec = (best_f.get("vcodec") or "")[:12]
        size = fmt_bytes(best_f.get("filesize") or best_f.get("filesize_approx"))
        tbr = best_f.get("tbr",0) or 0
        needs_merge = h > 720
        note = ""
        if needs_merge and not FFMPEG_OK:
            if cf:
                fmt_str = f"{cf['format_id']}/best[height<={h}][ext=mp4]/best[height<={h}]"
                note = " (no-ffmpeg fallback)"; color = C["amber"]
            else: continue
        elif FFMPEG_OK:
            if vf:
                fmt_str = (f"{vf['format_id']}+{best_audio_id}"
                           f"/bestvideo[height<={h}]+bestaudio/best[height<={h}]")
            elif cf: fmt_str = f"{cf['format_id']}/best[height<={h}]"
            else: continue
        else:
            if cf: fmt_str = f"{cf['format_id']}/best[height<={h}][ext=mp4]/best[height<={h}]"
            elif vf: fmt_str = f"{vf['format_id']}+{best_audio_id}/best[height<={h}]"
            else: continue
        seen.add(h)
        out.append({"type":"video","label":label+note,"badge":badge,"color":color,
                     "fps":f"{fps:.0f}fps" if fps else "","bitrate":f"{tbr:.0f}kbps" if tbr else "",
                     "size":size,"format_str":fmt_str,"height":h,"vcodec":vcodec,"needs_ffmpeg":needs_merge})

    seen_ext = set()
    for f in audio_only:
        ext = f.get("ext","m4a")
        if ext in seen_ext: continue
        seen_ext.add(ext)
        out.append({"type":"audio","label":f"Audio {ext.upper()}","badge":ext.upper(),
                     "color":C["purple"],"fps":"",
                     "bitrate":f"{f.get('abr',0) or 0:.0f}kbps" if f.get("abr") else "",
                     "size":fmt_bytes(f.get("filesize") or f.get("filesize_approx")),
                     "format_str":f.get("format_id","bestaudio"),"height":0,"mp3":False,"needs_ffmpeg":False})
    if FFMPEG_OK:
        out.append({"type":"audio","label":"Audio MP3 (Best)","badge":"MP3","color":C["purple"],
                     "fps":"","bitrate":"Best quality","size":"~varies","format_str":"bestaudio/best",
                     "height":0,"mp3":True,"needs_ffmpeg":True})
    else:
        out.append({"type":"audio","label":"Audio M4A (Best — no ffmpeg needed)","badge":"M4A",
                     "color":C["purple"],"fps":"","bitrate":"Best quality","size":"~varies",
                     "format_str":"bestaudio[ext=m4a]/bestaudio","height":0,"mp3":False,"needs_ffmpeg":False})
    return out

def friendly(raw):
    r = raw.lower()
    if "ffmpeg" in r:
        path_hint = f"\nFound at: {FFMPEG_PATH}" if FFMPEG_PATH else "\nffmpeg not found on this system."
        return "FFmpeg error. Run:  winget install ffmpeg  then restart." + path_hint
    if "ssl" in r or "certificate" in r: return "SSL error — run:  pip install -U yt-dlp"
    if "sign in" in r or "age" in r: return "Age-restricted video — cannot download without sign-in."
    if "private" in r: return "This video is private."
    if "playback on other websites" in r: return "This video blocks external playback."
    if "unavailable" in r or "removed" in r: return "Video unavailable or removed."
    if "requested format is not available" in r: return "Format unavailable. Try lower quality."
    if "403" in r or "forbidden" in r: return "YouTube blocked request. pip install -U yt-dlp"
    return f"Error: {raw[:220]}"


# ===========================================================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YTDROP v5")
        self.geometry("880x980")
        self.minsize(700, 600)
        self.configure(fg_color=C["bg"])
        self._info      = None
        self._formats   = []
        self._sel       = None
        self._save_dir  = os.path.expanduser("~/Downloads")
        self._dl_active = False
        self._fmt_btns  = []
        self._ci        = None
        self._last_file = None
        self._build()

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=0, height=68)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        hi = ctk.CTkFrame(hdr, fg_color="transparent")
        hi.pack(fill="both", expand=True, padx=24)

        ctk.CTkLabel(hi, text="▶  YTDROP", font=ctk.CTkFont("Courier New", 22, "bold"),
                     text_color=C["accent"]).pack(side="left", pady=14)
        ctk.CTkLabel(hi, text="v5", font=ctk.CTkFont("Courier New", 11),
                     text_color=C["muted"]).pack(side="left", padx=(8,0), pady=14)

        if FFMPEG_OK:
            badge_color, badge_text, badge_tc = "#1a4a2e", " ✓ FFmpeg ready — 1080p/4K enabled ", C["green"]
        else:
            badge_color, badge_text, badge_tc = "#3a1f0a", " ⚠ FFmpeg not found — max 720p ", C["amber"]

        bf = ctk.CTkFrame(hi, fg_color=badge_color, corner_radius=8)
        bf.pack(side="right", pady=18)
        ctk.CTkLabel(bf, text=badge_text, font=ctk.CTkFont("Courier New", 9, "bold"),
                     text_color=badge_tc).pack(padx=8, pady=4)

        self._body = ctk.CTkScrollableFrame(self, fg_color=C["bg"], corner_radius=0,
            scrollbar_fg_color=C["surface"], scrollbar_button_color=C["dim"])
        self._body.pack(fill="both", expand=True)
        self._url_section()
        if not FFMPEG_OK:
            self._ffmpeg_banner()

        # Stable wrapper frames for correct re-pack order
        self._info_wrapper = ctk.CTkFrame(self._body, fg_color="transparent")
        self._fmt_wrapper  = ctk.CTkFrame(self._body, fg_color="transparent")
        self._dl_wrapper   = ctk.CTkFrame(self._body, fg_color="transparent")
        self._info_wrapper.pack(fill="x")
        self._fmt_wrapper.pack(fill="x")
        self._dl_wrapper.pack(fill="x")

        self._info_card = self._make_card(self._info_wrapper)
        self._fmt_card  = self._make_card(self._fmt_wrapper)
        self._dl_card   = self._make_card(self._dl_wrapper)
        self._hide_cards()

    def _hide_cards(self):
        for wrapper in (self._info_wrapper, self._fmt_wrapper, self._dl_wrapper):
            for child in wrapper.winfo_children():
                child.pack_forget()

    def _show_card(self, card):
        card.master.pack(fill="x", padx=18, pady=(0, 12))

    def _ffmpeg_banner(self):
        banner = ctk.CTkFrame(self._body, fg_color="#1E1200", corner_radius=12,
                               border_width=1, border_color="#3a2800")
        banner.pack(fill="x", padx=18, pady=(0, 12))
        bi = ctk.CTkFrame(banner, fg_color="transparent")
        bi.pack(fill="x", padx=16, pady=12)
        ctk.CTkLabel(bi, text="⚠  FFmpeg not found. Qualities above 720p require FFmpeg.",
            font=ctk.CTkFont("Courier New", 11), text_color=C["amber"],
            wraplength=780, justify="left").pack(anchor="w")
        ctk.CTkLabel(bi, text="Install: Windows → winget install ffmpeg → restart app",
            font=ctk.CTkFont("Courier New", 10), text_color=C["muted"],
            wraplength=780, justify="left").pack(anchor="w", pady=(4,0))

    def _make_card(self, parent, pady=(0, 12)):
        outer = ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=16,
                             border_width=1, border_color=C["border"])
        outer.pack(fill="x", padx=18, pady=pady)
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=18, pady=16)
        return inner

    def _sec_label(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=ctk.CTkFont("Courier New", 9, "bold"),
                     text_color=C["muted"]).pack(anchor="w", pady=(0,10))

    def _url_section(self):
        f = self._make_card(self._body, pady=(16,12))
        self._sec_label(f, "① PASTE YOUTUBE URL")
        row = ctk.CTkFrame(f, fg_color="transparent"); row.pack(fill="x")
        self._url_var = ctk.StringVar()
        self._entry = ctk.CTkEntry(row, textvariable=self._url_var,
            placeholder_text="https://www.youtube.com/watch?v=...",
            height=52, corner_radius=12,
            fg_color=C["surface"], border_color=C["border"], border_width=1,
            text_color=C["primary"], placeholder_text_color=C["dim"],
            font=ctk.CTkFont("Courier New", 13))
        self._entry.pack(side="left", fill="x", expand=True, padx=(0,10))
        self._entry.bind("<Return>", lambda e: self._do_fetch())
        self._fbtn = ctk.CTkButton(row, text="FETCH  →", width=130, height=52, corner_radius=12,
            fg_color=C["accent"], hover_color=C["accent2"],
            text_color="white", font=ctk.CTkFont("Courier New", 13, "bold"),
            command=self._do_fetch)
        self._fbtn.pack(side="right")

        brow = ctk.CTkFrame(f, fg_color="transparent"); brow.pack(fill="x", pady=(8,0))
        ctk.CTkButton(brow, text="⊕  Paste", height=30, width=100,
                      fg_color="transparent", hover_color=C["hover"],
                      text_color=C["muted"], font=ctk.CTkFont("Courier New",11),
                      border_width=1, border_color=C["border"], corner_radius=8,
                      command=self._paste).pack(side="left")
        ctk.CTkButton(brow, text="✕  Clear", height=30, width=80,
                      fg_color="transparent", hover_color=C["hover"],
                      text_color=C["dim"], font=ctk.CTkFont("Courier New",11),
                      border_width=1, border_color=C["border"], corner_radius=8,
                      command=self._clear_url).pack(side="left", padx=(8,0))

        self._slbl = ctk.CTkLabel(f, text="", font=ctk.CTkFont("Courier New", 11),
                                   text_color=C["muted"], wraplength=780, justify="left")
        self._slbl.pack(anchor="w", pady=(8,0))

    def _paste(self):
        try: self._url_var.set(self.clipboard_get().strip())
        except: pass

    def _clear_url(self):
        self._url_var.set(""); self._setstatus("")
        self._hide_cards()
        self._info = None; self._formats = []; self._sel = None

    def _setstatus(self, txt, col=None):
        self._slbl.configure(text=txt, text_color=col or C["muted"])

    def _do_fetch(self):
        url = self._url_var.get().strip()
        if not url:
            self._setstatus("⚠  Paste a YouTube URL first.", C["amber"]); return
        if "youtube.com" not in url and "youtu.be" not in url:
            self._setstatus("⚠  Not a YouTube URL.", C["amber"]); return
        self._fbtn.configure(text="Loading…", state="disabled", fg_color=C["surface"])
        self._setstatus("⏳  Connecting…", C["muted"])
        self._hide_cards()
        for card in (self._info_card, self._fmt_card, self._dl_card):
            for w in card.winfo_children(): w.destroy()
        threading.Thread(target=self._fetch_th, args=(url,), daemon=True).start()

    def _fetch_th(self, url):
        try:
            info, client = fetch_robust(url)
            self._info = info
            self._formats = extract_formats(info)
            self.after(0, lambda c=client: self._fetch_ok(c))
        except Exception as e:
            msg = friendly(str(e))
            self.after(0, lambda m=msg: self._fetch_fail(m))

    def _fetch_ok(self, client):
        self._fbtn.configure(text="FETCH  →", state="normal", fg_color=C["accent"])
        self._setstatus(f"✓  Loaded via [{client}]", C["green"])
        self._show_info()

    def _fetch_fail(self, msg):
        self._fbtn.configure(text="FETCH  →", state="normal", fg_color=C["accent"])
        self._setstatus(msg, C["accent"])

    def _show_info(self):
        f = self._info_card
        for w in f.winfo_children(): w.destroy()
        self._show_card(f)
        info = self._info
        self._sec_label(f, "② VIDEO INFO")
        row = ctk.CTkFrame(f, fg_color="transparent"); row.pack(fill="x")
        thumb = ctk.CTkFrame(row, fg_color=C["surface"], corner_radius=12, width=180, height=101)
        thumb.pack(side="left", padx=(0,16)); thumb.pack_propagate(False)
        ctk.CTkLabel(thumb, text="▶", font=ctk.CTkFont(size=34), text_color=C["accent"]
                     ).place(relx=.5, rely=.5, anchor="center")
        t_url = info.get("thumbnail","")
        if t_url:
            threading.Thread(target=self._thumb, args=(t_url, thumb), daemon=True).start()
        meta = ctk.CTkFrame(row, fg_color="transparent"); meta.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(meta, text=info.get("title","?"),
                     font=ctk.CTkFont("Courier New",14,"bold"),
                     text_color=C["primary"], wraplength=560, justify="left", anchor="w"
                     ).pack(anchor="w", pady=(0,6))
        d = info.get("upload_date","")
        date_str = f"{d[6:]}/{d[4:6]}/{d[:4]}" if len(d)==8 else d
        for icon, val in [
            ("⏱", fmt_dur(info.get("duration"))),
            ("👤", info.get("uploader") or info.get("channel","")),
            ("👁", f"{info.get('view_count',0):,} views" if info.get("view_count") else ""),
            ("📅", date_str),
        ]:
            if val:
                r2 = ctk.CTkFrame(meta, fg_color="transparent"); r2.pack(anchor="w", pady=2)
                ctk.CTkLabel(r2, text=f"{icon}  {val}", font=ctk.CTkFont("Courier New",11),
                             text_color=C["muted"]).pack(side="left")
        self._show_formats()

    def _thumb(self, url, frame):
        try:
            r = requests.get(url, timeout=8, verify=False)
            r.raise_for_status()
            img = Image.open(BytesIO(r.content)).resize((180, 101), Image.LANCZOS)
            ci = ctk.CTkImage(img, size=(180, 101))
            self._ci = ci
            lbl = ctk.CTkLabel(frame, image=ci, text="")
            self.after(0, lambda: lbl.place(relx=0, rely=0, relwidth=1, relheight=1))
        except: pass

    def _show_formats(self):
        f = self._fmt_card
        for w in f.winfo_children(): w.destroy()
        self._show_card(f)
        self._fmt_btns = []; self._sel = None
        self._sec_label(f, "③ SELECT QUALITY")
        if not FFMPEG_OK:
            nf = ctk.CTkFrame(f, fg_color="#1E1200", corner_radius=8, border_width=1, border_color="#3a2800")
            nf.pack(fill="x", pady=(0,10))
            ctk.CTkLabel(nf, text="⚠  FFmpeg not installed — 1080p/4K hidden.",
                         font=ctk.CTkFont("Courier New",10), text_color=C["amber"],
                         wraplength=700, justify="left").pack(padx=12, pady=8, anchor="w")
        vfmts = [x for x in self._formats if x["type"]=="video"]
        afmts = [x for x in self._formats if x["type"]=="audio"]
        if vfmts:
            ctk.CTkLabel(f, text="VIDEO FORMATS", font=ctk.CTkFont("Courier New",9),
                         text_color=C["dim"]).pack(anchor="w", pady=(0,5))
            for fmt in vfmts: self._fmt_row(f, fmt)
        if afmts:
            ctk.CTkLabel(f, text="AUDIO ONLY", font=ctk.CTkFont("Courier New",9),
                         text_color=C["dim"]).pack(anchor="w", pady=(12,5))
            for fmt in afmts: self._fmt_row(f, fmt)
        self._build_dl()

    def _fmt_row(self, parent, fmt):
        fr = ctk.CTkFrame(parent, fg_color=C["surface"], corner_radius=12,
                          border_width=1, border_color=C["border"])
        fr.pack(fill="x", pady=3)
        ctk.CTkLabel(fr, text=fmt["badge"], font=ctk.CTkFont("Courier New",9,"bold"),
                     text_color="white", fg_color=fmt["color"],
                     corner_radius=6, width=44, height=22).pack(side="left", padx=(12,10), pady=12)
        ctk.CTkLabel(fr, text=fmt["label"], font=ctk.CTkFont("Courier New",12),
                     text_color=C["primary"], anchor="w").pack(side="left", padx=4)
        if fmt.get("vcodec"):
            ctk.CTkLabel(fr, text=fmt["vcodec"], font=ctk.CTkFont("Courier New",9),
                         text_color=C["dim"]).pack(side="left", padx=4)
        ctk.CTkFrame(fr, fg_color="transparent").pack(side="left", expand=True)
        details = "  ·  ".join(filter(None,[fmt.get("fps",""),fmt.get("bitrate",""),fmt.get("size","")]))
        if details:
            ctk.CTkLabel(fr, text=details, font=ctk.CTkFont("Courier New",10),
                         text_color=C["muted"]).pack(side="left", padx=6)
        btn = ctk.CTkButton(fr, text="SELECT", width=84, height=32, corner_radius=8,
                            fg_color="transparent", border_width=1,
                            border_color=C["dim"], hover_color=C["hover"],
                            text_color=C["muted"], font=ctk.CTkFont("Courier New",10,"bold"))
        btn.pack(side="right", padx=12, pady=10)
        btn.configure(command=lambda _f=fmt,_b=btn,_fr=fr: self._pick(_f,_b,_fr))
        self._fmt_btns.append((btn, fr))

    def _pick(self, f, b, fr):
        for btn, frame in self._fmt_btns:
            btn.configure(text="SELECT", fg_color="transparent",
                          text_color=C["muted"], border_color=C["dim"])
            frame.configure(border_color=C["border"])
        self._sel = f
        b.configure(text="✓ CHOSEN", fg_color=C["accent"],
                    text_color="white", border_color=C["accent"])
        fr.configure(border_color=C["accent"])
        ext_label = "MP4" if f["type"]=="video" else f.get("badge","")
        self._dlbtn.configure(
            text=f"⬇  DOWNLOAD  {f['label']}  [{ext_label}]",
            fg_color=C["accent"], hover_color=C["accent2"],
            text_color="white", state="normal")

    def _build_dl(self):
        f = self._dl_card
        for w in f.winfo_children(): w.destroy()
        self._show_card(f)
        self._sec_label(f, "④ SAVE LOCATION & DOWNLOAD")
        loc = ctk.CTkFrame(f, fg_color=C["surface"], corner_radius=12,
                            border_width=1, border_color=C["border"])
        loc.pack(fill="x", pady=(0,12))
        li = ctk.CTkFrame(loc, fg_color="transparent"); li.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(li, text="📁  Save to:", font=ctk.CTkFont("Courier New",11,"bold"),
                     text_color=C["primary"]).pack(side="left", padx=(0,10))
        self._dir_var = ctk.StringVar(value=self._save_dir)
        ctk.CTkEntry(li, textvariable=self._dir_var, height=38, corner_radius=8,
                     fg_color=C["card"], border_color=C["border"],
                     text_color=C["muted"], font=ctk.CTkFont("Courier New",11)
                     ).pack(side="left", fill="x", expand=True, padx=(0,10))
        ctk.CTkButton(li, text="📂  Browse…", width=110, height=38, corner_radius=8,
                      fg_color=C["accent"], hover_color=C["accent2"],
                      text_color="white", font=ctk.CTkFont("Courier New",11,"bold"),
                      command=self._browse).pack(side="right")

        qr = ctk.CTkFrame(f, fg_color="transparent"); qr.pack(fill="x", pady=(0,12))
        ctk.CTkLabel(qr, text="Quick:", font=ctk.CTkFont("Courier New",10),
                     text_color=C["dim"]).pack(side="left", padx=(0,8))
        for label, path in [
            ("~/Downloads", os.path.expanduser("~/Downloads")),
            ("~/Desktop", os.path.expanduser("~/Desktop")),
            ("~/Videos", os.path.expanduser("~/Videos")),
            ("~/Music", os.path.expanduser("~/Music")),
        ]:
            if os.path.isdir(path):
                ctk.CTkButton(qr, text=label, height=26, corner_radius=6,
                              fg_color="transparent", border_width=1,
                              border_color=C["border"], hover_color=C["hover"],
                              text_color=C["muted"], font=ctk.CTkFont("Courier New",10),
                              command=lambda p=path: self._set_dir(p)).pack(side="left", padx=(0,6))

        self._prog = ctk.CTkProgressBar(f, height=8, corner_radius=4,
                                         fg_color=C["surface"], progress_color=C["accent"])
        self._prog.set(0)
        self._plbl = ctk.CTkLabel(f, text="", font=ctk.CTkFont("Courier New",11),
                                   text_color=C["muted"])
        self._dlbtn = ctk.CTkButton(f, text="⬇  SELECT A FORMAT FIRST",
            height=58, corner_radius=14, fg_color=C["surface"], hover_color=C["hover"],
            border_width=1, border_color=C["border"],
            text_color=C["dim"], state="disabled",
            font=ctk.CTkFont("Courier New",13,"bold"), command=self._start_dl)
        self._dlbtn.pack(fill="x", pady=(4,0))

        self._open_btn = ctk.CTkButton(f, text="📂  Open Download Folder",
            height=40, corner_radius=10, fg_color="transparent", hover_color=C["hover"],
            border_width=1, border_color=C["green"],
            text_color=C["green"], font=ctk.CTkFont("Courier New", 11, "bold"),
            command=self._open_folder)

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self._save_dir)
        if d: self._save_dir = d; self._dir_var.set(d)

    def _set_dir(self, path):
        self._save_dir = path; self._dir_var.set(path)

    def _open_folder(self):
        path = self._dir_var.get().strip() or self._save_dir
        if os.path.isdir(path):
            if sys.platform == "win32": os.startfile(path)
            elif sys.platform == "darwin": subprocess.Popen(["open", path])
            else: subprocess.Popen(["xdg-open", path])

    def _start_dl(self):
        if self._dl_active or not self._sel: return
        save = self._dir_var.get().strip() or os.path.expanduser("~/Downloads")
        os.makedirs(save, exist_ok=True)
        self._dl_active = True
        self._dlbtn.configure(text="⏳  Downloading…", state="disabled", fg_color=C["surface"])
        self._open_btn.pack_forget()
        self._prog.configure(progress_color=C["accent"])
        self._prog.pack(fill="x", pady=(10,4)); self._prog.set(0)
        self._plbl.pack(anchor="w"); self._plbl.configure(text="Starting…", text_color=C["muted"])
        threading.Thread(target=self._dl_th, args=(self._sel, save), daemon=True).start()

    def _dl_th(self, fmt, save):
        url = self._url_var.get().strip()
        title = clean(self._info.get("title","video"))

        def hook(d):
            if d["status"] == "downloading":
                try:
                    pct = float(d.get("_percent_str","0%").strip().rstrip("%"))/100
                except (ValueError, TypeError):
                    pct = 0
                downloaded = d.get("_downloaded_bytes_str","").strip()
                total = d.get("_total_bytes_str", d.get("_total_bytes_estimate_str","")).strip()
                speed = d.get("_speed_str","").strip()
                eta = d.get("_eta_str","").strip()
                txt = f"  {int(pct*100)}%"
                if downloaded:
                    txt += f"  {downloaded}"
                    if total: txt += f" / {total}"
                if speed: txt += f"   @ {speed}"
                if eta: txt += f"   ETA {eta}"
                self.after(0, lambda p=pct,t=txt: (self._prog.set(p), self._plbl.configure(text=t)))
            elif d["status"] == "finished":
                self.after(0, lambda: (self._prog.set(1.0), self._plbl.configure(text="✓  Processing / merging…")))

        opts = base_opts({"progress_hooks": [hook]})
        opts["outtmpl"] = os.path.join(save, f"{title}.%(ext)s")

        if fmt.get("mp3"):
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{"key":"FFmpegExtractAudio",
                                       "preferredcodec":"mp3","preferredquality":"192"}]
        elif fmt["type"] == "audio":
            opts["format"] = fmt["format_str"]
        else:
            opts["format"] = fmt["format_str"]
            if FFMPEG_OK: opts["merge_output_format"] = "mp4"

        success, last_err = False, Exception("unknown")
        for client in CLIENTS:
            o = dict(opts)
            o["extractor_args"] = {"youtube": {"player_client": client}}
            try:
                with yt_dlp.YoutubeDL(o) as ydl:
                    ydl.download([url])
                success = True; break
            except Exception as e:
                last_err = e
                if "ffmpeg" in str(e).lower(): break
                continue

        if not success and "ffmpeg" not in str(last_err).lower():
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                success = True
            except Exception as e:
                last_err = e

        if success:
            self.after(0, lambda: self._dl_done(save))
        else:
            msg = friendly(str(last_err))
            self.after(0, lambda m=msg: self._dl_fail(m))

    def _dl_done(self, save):
        self._dl_active = False
        self._prog.configure(progress_color=C["green"])
        self._plbl.configure(text=f"✓  Saved to: {save}", text_color=C["green"])
        self._dlbtn.configure(text="✓  DONE — CLICK TO DOWNLOAD AGAIN",
                              fg_color=C["green"], hover_color="#27AE60",
                              text_color="white", state="normal", command=self._reset_for_redownload)
        self._open_btn.pack(fill="x", pady=(8,0))
        messagebox.showinfo("Done!", f"Download complete!\nSaved to:\n{save}")

    def _reset_for_redownload(self):
        self._prog.pack_forget(); self._plbl.pack_forget(); self._open_btn.pack_forget()
        self._prog.configure(progress_color=C["accent"]); self._prog.set(0)
        self._plbl.configure(text="", text_color=C["muted"])
        if self._sel:
            ext_label = "MP4" if self._sel["type"]=="video" else self._sel.get("badge","")
            self._dlbtn.configure(text=f"⬇  DOWNLOAD  {self._sel['label']}  [{ext_label}]",
                fg_color=C["accent"], hover_color=C["accent2"],
                text_color="white", state="normal", command=self._start_dl)
        else:
            self._dlbtn.configure(text="⬇  SELECT A FORMAT FIRST", fg_color=C["surface"],
                hover_color=C["hover"], text_color=C["dim"], state="disabled", command=self._start_dl)

    def _dl_fail(self, msg):
        self._dl_active = False
        self._prog.configure(progress_color=C["accent"])
        self._plbl.configure(text=msg[:120], text_color=C["accent"])
        self._dlbtn.configure(text="✗  FAILED — CLICK TO TRY AGAIN",
                              fg_color=C["accent2"], text_color="white", state="normal",
                              command=self._start_dl)
        messagebox.showerror("Download Failed", msg)


if __name__ == "__main__":
    App().mainloop()
