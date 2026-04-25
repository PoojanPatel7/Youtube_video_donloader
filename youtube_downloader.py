"""
██╗   ██╗████████╗     ██████╗ ██████╗ ███████╗ █████╗  ██████╗██╗  ██╗
╚██╗ ██╔╝╚══██╔══╝     ██╔══██╗██╔══██╗██╔════╝██╔══██╗██╔════╝██║  ██║
 ╚████╔╝    ██║        ██████╔╝██████╔╝█████╗  ███████║██║     ███████║
  ╚██╔╝     ██║        ██╔══██╗██╔══██╗██╔══╝  ██╔══██║██║     ██╔══██║
   ██║      ██║███████╗██████╔╝██║  ██║███████╗██║  ██║╚██████╗██║  ██║
   ╚═╝      ╚═╝╚══════╝╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝

   YT-BREACH — Intercept. Extract. Own.

INSTALL:
    pip install customtkinter yt-dlp Pillow requests

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
import time
import random
import shutil
import subprocess
import requests
import urllib3
from PIL import Image
from io import BytesIO
from tkinter import filedialog, messagebox

ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ---------------------------------------------------------------------------
# HACKER COLOR PALETTE  (brighter, more readable)
# ---------------------------------------------------------------------------
H = {
    "bg":         "#0a0a0a",
    "bg2":        "#0d110d",
    "card":       "#101810",
    "surface":    "#141c14",
    "hover":      "#1a2a1a",
    "border":     "#1a3a1a",
    "border2":    "#2a5a2a",

    "green":      "#00ff41",        # Matrix green — headings / highlights
    "green_hi":   "#7fff7f",        # Bright green — for body text (very readable)
    "green_mid":  "#40d060",        # Medium green — secondary text
    "green_lo":   "#208830",        # Low green — muted labels
    "green_bg":   "#0a2a0a",        # Green tinted background
    "green_dark": "#082008",

    "red":        "#ff3355",
    "red_bg":     "#2a0a10",
    "amber":      "#ffcc00",
    "amber_bg":   "#2a2200",
    "cyan":       "#00e5ff",
    "cyan_bg":    "#002a33",
    "purple":     "#cc66ff",
    "white":      "#e8ffe8",        # Near-white for titles
    "off_white":  "#c0e8c0",        # Softer white for body
    "dim":        "#306030",
}

# ---------------------------------------------------------------------------
# FFmpeg detection
# ---------------------------------------------------------------------------
def _find_ffmpeg():
    p = shutil.which("ffmpeg")
    if p:
        return p
    local = os.environ.get("LOCALAPPDATA", "")
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
                    r = subprocess.run([candidate, "-version"], capture_output=True, timeout=5,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                    if r.returncode == 0:
                        return candidate
                except Exception:
                    pass
    winapps = os.path.join(local, "Microsoft", "WindowsApps")
    if os.path.isdir(winapps):
        c2 = os.path.join(winapps, "ffmpeg.exe")
        if os.path.isfile(c2):
            try:
                r = subprocess.run([c2, "-version"], capture_output=True, timeout=5,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                if r.returncode == 0:
                    return c2
            except Exception:
                pass
    for candidate in [
        os.path.join("C:\\", "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join("C:\\", "Program Files", "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(userprofile, "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(userprofile, "scoop", "apps", "ffmpeg", "current", "bin", "ffmpeg.exe"),
        os.path.join("C:\\", "ProgramData", "chocolatey", "bin", "ffmpeg.exe"),
    ]:
        if os.path.isfile(candidate):
            try:
                r = subprocess.run([candidate, "-version"], capture_output=True, timeout=5,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
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
    if not b:
        return "???"
    if b >= 1_073_741_824:
        return f"{b / 1_073_741_824:.2f} GB"
    if b >= 1_048_576:
        return f"{b / 1_048_576:.1f} MB"
    return f"{b / 1024:.0f} KB"


def fmt_dur(s):
    if not s:
        return "00:00"
    s = int(s)
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


def clean(n):
    return re.sub(r'[\\/*?:"<>|]', "_", n)[:80]


def get_drive_info(path):
    """Get drive usage info for the given path."""
    try:
        total, used, free = shutil.disk_usage(path)
        return {
            "total": total, "used": used, "free": free,
            "percent_used": (used / total * 100) if total else 0,
        }
    except Exception:
        return None


def base_opts(extra=None):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "socket_timeout": 30,
        "retries": 5,
        "abort_on_unavailable_fragments": False,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
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
    raise last or Exception("All extraction strategies failed.")


RES = {
    2160: ("4K  ·  2160p",    "4K",  H["amber"]),
    1440: ("2K  ·  1440p",    "2K",  H["amber"]),
    1080: ("1080p  FULL HD",  "FHD", H["cyan"]),
    720:  ("720p  HD",        "HD",  H["green"]),
    480:  ("480p  SD",        "SD",  H["green_mid"]),
    360:  ("360p  LOW",       "360", H["green_lo"]),
    240:  ("240p  MIN",       "240", H["dim"]),
    144:  ("144p  MICRO",     "144", H["dim"]),
}


def extract_formats(info):
    """
    Build a list of downloadable format entries.
    
    KEY FIX: When ffmpeg is NOT available, we ONLY offer combined streams
    (video+audio in a single file). Video-only streams would produce
    unplayable files with no audio and sometimes no video in players.
    """
    out, seen = [], set()
    fmts = info.get("formats", [])

    all_video  = [f for f in fmts if f.get("vcodec", "none") != "none" and f.get("height")]
    combined   = [f for f in all_video if f.get("acodec", "none") != "none"]
    video_only = [f for f in all_video if f.get("acodec", "none") == "none"]
    audio_only = sorted(
        [f for f in fmts
         if f.get("vcodec", "none") == "none"
         and f.get("acodec", "none") != "none"],
        key=lambda x: x.get("abr", 0) or 0, reverse=True,
    )
    best_audio_id = audio_only[0]["format_id"] if audio_only else "bestaudio"

    # Group best stream per height
    combined_by_h = {}
    for f in sorted(combined, key=lambda x: (x.get("height", 0), x.get("tbr", 0) or 0), reverse=True):
        h = f.get("height", 0)
        if h not in combined_by_h:
            combined_by_h[h] = f

    vidonly_by_h = {}
    for f in sorted(video_only, key=lambda x: (x.get("height", 0), x.get("tbr", 0) or 0), reverse=True):
        h = f.get("height", 0)
        if h not in vidonly_by_h:
            vidonly_by_h[h] = f

    all_heights = sorted(set(list(combined_by_h) + list(vidonly_by_h)), reverse=True)

    for h in all_heights:
        if h not in RES or h in seen:
            continue
        label, badge, color = RES[h]
        cf = combined_by_h.get(h)
        vf = vidonly_by_h.get(h)

        if FFMPEG_OK:
            # With ffmpeg: prefer video-only + best audio (better quality),
            # fall back to combined
            if vf:
                best_f = vf
                fmt_str = (
                    f"{vf['format_id']}+{best_audio_id}"
                    f"/bestvideo[height<={h}]+bestaudio"
                    f"/best[height<={h}]"
                )
            elif cf:
                best_f = cf
                fmt_str = f"{cf['format_id']}/best[height<={h}]"
            else:
                continue
        else:
            # WITHOUT ffmpeg: ONLY use combined streams (video+audio together)
            # This is the KEY FIX — video-only streams produce broken files
            if cf:
                best_f = cf
                # Prefer mp4 container for maximum compatibility
                fmt_str = (
                    f"{cf['format_id']}"
                    f"/best[height<={h}][ext=mp4]"
                    f"/best[height<={h}]"
                )
            else:
                # No combined stream at this height — skip entirely
                # (video-only would be silent/broken without ffmpeg)
                continue

        fps    = best_f.get("fps", 0) or 0
        vcodec = (best_f.get("vcodec") or "")[:12]
        size   = fmt_bytes(best_f.get("filesize") or best_f.get("filesize_approx"))
        tbr    = best_f.get("tbr", 0) or 0

        seen.add(h)
        out.append({
            "type": "video",
            "label": label,
            "badge": badge,
            "color": color,
            "fps": f"{fps:.0f} fps" if fps else "",
            "bitrate": f"{tbr:.0f} kbps" if tbr else "",
            "size": size,
            "format_str": fmt_str,
            "height": h,
            "vcodec": vcodec,
            "has_audio": True,  # all formats we list now have audio
        })

    # Audio-only formats
    seen_ext = set()
    for f in audio_only:
        ext = f.get("ext", "m4a")
        if ext in seen_ext:
            continue
        seen_ext.add(ext)
        out.append({
            "type": "audio",
            "label": f"Audio  {ext.upper()}",
            "badge": ext.upper(),
            "color": H["purple"],
            "fps": "",
            "bitrate": f"{f.get('abr', 0) or 0:.0f} kbps" if f.get("abr") else "",
            "size": fmt_bytes(f.get("filesize") or f.get("filesize_approx")),
            "format_str": f.get("format_id", "bestaudio"),
            "height": 0,
            "mp3": False,
            "has_audio": True,
        })

    # Best audio option
    if FFMPEG_OK:
        out.append({
            "type": "audio", "label": "Audio  MP3  [ BEST ]", "badge": "MP3",
            "color": H["purple"], "fps": "", "bitrate": "MAX QUALITY",
            "size": "~varies", "format_str": "bestaudio/best", "height": 0,
            "mp3": True, "has_audio": True,
        })
    else:
        out.append({
            "type": "audio", "label": "Audio  M4A  [ BEST ]", "badge": "M4A",
            "color": H["purple"], "fps": "", "bitrate": "MAX QUALITY",
            "size": "~varies", "format_str": "bestaudio[ext=m4a]/bestaudio",
            "height": 0, "mp3": False, "has_audio": True,
        })
    return out


def friendly(raw):
    r = raw.lower()
    if "ffmpeg" in r:
        return "MERGE ENGINE MISSING  —  Install ffmpeg and restart"
    if "ssl" in r or "certificate" in r:
        return "SSL HANDSHAKE FAIL  —  Run:  pip install -U yt-dlp"
    if "sign in" in r or "age" in r:
        return "AGE GATE LOCKED  —  Authentication required"
    if "private" in r:
        return "ACCESS DENIED  —  Private content"
    if "playback on other websites" in r:
        return "EXTERNAL PLAYBACK BLOCKED  —  Owner restriction"
    if "unavailable" in r or "removed" in r:
        return "TARGET OFFLINE  —  Content removed"
    if "requested format is not available" in r:
        return "FORMAT NOT FOUND  —  Try a lower quality"
    if "403" in r or "forbidden" in r:
        return "FIREWALL BLOCK  —  Run:  pip install -U yt-dlp"
    return f"ERROR:  {raw[:160]}"


# ===========================================================================
# MAIN APP — YT-BREACH  (Hacker UI)
# ===========================================================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YT-BREACH  //  INTERCEPT · EXTRACT · OWN")
        self.geometry("960x1020")
        self.minsize(780, 650)
        self.configure(fg_color=H["bg"])

        self._info       = None
        self._formats    = []
        self._sel        = None
        self._save_dir   = os.path.expanduser("~/Downloads")
        self._dl_active  = False
        self._fmt_btns   = []
        self._ci         = None
        self._anim_id    = None
        self._scan_dots  = 0
        self._glitch     = "█▓▒░╠╣╚╗╔╝║═"

        self._boot_sequence()

    # ===================================================================
    # BOOT SEQUENCE
    # ===================================================================
    def _boot_sequence(self):
        self._boot_frame = ctk.CTkFrame(self, fg_color=H["bg"])
        self._boot_frame.pack(fill="both", expand=True)
        self._boot_label = ctk.CTkLabel(
            self._boot_frame, text="",
            font=ctk.CTkFont("Consolas", 12),
            text_color=H["green"], justify="left", anchor="nw",
        )
        self._boot_label.pack(fill="both", expand=True, padx=30, pady=30)

        self._boot_lines = [
            "╔════════════════════════════════════════════════════════╗",
            "║          YT-BREACH  v2.0  —  INITIALIZING             ║",
            "╚════════════════════════════════════════════════════════╝",
            "",
            f"  [SYS]  Platform .......... {sys.platform.upper()}",
            f"  [SYS]  Python ............ {sys.version.split()[0]}",
            f"  [NET]  SSL Bypass ........ ACTIVE",
            f"  [NET]  User-Agent ........ SPOOFED",
            f"  [MOD]  yt-dlp Engine ..... LOADED",
            f"  [MOD]  FFmpeg Codec ...... {'ONLINE' if FFMPEG_OK else 'OFFLINE  (720p MAX)'}",
            f"  [MOD]  PIL Imaging ....... LOADED",
            "",
            "  [SCAN] Probing YouTube endpoints...",
            "  [SCAN] tv_embedded ....... OK",
            "  [SCAN] web_embedded ...... OK",
            "  [SCAN] ios ............... OK",
            "  [SCAN] android ........... OK",
            "",
            "╔════════════════════════════════════════════════════════╗",
            "║   ALL SYSTEMS OPERATIONAL  —  READY TO BREACH         ║",
            "╚════════════════════════════════════════════════════════╝",
        ]
        self._boot_idx = 0
        self._boot_text = ""
        self._tick_boot()

    def _tick_boot(self):
        if self._boot_idx < len(self._boot_lines):
            line = self._boot_lines[self._boot_idx]
            self._boot_text += line + "\n"
            self._boot_label.configure(text=self._boot_text)
            self._boot_idx += 1
            delay = random.randint(40, 90)
            if "[SCAN]" in line and "..." in line:
                delay = random.randint(80, 200)
            self.after(delay, self._tick_boot)
        else:
            self.after(700, self._build_main)

    def _build_main(self):
        self._boot_frame.destroy()
        self._build()

    # ===================================================================
    # BUILD MAIN UI
    # ===================================================================
    def _build(self):
        # ── TOP BAR ──
        top = ctk.CTkFrame(self, fg_color=H["bg2"], corner_radius=0, height=56)
        top.pack(fill="x")
        top.pack_propagate(False)
        ti = ctk.CTkFrame(top, fg_color="transparent")
        ti.pack(fill="both", expand=True, padx=20)

        ctk.CTkLabel(
            ti, text="☠  YT-BREACH",
            font=ctk.CTkFont("Consolas", 22, "bold"), text_color=H["green"],
        ).pack(side="left", pady=10)

        ctk.CTkLabel(
            ti, text="   INTERCEPT · EXTRACT · OWN",
            font=ctk.CTkFont("Consolas", 11), text_color=H["green_lo"],
        ).pack(side="left", pady=10)

        # System status (right side)
        self._sys_label = ctk.CTkLabel(
            ti, text="●  IDLE",
            font=ctk.CTkFont("Consolas", 11, "bold"), text_color=H["dim"],
        )
        self._sys_label.pack(side="right", pady=10)

        # FFmpeg badge
        if FFMPEG_OK:
            ff_txt, ff_c, ff_bg = "FFMPEG : ON", H["green"], H["green_bg"]
        else:
            ff_txt, ff_c, ff_bg = "FFMPEG : OFF", H["amber"], H["amber_bg"]
        ff = ctk.CTkFrame(ti, fg_color=ff_bg, corner_radius=4)
        ff.pack(side="right", padx=14, pady=14)
        ctk.CTkLabel(ff, text=ff_txt, font=ctk.CTkFont("Consolas", 10, "bold"),
                     text_color=ff_c).pack(padx=8, pady=2)

        # Green divider
        ctk.CTkFrame(self, fg_color=H["green_lo"], height=1, corner_radius=0).pack(fill="x")

        # ── SCROLLABLE BODY ──
        self._body = ctk.CTkScrollableFrame(
            self, fg_color=H["bg"], corner_radius=0,
            scrollbar_fg_color=H["bg2"], scrollbar_button_color=H["green_lo"],
        )
        self._body.pack(fill="both", expand=True)

        self._build_target_input()

        # Ordered wrappers
        self._info_wrap = ctk.CTkFrame(self._body, fg_color="transparent")
        self._fmt_wrap  = ctk.CTkFrame(self._body, fg_color="transparent")
        self._dl_wrap   = ctk.CTkFrame(self._body, fg_color="transparent")
        self._info_wrap.pack(fill="x")
        self._fmt_wrap.pack(fill="x")
        self._dl_wrap.pack(fill="x")

        self._info_card = self._card(self._info_wrap)
        self._fmt_card  = self._card(self._fmt_wrap)
        self._dl_card   = self._card(self._dl_wrap)
        self._hide_all()

        # ── BOTTOM BAR ──
        bot = ctk.CTkFrame(self, fg_color=H["bg2"], corner_radius=0, height=30)
        bot.pack(fill="x", side="bottom")
        bot.pack_propagate(False)
        bi = ctk.CTkFrame(bot, fg_color="transparent")
        bi.pack(fill="both", expand=True, padx=16)

        self._bottom_lbl = ctk.CTkLabel(
            bi, text="SYSTEM READY  //  NO TARGET LOADED",
            font=ctk.CTkFont("Consolas", 10), text_color=H["green_lo"],
        )
        self._bottom_lbl.pack(side="left")

        self._clock = ctk.CTkLabel(
            bi, text="", font=ctk.CTkFont("Consolas", 10), text_color=H["green_lo"],
        )
        self._clock.pack(side="right")
        self._tick_clock()

    def _tick_clock(self):
        self._clock.configure(text=time.strftime("LOCAL  %H:%M:%S"))
        self.after(1000, self._tick_clock)

    # ── Card helpers ──
    def _card(self, parent):
        outer = ctk.CTkFrame(parent, fg_color=H["card"], corner_radius=6,
                             border_width=1, border_color=H["border"])
        outer.pack(fill="x", padx=16, pady=(0, 10))
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=14)
        return inner

    def _hide_all(self):
        for wrap in (self._info_wrap, self._fmt_wrap, self._dl_wrap):
            for c in wrap.winfo_children():
                c.pack_forget()

    def _show(self, card):
        card.master.pack(fill="x", padx=16, pady=(0, 10))

    def _heading(self, parent, text, icon="►"):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(row, text=f"{icon}  {text}",
                     font=ctk.CTkFont("Consolas", 12, "bold"),
                     text_color=H["green"]).pack(side="left")
        ctk.CTkFrame(row, fg_color=H["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(12, 0), pady=1)

    # ===================================================================
    # TARGET INPUT
    # ===================================================================
    def _build_target_input(self):
        card = self._card(self._body)
        self._heading(card, "TARGET ACQUISITION", "◉")

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x")

        self._url_var = ctk.StringVar()

        ctk.CTkLabel(row, text="URL >",
                     font=ctk.CTkFont("Consolas", 15, "bold"),
                     text_color=H["green"]).pack(side="left", padx=(0, 8))

        self._entry = ctk.CTkEntry(
            row, textvariable=self._url_var,
            placeholder_text="paste youtube url here...",
            height=48, corner_radius=4,
            fg_color=H["surface"], border_color=H["border"], border_width=1,
            text_color=H["white"], placeholder_text_color=H["dim"],
            font=ctk.CTkFont("Consolas", 14),
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._entry.bind("<Return>", lambda e: self._do_fetch())

        self._fbtn = ctk.CTkButton(
            row, text="⚡ BREACH", width=140, height=48, corner_radius=4,
            fg_color=H["green_bg"], hover_color=H["hover"],
            border_width=1, border_color=H["green"],
            text_color=H["green"], font=ctk.CTkFont("Consolas", 14, "bold"),
            command=self._do_fetch,
        )
        self._fbtn.pack(side="right")

        # Utility buttons
        brow = ctk.CTkFrame(card, fg_color="transparent")
        brow.pack(fill="x", pady=(8, 0))
        for text, cmd in [("📋  PASTE", self._paste), ("✕  CLEAR", self._clear)]:
            ctk.CTkButton(
                brow, text=text, height=28, corner_radius=4,
                fg_color="transparent", hover_color=H["hover"],
                text_color=H["green_mid"], font=ctk.CTkFont("Consolas", 11),
                border_width=1, border_color=H["border"], command=cmd,
            ).pack(side="left", padx=(0, 8))

        # Terminal output
        self._term = ctk.CTkLabel(
            card, text="", font=ctk.CTkFont("Consolas", 11),
            text_color=H["green_mid"], wraplength=860, justify="left", anchor="w",
        )
        self._term.pack(anchor="w", pady=(8, 0))

    def _paste(self):
        try:
            self._url_var.set(self.clipboard_get().strip())
        except Exception:
            pass

    def _clear(self):
        self._url_var.set("")
        self._term.configure(text="")
        self._hide_all()
        self._info = None
        self._formats = []
        self._sel = None
        self._sys_label.configure(text="●  IDLE", text_color=H["dim"])
        self._bottom_lbl.configure(text="SYSTEM READY  //  NO TARGET LOADED")

    def _set_term(self, txt, color=None):
        self._term.configure(text=txt, text_color=color or H["green_mid"])

    # ===================================================================
    # FETCH
    # ===================================================================
    def _do_fetch(self):
        url = self._url_var.get().strip()
        if not url:
            self._set_term("[WARN]  No target URL provided.", H["amber"])
            return
        if "youtube.com" not in url and "youtu.be" not in url:
            self._set_term("[ERR]  Invalid target — YouTube URLs only.", H["red"])
            return

        self._fbtn.configure(text="SCANNING...", state="disabled", fg_color=H["surface"])
        self._sys_label.configure(text="●  BREACHING", text_color=H["amber"])
        self._set_term("[CONN]  Establishing tunnel to YouTube...", H["green_lo"])
        self._hide_all()
        for card in (self._info_card, self._fmt_card, self._dl_card):
            for w in card.winfo_children():
                w.destroy()
        self._start_scan()
        threading.Thread(target=self._fetch_th, args=(url,), daemon=True).start()

    def _start_scan(self):
        self._scan_dots = 0
        self._tick_scan()

    def _tick_scan(self):
        if self._fbtn.cget("state") == "disabled":
            self._scan_dots = (self._scan_dots + 1) % 4
            phases = [
                "Bypassing YouTube firewall",
                "Extracting video manifest",
                "Decrypting stream data",
                "Intercepting format list",
            ]
            phase = phases[self._scan_dots % len(phases)]
            dots = "·" * (self._scan_dots + 1)
            glitch = "".join(random.choice(self._glitch) for _ in range(3))
            self._set_term(f"[SCAN]  {glitch}  {phase} {dots}", H["green_mid"])
            self._anim_id = self.after(400, self._tick_scan)

    def _stop_scan(self):
        if self._anim_id:
            self.after_cancel(self._anim_id)
            self._anim_id = None

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
        self._stop_scan()
        self._fbtn.configure(text="⚡ BREACH", state="normal", fg_color=H["green_bg"])
        self._sys_label.configure(text="●  TARGET ACQUIRED", text_color=H["green"])
        n = len(self._formats)
        self._set_term(
            f"[OK]  Breach successful via [{client}]  —  {n} streams intercepted",
            H["green"],
        )
        title = self._info.get("title", "?")
        self._bottom_lbl.configure(text=f"TARGET:  {title[:55]}")
        self._show_intel()

    def _fetch_fail(self, msg):
        self._stop_scan()
        self._fbtn.configure(text="⚡ BREACH", state="normal", fg_color=H["green_bg"])
        self._sys_label.configure(text="●  BREACH FAILED", text_color=H["red"])
        self._set_term(f"[FAIL]  {msg}", H["red"])

    # ===================================================================
    # VIDEO INFO (Intel)
    # ===================================================================
    def _show_intel(self):
        f = self._info_card
        for w in f.winfo_children():
            w.destroy()
        self._show(f)
        info = self._info

        self._heading(f, "TARGET INTEL", "◈")

        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x")

        # Thumbnail
        thumb = ctk.CTkFrame(row, fg_color=H["surface"], corner_radius=4,
                             width=210, height=118, border_width=1, border_color=H["border"])
        thumb.pack(side="left", padx=(0, 16))
        thumb.pack_propagate(False)
        ctk.CTkLabel(thumb, text="▶  PREVIEW", font=ctk.CTkFont("Consolas", 10),
                     text_color=H["dim"]).place(relx=0.5, rely=0.5, anchor="center")

        t_url = info.get("thumbnail", "")
        if t_url:
            threading.Thread(target=self._load_thumb, args=(t_url, thumb), daemon=True).start()

        # Meta
        meta = ctk.CTkFrame(row, fg_color="transparent")
        meta.pack(side="left", fill="both", expand=True)

        # Title — bright white for max readability
        ctk.CTkLabel(
            meta, text=info.get("title", "UNKNOWN"),
            font=ctk.CTkFont("Consolas", 14, "bold"),
            text_color=H["white"], wraplength=600, justify="left", anchor="w",
        ).pack(anchor="w", pady=(0, 8))

        d = info.get("upload_date", "")
        date_str = f"{d[:4]}-{d[4:6]}-{d[6:]}" if len(d) == 8 else d
        dur = info.get("duration")
        views = info.get("view_count", 0)
        uploader = info.get("uploader") or info.get("channel", "?")

        lines = [
            ("DURATION", fmt_dur(dur)),
            ("CHANNEL", uploader),
            ("VIEWS", f"{views:,}" if views else None),
            ("UPLOADED", date_str if date_str else None),
            ("VIDEO ID", info.get("id", "?")),
        ]
        for lbl, val in lines:
            if not val:
                continue
            r2 = ctk.CTkFrame(meta, fg_color="transparent")
            r2.pack(anchor="w", fill="x", pady=1)
            ctk.CTkLabel(
                r2, text=f"  {lbl}",
                font=ctk.CTkFont("Consolas", 11, "bold"), text_color=H["green_mid"],
                width=100, anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                r2, text=f":   {val}",
                font=ctk.CTkFont("Consolas", 11), text_color=H["off_white"],
            ).pack(side="left")

        self._show_streams()

    def _load_thumb(self, url, frame):
        try:
            r = requests.get(url, timeout=8, verify=False)
            r.raise_for_status()
            img = Image.open(BytesIO(r.content)).resize((210, 118), Image.LANCZOS)
            # Light green tint
            overlay = Image.new("RGBA", img.size, (0, 255, 65, 25))
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, overlay).convert("RGB")
            ci = ctk.CTkImage(img, size=(210, 118))
            self._ci = ci
            lbl = ctk.CTkLabel(frame, image=ci, text="")
            self.after(0, lambda: lbl.place(relx=0, rely=0, relwidth=1, relheight=1))
        except Exception:
            pass

    # ===================================================================
    # STREAM LIST
    # ===================================================================
    def _show_streams(self):
        f = self._fmt_card
        for w in f.winfo_children():
            w.destroy()
        self._show(f)
        self._fmt_btns = []
        self._sel = None

        self._heading(f, "INTERCEPTED STREAMS", "◆")

        if not FFMPEG_OK:
            warn = ctk.CTkFrame(f, fg_color=H["amber_bg"], corner_radius=4,
                                border_width=1, border_color="#4a3300")
            warn.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(
                warn,
                text="⚠  FFMPEG OFFLINE  —  Only combined streams (with audio) are shown.\n"
                     "    Install ffmpeg to unlock 1080p / 4K qualities.",
                font=ctk.CTkFont("Consolas", 10), text_color=H["amber"],
                wraplength=800, justify="left",
            ).pack(padx=12, pady=8, anchor="w")

        vfmts = [x for x in self._formats if x["type"] == "video"]
        afmts = [x for x in self._formats if x["type"] == "audio"]

        if vfmts:
            ctk.CTkLabel(f, text="── VIDEO STREAMS ──────────────────────",
                         font=ctk.CTkFont("Consolas", 10, "bold"),
                         text_color=H["green_lo"]).pack(anchor="w", pady=(0, 6))
            for fmt in vfmts:
                self._stream_row(f, fmt)

        if afmts:
            ctk.CTkLabel(f, text="── AUDIO STREAMS ──────────────────────",
                         font=ctk.CTkFont("Consolas", 10, "bold"),
                         text_color=H["green_lo"]).pack(anchor="w", pady=(12, 6))
            for fmt in afmts:
                self._stream_row(f, fmt)

        self._build_extract()

    def _stream_row(self, parent, fmt):
        fr = ctk.CTkFrame(parent, fg_color=H["surface"], corner_radius=4,
                          border_width=1, border_color=H["border"])
        fr.pack(fill="x", pady=3)

        # Badge
        ctk.CTkLabel(
            fr, text=f"  {fmt['badge']}  ",
            font=ctk.CTkFont("Consolas", 10, "bold"),
            text_color=H["bg"], fg_color=fmt.get("color", H["green"]),
            corner_radius=3, width=50, height=22,
        ).pack(side="left", padx=(10, 10), pady=10)

        # Label — bright and readable
        ctk.CTkLabel(
            fr, text=fmt["label"],
            font=ctk.CTkFont("Consolas", 12, "bold"), text_color=H["white"], anchor="w",
        ).pack(side="left", padx=4)

        # Codec
        if fmt.get("vcodec"):
            ctk.CTkLabel(
                fr, text=f"[{fmt['vcodec']}]",
                font=ctk.CTkFont("Consolas", 9), text_color=H["green_lo"],
            ).pack(side="left", padx=4)

        ctk.CTkFrame(fr, fg_color="transparent").pack(side="left", expand=True)

        # Details — larger, readable
        parts = [p for p in [fmt.get("fps", ""), fmt.get("bitrate", ""), fmt.get("size", "")] if p]
        details = "  ·  ".join(parts)
        if details:
            ctk.CTkLabel(
                fr, text=details,
                font=ctk.CTkFont("Consolas", 10), text_color=H["green_mid"],
            ).pack(side="left", padx=8)

        btn = ctk.CTkButton(
            fr, text="► SELECT", width=100, height=30, corner_radius=4,
            fg_color="transparent", border_width=1, border_color=H["border"],
            hover_color=H["hover"], text_color=H["green_mid"],
            font=ctk.CTkFont("Consolas", 10, "bold"),
        )
        btn.pack(side="right", padx=10, pady=8)
        btn.configure(command=lambda _f=fmt, _b=btn, _fr=fr: self._pick(_f, _b, _fr))
        self._fmt_btns.append((btn, fr))

    def _pick(self, f, b, fr):
        for btn, frame in self._fmt_btns:
            btn.configure(text="► SELECT", fg_color="transparent",
                          text_color=H["green_mid"], border_color=H["border"])
            frame.configure(border_color=H["border"])

        self._sel = f
        b.configure(text="✓ LOCKED", fg_color=H["green_bg"],
                    text_color=H["green"], border_color=H["green"])
        fr.configure(border_color=H["green"])

        ext = "MP4" if f["type"] == "video" else f.get("badge", "")
        self._extract_btn.configure(
            text=f"⚡  EXTRACT   {f['label']}   [{ext}]",
            fg_color=H["green_bg"], hover_color=H["hover"],
            text_color=H["green"], state="normal", border_color=H["green"],
        )

    # ===================================================================
    # EXTRACTION PANEL
    # ===================================================================
    def _build_extract(self):
        f = self._dl_card
        for w in f.winfo_children():
            w.destroy()
        self._show(f)

        self._heading(f, "EXTRACTION  //  SAVE TARGET", "◉")

        # ── Save location ──
        loc = ctk.CTkFrame(f, fg_color=H["surface"], corner_radius=4,
                           border_width=1, border_color=H["border"])
        loc.pack(fill="x", pady=(0, 8))
        li = ctk.CTkFrame(loc, fg_color="transparent")
        li.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(li, text="SAVE PATH >",
                     font=ctk.CTkFont("Consolas", 11, "bold"),
                     text_color=H["green"]).pack(side="left", padx=(0, 8))

        self._dir_var = ctk.StringVar(value=self._save_dir)
        ctk.CTkEntry(
            li, textvariable=self._dir_var, height=34, corner_radius=4,
            fg_color=H["card"], border_color=H["border"],
            text_color=H["off_white"], font=ctk.CTkFont("Consolas", 11),
        ).pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            li, text="📂  BROWSE", width=110, height=34, corner_radius=4,
            fg_color=H["green_bg"], hover_color=H["hover"],
            border_width=1, border_color=H["green_lo"],
            text_color=H["green"], font=ctk.CTkFont("Consolas", 11, "bold"),
            command=self._browse,
        ).pack(side="right")

        # Quick dirs
        qr = ctk.CTkFrame(f, fg_color="transparent")
        qr.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(qr, text="QUICK :",
                     font=ctk.CTkFont("Consolas", 10, "bold"),
                     text_color=H["green_lo"]).pack(side="left", padx=(0, 8))
        for label, path in [
            ("Downloads", os.path.expanduser("~/Downloads")),
            ("Desktop",   os.path.expanduser("~/Desktop")),
            ("Videos",    os.path.expanduser("~/Videos")),
            ("Music",     os.path.expanduser("~/Music")),
        ]:
            if os.path.isdir(path):
                ctk.CTkButton(
                    qr, text=label, height=24, corner_radius=4,
                    fg_color="transparent", border_width=1, border_color=H["border"],
                    hover_color=H["hover"], text_color=H["green_mid"],
                    font=ctk.CTkFont("Consolas", 10),
                    command=lambda p=path: self._set_dir(p),
                ).pack(side="left", padx=(0, 6))

        # ── Drive storage ──
        self._storage_frame = ctk.CTkFrame(f, fg_color=H["surface"], corner_radius=4,
                                            border_width=1, border_color=H["border"])
        self._storage_frame.pack(fill="x", pady=(0, 10))
        self._storage_inner = ctk.CTkFrame(self._storage_frame, fg_color="transparent")
        self._storage_inner.pack(fill="x", padx=12, pady=8)
        self._update_storage()

        # ── Progress area (hidden initially) ──
        self._prog_frame = ctk.CTkFrame(f, fg_color=H["surface"], corner_radius=4,
                                         border_width=1, border_color=H["border"])

        # ── Extract button ──
        self._extract_btn = ctk.CTkButton(
            f, text="⬇  SELECT A STREAM FIRST",
            height=54, corner_radius=4,
            fg_color=H["surface"], hover_color=H["hover"],
            border_width=1, border_color=H["border"],
            text_color=H["dim"], state="disabled",
            font=ctk.CTkFont("Consolas", 14, "bold"),
            command=self._start_dl,
        )
        self._extract_btn.pack(fill="x", pady=(4, 0))

        # Open folder (hidden)
        self._open_btn = ctk.CTkButton(
            f, text="📂  OPEN TARGET FOLDER",
            height=38, corner_radius=4,
            fg_color="transparent", hover_color=H["hover"],
            border_width=1, border_color=H["green"],
            text_color=H["green"], font=ctk.CTkFont("Consolas", 12, "bold"),
            command=self._open_folder,
        )

    def _update_storage(self):
        for w in self._storage_inner.winfo_children():
            w.destroy()

        path = self._dir_var.get().strip() if hasattr(self, "_dir_var") else self._save_dir
        info = get_drive_info(path)

        if info:
            total_gb = info["total"] / (1024 ** 3)
            free_gb  = info["free"] / (1024 ** 3)
            pct      = info["percent_used"]
            drive    = os.path.splitdrive(path)[0] or path[:3]

            # Color based on space
            if free_gb < 1:
                c, icon = H["red"], "⚠"
            elif free_gb < 5:
                c, icon = H["amber"], "!"
            else:
                c, icon = H["green"], "✓"

            row1 = ctk.CTkFrame(self._storage_inner, fg_color="transparent")
            row1.pack(fill="x")

            ctk.CTkLabel(
                row1, text=f"💾  DRIVE  [ {drive} ]",
                font=ctk.CTkFont("Consolas", 11, "bold"), text_color=H["green"],
            ).pack(side="left")

            ctk.CTkLabel(
                row1,
                text=f"{icon}  FREE :  {free_gb:.1f} GB  /  {total_gb:.1f} GB   ({100 - pct:.1f}% available)",
                font=ctk.CTkFont("Consolas", 11), text_color=c,
            ).pack(side="right")

            # Bar
            bar = ctk.CTkFrame(self._storage_inner, fg_color=H["bg"], height=10, corner_radius=3)
            bar.pack(fill="x", pady=(6, 0))
            bar.pack_propagate(False)

            bar_c = H["green"] if pct < 70 else (H["amber"] if pct < 90 else H["red"])
            ctk.CTkFrame(bar, fg_color=bar_c, corner_radius=3).place(
                relx=0, rely=0, relwidth=min(pct / 100, 1.0), relheight=1.0)
        else:
            ctk.CTkLabel(
                self._storage_inner, text="💾  DRIVE INFO :  UNAVAILABLE",
                font=ctk.CTkFont("Consolas", 11), text_color=H["dim"],
            ).pack(anchor="w")

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self._save_dir)
        if d:
            self._save_dir = d
            self._dir_var.set(d)
            self._update_storage()

    def _set_dir(self, path):
        self._save_dir = path
        self._dir_var.set(path)
        self._update_storage()

    def _open_folder(self):
        path = self._dir_var.get().strip() or self._save_dir
        if os.path.isdir(path):
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])

    # ===================================================================
    # DOWNLOAD
    # ===================================================================
    def _start_dl(self):
        if self._dl_active or not self._sel:
            return
        save = self._dir_var.get().strip() or os.path.expanduser("~/Downloads")
        os.makedirs(save, exist_ok=True)
        self._dl_active = True
        self._open_btn.pack_forget()

        self._extract_btn.configure(
            text="⏳  EXTRACTING DATA...", state="disabled",
            fg_color=H["surface"], border_color=H["amber"], text_color=H["amber"],
        )
        self._sys_label.configure(text="●  EXTRACTING", text_color=H["amber"])

        # Build progress HUD
        self._prog_frame.pack(fill="x", pady=(0, 8))
        for w in self._prog_frame.winfo_children():
            w.destroy()
        pi = ctk.CTkFrame(self._prog_frame, fg_color="transparent")
        pi.pack(fill="x", padx=14, pady=12)

        self._prog_hdr = ctk.CTkLabel(
            pi, text="[EXTRACT]  Initiating data stream...",
            font=ctk.CTkFont("Consolas", 11, "bold"), text_color=H["green"],
        )
        self._prog_hdr.pack(anchor="w")

        # Bar
        self._prog = ctk.CTkProgressBar(pi, height=14, corner_radius=3,
                                         fg_color=H["bg"], progress_color=H["green"])
        self._prog.pack(fill="x", pady=(8, 6))
        self._prog.set(0)

        # Big percentage
        self._pct_lbl = ctk.CTkLabel(
            pi, text="0 %",
            font=ctk.CTkFont("Consolas", 28, "bold"), text_color=H["green"],
        )
        self._pct_lbl.pack(anchor="w", pady=(2, 6))

        # Stats grid
        stats = ctk.CTkFrame(pi, fg_color="transparent")
        stats.pack(fill="x")

        labels = ["DOWNLOADED", "TOTAL SIZE", "SPEED", "ETA", "ELAPSED"]
        self._stat_vars = {}
        for lbl in labels:
            r = ctk.CTkFrame(stats, fg_color="transparent")
            r.pack(anchor="w", fill="x", pady=1)
            ctk.CTkLabel(
                r, text=f"  {lbl:12s}:",
                font=ctk.CTkFont("Consolas", 11, "bold"), text_color=H["green_mid"],
                width=140, anchor="w",
            ).pack(side="left")
            v = ctk.CTkLabel(
                r, text="---",
                font=ctk.CTkFont("Consolas", 11), text_color=H["off_white"],
            )
            v.pack(side="left")
            self._stat_vars[lbl] = v

        # Binary stream viz
        self._stream_viz = ctk.CTkLabel(
            pi, text="",
            font=ctk.CTkFont("Consolas", 9), text_color=H["green_lo"],
        )
        self._stream_viz.pack(anchor="w", pady=(6, 0))

        self._dl_start = time.time()
        self._tick_elapsed()

        threading.Thread(target=self._dl_th, args=(self._sel, save), daemon=True).start()

    def _tick_elapsed(self):
        if not self._dl_active:
            return
        elapsed = time.time() - self._dl_start
        m, s = divmod(int(elapsed), 60)
        h, m = divmod(m, 60)
        if h:
            self._stat_vars["ELAPSED"].configure(text=f"{h:02d}:{m:02d}:{s:02d}")
        else:
            self._stat_vars["ELAPSED"].configure(text=f"{m:02d}:{s:02d}")

        # Data stream viz
        stream = "".join(random.choice("01") for _ in range(48))
        blocks = "  ".join(stream[i:i + 8] for i in range(0, 48, 8))
        self._stream_viz.configure(text=f"DATA :  {blocks}")

        self.after(1000, self._tick_elapsed)

    def _dl_th(self, fmt, save):
        url   = self._url_var.get().strip()
        title = clean(self._info.get("title", "video"))

        def hook(d):
            if d["status"] == "downloading":
                try:
                    pct = float(d.get("_percent_str", "0%").strip().rstrip("%")) / 100
                except (ValueError, TypeError):
                    pct = 0

                downloaded = d.get("_downloaded_bytes_str", "").strip() or "---"
                total      = (d.get("_total_bytes_str", "")
                              or d.get("_total_bytes_estimate_str", "")).strip() or "---"
                speed      = d.get("_speed_str", "").strip() or "---"
                eta        = d.get("_eta_str", "").strip() or "---"
                pct_int    = int(pct * 100)

                glitch = "".join(random.choice(self._glitch) for _ in range(2))
                header = f"[EXTRACT]  {glitch}  Stream capture in progress..."

                def upd(p=pct, pi=pct_int, dl=downloaded, tt=total,
                        sp=speed, et=eta, hd=header):
                    self._prog.set(p)
                    self._pct_lbl.configure(text=f"{pi} %")
                    self._prog_hdr.configure(text=hd)
                    self._stat_vars["DOWNLOADED"].configure(text=dl)
                    self._stat_vars["TOTAL SIZE"].configure(text=tt)
                    self._stat_vars["SPEED"].configure(text=sp)
                    self._stat_vars["ETA"].configure(text=et)

                self.after(0, upd)

            elif d["status"] == "finished":
                def fin():
                    self._prog.set(1.0)
                    self._pct_lbl.configure(text="100 %")
                    self._prog_hdr.configure(
                        text="[MERGE]  Combining video + audio streams...",
                        text_color=H["cyan"],
                    )
                    self._stat_vars["SPEED"].configure(text="MERGING")
                    self._stat_vars["ETA"].configure(text="Processing...")
                self.after(0, fin)

        opts = base_opts({"progress_hooks": [hook]})
        opts["outtmpl"] = os.path.join(save, f"{title}.%(ext)s")

        if fmt.get("mp3"):
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3", "preferredquality": "192",
            }]
        elif fmt["type"] == "audio":
            opts["format"] = fmt["format_str"]
        else:
            # VIDEO: use the format string we built
            opts["format"] = fmt["format_str"]
            if FFMPEG_OK:
                opts["merge_output_format"] = "mp4"
            else:
                # Force mp4 extension for compatibility
                opts["prefer_free_formats"] = False

        success, last_err = False, Exception("unknown")
        for client in CLIENTS:
            o = dict(opts)
            o["extractor_args"] = {"youtube": {"player_client": client}}
            try:
                with yt_dlp.YoutubeDL(o) as ydl:
                    ydl.download([url])
                success = True
                break
            except Exception as e:
                last_err = e
                if "ffmpeg" in str(e).lower():
                    break
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
        elapsed = time.time() - self._dl_start
        m, s = divmod(int(elapsed), 60)

        self._prog.configure(progress_color=H["green"])
        self._pct_lbl.configure(text="✓  DONE", text_color=H["green"])
        self._prog_hdr.configure(
            text=f"[COMPLETE]  Extraction successful  —  {m}m {s}s",
            text_color=H["green"],
        )
        self._stat_vars["SPEED"].configure(text="COMPLETE")
        self._stat_vars["ETA"].configure(text="00:00")
        self._stream_viz.configure(
            text="DATA :  TRANSFER COMPLETE  ████████████████████",
            text_color=H["green"],
        )

        self._sys_label.configure(text="●  EXTRACTED", text_color=H["green"])
        self._bottom_lbl.configure(text=f"SAVED :  {save}")

        self._extract_btn.configure(
            text="✓  EXTRACTION COMPLETE  //  CLICK TO RE-EXTRACT",
            fg_color=H["green_bg"], hover_color=H["hover"],
            border_color=H["green"], text_color=H["green"],
            state="normal", command=self._reset_dl,
        )
        self._open_btn.pack(fill="x", pady=(8, 0))
        self._update_storage()

        messagebox.showinfo(
            "Extraction Complete",
            f"☠  Data extracted successfully!\n\nSaved to:\n{save}\n\nTime: {m}m {s}s",
        )

    def _reset_dl(self):
        self._prog_frame.pack_forget()
        self._open_btn.pack_forget()
        if self._sel:
            ext = "MP4" if self._sel["type"] == "video" else self._sel.get("badge", "")
            self._extract_btn.configure(
                text=f"⚡  EXTRACT   {self._sel['label']}   [{ext}]",
                fg_color=H["green_bg"], hover_color=H["hover"],
                text_color=H["green"], state="normal",
                border_color=H["green"], command=self._start_dl,
            )
        else:
            self._extract_btn.configure(
                text="⬇  SELECT A STREAM FIRST",
                fg_color=H["surface"], text_color=H["dim"],
                state="disabled", command=self._start_dl,
            )
        self._sys_label.configure(text="●  TARGET ACQUIRED", text_color=H["green"])

    def _dl_fail(self, msg):
        self._dl_active = False
        self._prog.configure(progress_color=H["red"])
        self._pct_lbl.configure(text="✗  FAIL", text_color=H["red"])
        self._prog_hdr.configure(text=f"[ERROR]  {msg[:80]}", text_color=H["red"])
        self._stream_viz.configure(
            text="DATA :  CONNECTION LOST  ████████░░░░░░░░░░░░",
            text_color=H["red"],
        )
        self._sys_label.configure(text="●  EXTRACTION FAILED", text_color=H["red"])
        self._extract_btn.configure(
            text="✗  FAILED  —  CLICK TO RETRY",
            fg_color=H["red_bg"], hover_color="#4a0020",
            border_color=H["red"], text_color=H["red"],
            state="normal", command=self._start_dl,
        )
        messagebox.showerror("Extraction Failed", f"☠  {msg}")


# ===========================================================================
if __name__ == "__main__":
    App().mainloop()