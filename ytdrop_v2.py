"""
YTDROP PRO V2 — Browse YouTube + Download

INSTALL:
    pip install customtkinter yt-dlp Pillow requests tkwebview2

"""
import sys
sys.coinit_flags = 2  # COINIT_APARTMENTTHREADED

import customtkinter as ctk
import yt_dlp, threading, os, re, ssl, sys, time, shutil, subprocess
from tkinter import filedialog, messagebox

ssl._create_default_https_context = ssl._create_unverified_context
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── PALETTE ──
P = {
    "bg":"#050505","bg2":"#0a0a0a","card":"#121212","card2":"#181818",
    "surface":"#1f1f1f","hover":"#2c2c2e","border":"#2c2c2e","border_hi":"#3a3a3c",
    "accent":"#0a84ff","accent_hi":"#409cff","accent_dim":"#002A5A",
    "accent2":"#5e5ce6","success":"#32d74b","success_dim":"#0f3d1b",
    "warn":"#ff9f0a","warn_dim":"#3b2300","error":"#ff453a","error_dim":"#4a0e0b",
    "cyan":"#64d2ff","pink":"#ff375f","white":"#ffffff",
    "text":"#ebebf5","text2":"#c7c7cc","text3":"#8e8e93","dim":"#636366",
}

# ── FFmpeg ──
def _find_ffmpeg():
    p = shutil.which("ffmpeg")
    if p: return p
    local = os.environ.get("LOCALAPPDATA","")
    user = os.path.expanduser("~")
    cf = getattr(subprocess,"CREATE_NO_WINDOW",0)
    for base in [
        os.path.join(local,"Microsoft","WinGet","Packages"),
    ]:
        if os.path.isdir(base):
            for dp,dn,fn in os.walk(base):
                if dp[len(base):].count(os.sep)>5: dn.clear(); continue
                if "ffmpeg.exe" in fn:
                    c=os.path.join(dp,"ffmpeg.exe")
                    try:
                        if subprocess.run([c,"-version"],capture_output=True,timeout=5,creationflags=cf).returncode==0: return c
                    except: pass
    for c in [
        os.path.join("C:\\","ffmpeg","bin","ffmpeg.exe"),
        os.path.join("C:\\","Program Files","ffmpeg","bin","ffmpeg.exe"),
        os.path.join(user,"ffmpeg","bin","ffmpeg.exe"),
        os.path.join(user,"scoop","apps","ffmpeg","current","bin","ffmpeg.exe"),
    ]:
        if os.path.isfile(c):
            try:
                if subprocess.run([c,"-version"],capture_output=True,timeout=5,creationflags=cf).returncode==0: return c
            except: pass
    return None

FFMPEG_PATH = _find_ffmpeg()
FFMPEG_OK = FFMPEG_PATH is not None
CLIENTS = [["tv_embedded"],["web_embedded"],["ios"],["android"],["mweb"],["web"]]

def fmt_bytes(b):
    if not b: return "—"
    if b>=1_073_741_824: return f"{b/1_073_741_824:.2f} GB"
    if b>=1_048_576: return f"{b/1_048_576:.1f} MB"
    return f"{b/1024:.0f} KB"

def fmt_dur(s):
    if not s: return "0:00"
    s=int(s); h,r=divmod(s,3600); m,sec=divmod(r,60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

def clean(n): return re.sub(r'[\\/*?:"<>|]',"_",n)[:80]

def base_opts(extra=None):
    opts={"quiet":True,"no_warnings":True,"nocheckcertificate":True,"color":"no_color",
          "socket_timeout":30,"retries":5,"abort_on_unavailable_fragments":False,
          "http_headers":{"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36","Accept-Language":"en-US,en;q=0.9"}}
    if FFMPEG_PATH: opts["ffmpeg_location"]=os.path.dirname(FFMPEG_PATH)
    if extra: opts.update(extra)
    return opts

def fetch_robust(url):
    last=None
    for client in CLIENTS:
        opts=base_opts({"extractor_args":{"youtube":{"player_client":client}}})
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info=ydl.extract_info(url,download=False)
            if info and info.get("title"): return info,client[0]
        except Exception as e: last=e
    try:
        with yt_dlp.YoutubeDL(base_opts()) as ydl:
            info=ydl.extract_info(url,download=False)
        if info and info.get("title"): return info,"default"
    except Exception as e: last=e
    raise last or Exception("All extraction strategies failed.")

QUAL={2160:("4K Ultra HD","4K",P["warn"]),1440:("2K QHD","2K",P["warn"]),
      1080:("1080p Full HD","FHD",P["accent"]),720:("720p HD","HD",P["cyan"]),
      480:("480p SD","SD",P["text2"]),360:("360p","360",P["text3"]),
      240:("240p","240",P["dim"]),144:("144p","144",P["dim"])}

def extract_formats(info):
    out,seen=[],set()
    fmts=info.get("formats",[])
    all_video=[f for f in fmts if f.get("vcodec","none")!="none" and f.get("height")]
    combined=[f for f in all_video if f.get("acodec","none")!="none"]
    video_only=[f for f in all_video if f.get("acodec","none")=="none"]
    audio_only=sorted([f for f in fmts if f.get("vcodec","none")=="none" and f.get("acodec","none")!="none"],key=lambda x:x.get("abr",0) or 0,reverse=True)
    combined_by_h,vidonly_by_h={},{}
    for f in sorted(combined,key=lambda x:(x.get("height",0),x.get("tbr",0) or 0),reverse=True):
        h=f.get("height",0)
        if h not in combined_by_h: combined_by_h[h]=f
    for f in sorted(video_only,key=lambda x:(x.get("height",0),x.get("tbr",0) or 0),reverse=True):
        h=f.get("height",0)
        if h not in vidonly_by_h: vidonly_by_h[h]=f
    for h in sorted(set(list(combined_by_h)+list(vidonly_by_h)),reverse=True):
        if h not in QUAL or h in seen: continue
        label,badge,color=QUAL[h]; cf=combined_by_h.get(h); vf=vidonly_by_h.get(h)
        if FFMPEG_OK:
            if vf:
                best_f=vf; fmt_str=f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={h}]+bestaudio/best[height<={h}]"
            elif cf:
                best_f=cf; fmt_str=f"best[height<={h}][ext=mp4]/best[height<={h}]"
            else: continue
        else:
            if cf: best_f=cf; fmt_str=f"best[height<={h}][ext=mp4]/best[height<={h}]"
            else: continue
        fps=best_f.get("fps",0) or 0; vcodec=(best_f.get("vcodec") or "")[:12]
        size=fmt_bytes(best_f.get("filesize") or best_f.get("filesize_approx"))
        tbr=best_f.get("tbr",0) or 0; seen.add(h)
        out.append({"type":"video","label":label,"badge":badge,"color":color,
            "fps":f"{fps:.0f} fps" if fps else "","bitrate":f"{tbr:.0f} kbps" if tbr else "",
            "size":size,"format_str":fmt_str,"height":h,"vcodec":vcodec})
    seen_ext=set()
    for f in audio_only:
        ext=f.get("ext","m4a")
        if ext in seen_ext: continue
        seen_ext.add(ext)
        out.append({"type":"audio","label":f"Audio · {ext.upper()}","badge":ext.upper(),
            "color":P["pink"],"fps":"","bitrate":f"{f.get('abr',0) or 0:.0f} kbps" if f.get("abr") else "",
            "size":fmt_bytes(f.get("filesize") or f.get("filesize_approx")),
            "format_str":f.get("format_id","bestaudio"),"height":0,"mp3":False})
    if FFMPEG_OK:
        out.append({"type":"audio","label":"Audio · MP3 (Best)","badge":"MP3","color":P["pink"],"fps":"","bitrate":"Best","size":"~varies","format_str":"bestaudio/best","height":0,"mp3":True})
    else:
        out.append({"type":"audio","label":"Audio · M4A (Best)","badge":"M4A","color":P["pink"],"fps":"","bitrate":"Best","size":"~varies","format_str":"bestaudio[ext=m4a]/bestaudio","height":0,"mp3":False})
    return out

def friendly(raw):
    r=raw.lower()
    if "ffmpeg" in r: return "FFmpeg required. Install: winget install ffmpeg"
    if "ssl" in r or "certificate" in r: return "SSL error — update yt-dlp"
    if "sign in" in r or "age" in r: return "Age-restricted content"
    if "private" in r: return "This video is private"
    if "unavailable" in r or "removed" in r: return "Video unavailable"
    if "403" in r: return "Blocked — update: pip install -U yt-dlp"
    return f"Error: {raw[:180]}"


# ===========================================================================
# MAIN APP — YTDROP PRO V2 (Browser + Downloader)
# ===========================================================================
class BrowserApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YTDROP PRO V2 — YouTube Browser + Downloader")
        self.geometry("1100x780")
        self.minsize(900,600)
        self.configure(fg_color=P["bg"])
        self._info=None; self._formats=[]; self._sel=None
        self._save_dir=os.path.expanduser("~/Downloads")
        self._dl_active=False; self._fmt_btns=[]; self._dl_start=0
        self._cancel_flag=False; self._pause_flag=False
        self._current_url="https://www.youtube.com"
        self._is_video=False; self._panel_open=False
        # Persistent cookie dir so Google login persists
        self._user_data=os.path.join(os.environ.get("LOCALAPPDATA",os.path.expanduser("~")),"YTDrop_V2_Data")
        os.makedirs(self._user_data,exist_ok=True)
        self._build()
        self.protocol("WM_DELETE_WINDOW",self._on_close)

    def _on_close(self):
        try:
            if hasattr(self,"_browser"): self._browser.destroy()
        except: pass
        self.destroy()

    def _build(self):
        # ── HEADER ──
        hdr=ctk.CTkFrame(self,fg_color=P["bg2"],corner_radius=0,height=50)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        hi=ctk.CTkFrame(hdr,fg_color="transparent")
        hi.pack(fill="both",expand=True,padx=12)

        ctk.CTkLabel(hi,text="▶ YTDROP",font=ctk.CTkFont("Segoe UI",18,"bold"),text_color=P["accent_hi"]).pack(side="left",pady=8)
        ctk.CTkLabel(hi,text=" V2",font=ctk.CTkFont("Segoe UI",10,"bold"),text_color=P["text3"]).pack(side="left",pady=12)

        # Status
        self._status=ctk.CTkLabel(hi,text="Ready",font=ctk.CTkFont("Segoe UI",10),text_color=P["text3"])
        self._status.pack(side="right",padx=8)

        # FFmpeg badge
        ft,fc,fb=("✓ FFmpeg",P["success"],P["success_dim"]) if FFMPEG_OK else ("✗ FFmpeg",P["warn"],P["warn_dim"])
        ff=ctk.CTkFrame(hi,fg_color=fb,corner_radius=6); ff.pack(side="right",pady=12)
        ctk.CTkLabel(ff,text=ft,font=ctk.CTkFont("Segoe UI",9,"bold"),text_color=fc).pack(padx=8,pady=2)

        ctk.CTkFrame(self,fg_color=P["accent"],height=2,corner_radius=0).pack(fill="x")

        # ── NAV BAR ──
        nav=ctk.CTkFrame(self,fg_color=P["card"],corner_radius=0,height=44)
        nav.pack(fill="x"); nav.pack_propagate(False)
        ni=ctk.CTkFrame(nav,fg_color="transparent"); ni.pack(fill="both",expand=True,padx=10)

        for txt,cmd in [("←",self._go_back),("→",self._go_fwd),("⌂",self._go_home)]:
            ctk.CTkButton(ni,text=txt,width=36,height=32,corner_radius=8,fg_color=P["surface"],
                hover_color=P["hover"],text_color=P["text"],font=ctk.CTkFont("Segoe UI",14),
                command=cmd).pack(side="left",padx=2,pady=6)

        self._url_var=ctk.StringVar(value="https://www.youtube.com")
        self._url_entry=ctk.CTkEntry(ni,textvariable=self._url_var,height=32,corner_radius=8,
            fg_color=P["surface"],border_color=P["border"],border_width=1,
            text_color=P["white"],font=ctk.CTkFont("Segoe UI",11))
        self._url_entry.pack(side="left",fill="x",expand=True,padx=8,pady=6)
        self._url_entry.bind("<Return>",lambda e:self._nav_to_url())

        self._dl_toggle=ctk.CTkButton(ni,text="⬇ Download",width=110,height=32,corner_radius=8,
            fg_color=P["surface"],hover_color=P["hover"],text_color=P["dim"],
            font=ctk.CTkFont("Segoe UI",11,"bold"),state="disabled",command=self._toggle_panel)
        self._dl_toggle.pack(side="right",padx=2,pady=6)

        # ── BROWSER ──
        self._browser_frame=ctk.CTkFrame(self,fg_color=P["bg"],corner_radius=0)
        self._browser_frame.pack(fill="both",expand=True)

        # Import and create WebView2
        from tkwebview2.tkwebview2 import WebView2
        self._browser=WebView2(self._browser_frame,width=1080,height=500,
            url="https://www.youtube.com")
        self._browser.pack(fill="both",expand=True)

        # ── DOWNLOAD PANEL (hidden initially) ──
        self._panel=ctk.CTkFrame(self,fg_color=P["card"],corner_radius=0)
        self._panel_scroll=ctk.CTkScrollableFrame(self._panel,fg_color=P["card"],
            corner_radius=0,height=280,scrollbar_fg_color=P["bg2"],scrollbar_button_color=P["dim"])
        self._panel_scroll.pack(fill="both",expand=True,padx=0,pady=0)

        # Poll URL changes
        self.after(1500,self._poll_url)

    # ── Navigation ──
    def _go_back(self):
        try: self._browser.go_back()
        except: pass
    def _go_fwd(self):
        try: self._browser.go_forward()
        except: pass
    def _go_home(self):
        try: self._browser.load_url("https://www.youtube.com")
        except: pass
        self._url_var.set("https://www.youtube.com")
    def _nav_to_url(self):
        url=self._url_var.get().strip()
        if url and not url.startswith("http"): url="https://"+url
        try: self._browser.load_url(url)
        except: pass

    # ── URL Polling ──
    def _poll_url(self):
        try:
            url=self._browser.get_url()
            if url and url!=self._current_url:
                self._current_url=url
                self._url_var.set(url)
                was_video=self._is_video
                self._is_video=self._check_video_url(url)
                if self._is_video:
                    self._dl_toggle.configure(fg_color=P["accent"],hover_color=P["accent2"],
                        text_color="white",state="normal",text="⬇ Download")
                    self._status.configure(text="Video detected!",text_color=P["success"])
                else:
                    self._dl_toggle.configure(fg_color=P["surface"],hover_color=P["hover"],
                        text_color=P["dim"],state="disabled",text="⬇ Download")
                    if was_video:
                        self._status.configure(text="Browsing",text_color=P["text3"])
                        if self._panel_open: self._toggle_panel()
        except: pass
        self.after(1000,self._poll_url)

    def _check_video_url(self,url):
        if not url: return False
        if "youtube.com/watch" in url: return True
        if "youtu.be/" in url: return True
        if "youtube.com/shorts/" in url: return True
        return False

    # ── Download Panel Toggle ──
    def _toggle_panel(self):
        if self._panel_open:
            self._panel.pack_forget()
            self._panel_open=False
            self._dl_toggle.configure(text="⬇ Download")
        else:
            self._panel.pack(fill="x",side="bottom")
            self._panel_open=True
            self._dl_toggle.configure(text="✕ Close")
            self._fetch_formats()

    def _fetch_formats(self):
        for c in self._panel_scroll.winfo_children(): c.destroy()
        # Loading message
        self._panel_msg=ctk.CTkLabel(self._panel_scroll,text="⏳ Fetching available formats...",
            font=ctk.CTkFont("Segoe UI",13),text_color=P["warn"])
        self._panel_msg.pack(pady=20)
        self._status.configure(text="Fetching formats...",text_color=P["warn"])
        threading.Thread(target=self._fetch_th,daemon=True).start()

    def _fetch_th(self):
        url=self._current_url
        try:
            info,client=fetch_robust(url)
            self._info=info; self._formats=extract_formats(info)
            self.after(0,self._show_panel_formats)
        except Exception as e:
            msg=friendly(str(e))
            self.after(0,lambda m=msg:self._show_panel_error(m))

    def _show_panel_error(self,msg):
        for c in self._panel_scroll.winfo_children(): c.destroy()
        ctk.CTkLabel(self._panel_scroll,text=f"✗ {msg}",font=ctk.CTkFont("Segoe UI",12),
            text_color=P["error"],wraplength=800).pack(pady=20,padx=20)
        self._status.configure(text="Failed",text_color=P["error"])

    def _show_panel_formats(self):
        for c in self._panel_scroll.winfo_children(): c.destroy()
        self._fmt_btns=[]; self._sel=None
        info=self._info

        # ── Video title ──
        title_row=ctk.CTkFrame(self._panel_scroll,fg_color="transparent")
        title_row.pack(fill="x",padx=16,pady=(10,4))
        ctk.CTkLabel(title_row,text=info.get("title","Unknown")[:80],
            font=ctk.CTkFont("Segoe UI",13,"bold"),text_color=P["white"],
            wraplength=700,justify="left",anchor="w").pack(side="left")
        dur=fmt_dur(info.get("duration"))
        ctk.CTkLabel(title_row,text=dur,font=ctk.CTkFont("Segoe UI",11),
            text_color=P["text3"]).pack(side="right")

        n=len(self._formats)
        self._status.configure(text=f"{n} formats found",text_color=P["success"])

        # ── Format cards ──
        vfmts=[x for x in self._formats if x["type"]=="video"]
        afmts=[x for x in self._formats if x["type"]=="audio"]

        if vfmts:
            ctk.CTkLabel(self._panel_scroll,text="VIDEO QUALITY",font=ctk.CTkFont("Segoe UI",10,"bold"),
                text_color=P["text3"]).pack(anchor="w",padx=16,pady=(8,4))
            vgrid=ctk.CTkFrame(self._panel_scroll,fg_color="transparent")
            vgrid.pack(fill="x",padx=16)
            for i in range(min(len(vfmts),6)): vgrid.grid_columnconfigure(i,weight=1)
            for i,fmt in enumerate(vfmts):
                self._fmt_card(vgrid,fmt,0,i)

        if afmts:
            ctk.CTkLabel(self._panel_scroll,text="AUDIO ONLY",font=ctk.CTkFont("Segoe UI",10,"bold"),
                text_color=P["text3"]).pack(anchor="w",padx=16,pady=(8,4))
            agrid=ctk.CTkFrame(self._panel_scroll,fg_color="transparent")
            agrid.pack(fill="x",padx=16)
            for i in range(min(len(afmts),4)): agrid.grid_columnconfigure(i,weight=1)
            for i,fmt in enumerate(afmts):
                self._fmt_card(agrid,fmt,0,i)

        # ── Download controls ──
        ctrl=ctk.CTkFrame(self._panel_scroll,fg_color=P["surface"],corner_radius=10)
        ctrl.pack(fill="x",padx=16,pady=(10,12))
        ci=ctk.CTkFrame(ctrl,fg_color="transparent"); ci.pack(fill="x",padx=12,pady=10)

        ctk.CTkLabel(ci,text="Save to:",font=ctk.CTkFont("Segoe UI",10),
            text_color=P["text2"]).pack(side="left")
        self._dir_var=ctk.StringVar(value=self._save_dir)
        ctk.CTkEntry(ci,textvariable=self._dir_var,height=30,corner_radius=6,
            fg_color=P["card"],border_color=P["border"],text_color=P["text"],
            font=ctk.CTkFont("Segoe UI",10),width=300).pack(side="left",padx=8)
        ctk.CTkButton(ci,text="Browse",width=60,height=30,corner_radius=6,
            fg_color=P["card"],hover_color=P["hover"],border_width=1,border_color=P["border"],
            text_color=P["text2"],font=ctk.CTkFont("Segoe UI",9),
            command=self._browse).pack(side="left",padx=(0,12))

        self._dl_btn=ctk.CTkButton(ci,text="⬇  Select quality first",height=34,corner_radius=8,
            fg_color=P["border"],text_color=P["dim"],state="disabled",
            font=ctk.CTkFont("Segoe UI",12,"bold"),command=self._start_dl,width=220)
        self._dl_btn.pack(side="right")

        # Progress area (hidden)
        self._prog_frame=ctk.CTkFrame(self._panel_scroll,fg_color=P["surface"],corner_radius=10)

    def _fmt_card(self,parent,fmt,r,c):
        fr=ctk.CTkFrame(parent,fg_color=P["card"],corner_radius=8,border_width=1,
            border_color=P["border"],height=80,width=140)
        fr.grid(row=r,column=c,padx=4,pady=4,sticky="nsew")
        fr.grid_propagate(False)

        top=ctk.CTkFrame(fr,fg_color="transparent"); top.pack(fill="x",padx=8,pady=(8,0))
        ctk.CTkLabel(top,text=f" {fmt['badge']} ",font=ctk.CTkFont("Segoe UI",9,"bold"),
            text_color="white",fg_color=fmt["color"],corner_radius=3,height=18).pack(side="left")
        if fmt.get("size") and fmt["size"]!="—":
            ctk.CTkLabel(top,text=fmt["size"],font=ctk.CTkFont("Segoe UI",8),
                text_color=P["dim"]).pack(side="right")

        parts=[p for p in [fmt.get("fps"),fmt.get("bitrate")] if p and p!="—"]
        if parts:
            ctk.CTkLabel(fr,text=" · ".join(parts),font=ctk.CTkFont("Segoe UI",9),
                text_color=P["text3"]).pack(anchor="w",padx=8)

        btn=ctk.CTkButton(fr,text="Select",corner_radius=4,fg_color="transparent",
            border_width=1,border_color=P["border"],hover_color=P["hover"],
            text_color=P["text"],font=ctk.CTkFont("Segoe UI",9,"bold"),height=22)
        btn.pack(side="bottom",fill="x",padx=6,pady=6)
        btn.configure(command=lambda _f=fmt,_b=btn,_fr=fr:self._pick(_f,_b,_fr))
        self._fmt_btns.append((btn,fr))

    def _pick(self,f,b,fr):
        for btn,frame in self._fmt_btns:
            btn.configure(text="Select",fg_color="transparent",text_color=P["text2"],border_color=P["border"])
            frame.configure(border_color=P["border"])
        self._sel=f
        b.configure(text="✓",fg_color=P["accent_dim"],text_color=P["accent_hi"],border_color=P["accent"])
        fr.configure(border_color=P["accent"])
        ext="MP4" if f["type"]=="video" else f.get("badge","")
        self._dl_btn.configure(text=f"⬇  Download {f['badge']} [{ext}]",
            fg_color=P["accent"],hover_color=P["accent2"],text_color="white",state="normal")

    def _browse(self):
        d=filedialog.askdirectory(initialdir=self._save_dir)
        if d: self._save_dir=d; self._dir_var.set(d)

    # ── Download Engine ──
    def _start_dl(self):
        if self._dl_active or not self._sel: return
        save=self._dir_var.get().strip() or os.path.expanduser("~/Downloads")
        os.makedirs(save,exist_ok=True)
        self._dl_active=True; self._cancel_flag=False; self._pause_flag=False

        self._dl_btn.configure(text="Downloading...",state="disabled",fg_color=P["surface"],text_color=P["text3"])
        self._status.configure(text="Downloading",text_color=P["warn"])

        self._prog_frame.pack(fill="x",padx=16,pady=(0,10))
        for w in self._prog_frame.winfo_children(): w.destroy()
        pi=ctk.CTkFrame(self._prog_frame,fg_color="transparent"); pi.pack(fill="x",padx=12,pady=10)

        r1=ctk.CTkFrame(pi,fg_color="transparent"); r1.pack(fill="x")
        self._pct_lbl=ctk.CTkLabel(r1,text="0%",font=ctk.CTkFont("Segoe UI",20,"bold"),text_color=P["accent_hi"])
        self._pct_lbl.pack(side="left")
        self._eta_lbl=ctk.CTkLabel(r1,text="",font=ctk.CTkFont("Segoe UI",10),text_color=P["text3"])
        self._eta_lbl.pack(side="right")

        self._prog=ctk.CTkProgressBar(pi,height=5,corner_radius=3,fg_color=P["bg"],progress_color=P["accent"])
        self._prog.pack(fill="x",pady=(4,6)); self._prog.set(0)

        stats=ctk.CTkFrame(pi,fg_color="transparent"); stats.pack(fill="x")
        stats.grid_columnconfigure((0,1,2),weight=1)
        self._stat_labels={}
        for i,(key,val) in enumerate([("Speed","—"),("Downloaded","—"),("Total","—")]):
            cell=ctk.CTkFrame(stats,fg_color="transparent"); cell.grid(row=0,column=i,sticky="w",padx=(0,10))
            ctk.CTkLabel(cell,text=key,font=ctk.CTkFont("Segoe UI",8),text_color=P["dim"]).pack(anchor="w")
            vlbl=ctk.CTkLabel(cell,text=val,font=ctk.CTkFont("Segoe UI",11,"bold"),text_color=P["white"])
            vlbl.pack(anchor="w"); self._stat_labels[key]=vlbl

        ar=ctk.CTkFrame(pi,fg_color="transparent"); ar.pack(fill="x",pady=(8,0))
        ctk.CTkButton(ar,text="⏸",width=40,height=28,corner_radius=6,fg_color=P["surface"],
            hover_color=P["hover"],text_color=P["white"],border_width=1,border_color=P["border"],
            command=self._toggle_pause).pack(side="left",padx=(0,6))
        ctk.CTkButton(ar,text="✕ Cancel",width=80,height=28,corner_radius=6,fg_color=P["error_dim"],
            hover_color=P["error_dim"],text_color=P["error"],border_width=1,border_color=P["error"],
            command=self._cancel_dl).pack(side="left")

        self._dl_start=time.time()
        self._tick_elapsed()
        threading.Thread(target=self._dl_th,args=(self._sel,save),daemon=True).start()

    def _tick_elapsed(self):
        if not self._dl_active: return
        self.after(1000,self._tick_elapsed)

    def _toggle_pause(self):
        if not self._dl_active: return
        self._pause_flag=not self._pause_flag
        self._stat_labels["Speed"].configure(text="Paused" if self._pause_flag else "—")
        self._status.configure(text="Paused" if self._pause_flag else "Downloading",text_color=P["warn"])

    def _cancel_dl(self):
        if self._dl_active: self._cancel_flag=True

    def _dl_th(self,fmt,save):
        url=self._current_url
        title=clean(self._info.get("title","video"))

        def hook(d):
            if self._cancel_flag: raise ValueError("Cancelled")
            while self._pause_flag and not self._cancel_flag: time.sleep(0.5)
            if self._cancel_flag: raise ValueError("Cancelled")
            if d["status"]=="downloading":
                dl_bytes=d.get("downloaded_bytes"); total_bytes=d.get("total_bytes") or d.get("total_bytes_estimate")
                pct=(dl_bytes/total_bytes) if (dl_bytes and total_bytes and total_bytes>0) else 0
                speed=re.sub(r'\x1b\[[0-9;]*m','',d.get("_speed_str","").strip() or "—")
                downloaded=re.sub(r'\x1b\[[0-9;]*m','',d.get("_downloaded_bytes_str","").strip())
                total=re.sub(r'\x1b\[[0-9;]*m','',(d.get("_total_bytes_str","") or d.get("_total_bytes_estimate_str","")).strip())
                eta=re.sub(r'\x1b\[[0-9;]*m','',d.get("_eta_str","").strip() or "")
                def upd(p=pct,sp=speed,dl=downloaded,tt=total,et=eta):
                    self._prog.set(p); self._pct_lbl.configure(text=f"{p*100:.1f}%")
                    self._stat_labels["Speed"].configure(text=sp)
                    self._stat_labels["Downloaded"].configure(text=dl or "—")
                    self._stat_labels["Total"].configure(text=tt or "—")
                    if et: self._eta_lbl.configure(text=f"ETA {et}")
                self.after(0,upd)
            elif d["status"]=="finished":
                self.after(0,lambda:self._pct_lbl.configure(text="Processing..."))

        opts=base_opts({"progress_hooks":[hook]})
        opts["outtmpl"]=os.path.join(save,f"{title}.%(ext)s")
        if fmt.get("mp3"):
            opts["format"]="bestaudio/best"
            opts["postprocessors"]=[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"192"}]
        elif fmt["type"]=="audio":
            opts["format"]=fmt["format_str"]
        else:
            opts["format"]=fmt["format_str"]
            if FFMPEG_OK:
                opts["merge_output_format"]="mp4"
                opts["postprocessor_args"]={"merger":["-c:v","copy","-c:a","aac","-strict","experimental"]}

        success,last_err=False,Exception("unknown")
        for client in CLIENTS:
            if self._cancel_flag: break
            o=dict(opts); o["extractor_args"]={"youtube":{"player_client":client}}
            try:
                with yt_dlp.YoutubeDL(o) as ydl: ydl.download([url])
                success=True; break
            except Exception as e:
                last_err=e
                if self._cancel_flag or "cancel" in str(e).lower(): break
                if "ffmpeg" in str(e).lower(): break
        if not success and not self._cancel_flag and "ffmpeg" not in str(last_err).lower():
            try:
                with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([url])
                success=True
            except Exception as e: last_err=e

        if success: self.after(0,lambda:self._dl_done(save))
        elif self._cancel_flag: self.after(0,lambda:self._dl_fail("Cancelled"))
        else:
            msg=friendly(str(last_err))
            self.after(0,lambda m=msg:self._dl_fail(m))

    def _dl_done(self,save):
        self._dl_active=False
        self._prog.configure(progress_color=P["success"])
        self._pct_lbl.configure(text="✓ Complete",text_color=P["success"])
        self._eta_lbl.configure(text="")
        self._stat_labels["Speed"].configure(text="Done")
        self._status.configure(text="Downloaded!",text_color=P["success"])
        self._dl_btn.configure(text="✓ Saved! Click to download again",fg_color=P["success_dim"],
            hover_color=P["hover"],text_color=P["success"],state="normal",command=self._reset_dl)
        messagebox.showinfo("Done",f"✓ Saved to {save}")

    def _reset_dl(self):
        self._prog_frame.pack_forget()
        if self._sel:
            ext="MP4" if self._sel["type"]=="video" else self._sel.get("badge","")
            self._dl_btn.configure(text=f"⬇  Download {self._sel['badge']} [{ext}]",
                fg_color=P["accent"],hover_color=P["accent2"],text_color="white",
                state="normal",command=self._start_dl)
        self._status.configure(text="Ready",text_color=P["text3"])

    def _dl_fail(self,msg):
        self._dl_active=False
        self._prog.configure(progress_color=P["error"])
        self._pct_lbl.configure(text="✗ Failed" if "cancel" not in msg.lower() else "✗ Cancelled",text_color=P["error"])
        self._stat_labels["Speed"].configure(text="Stopped")
        self._status.configure(text="Failed",text_color=P["error"])
        self._dl_btn.configure(text="↻ Retry",fg_color=P["error_dim"],hover_color=P["hover"],
            text_color=P["error"],state="normal",command=self._start_dl)
        if "cancel" not in msg.lower(): messagebox.showerror("Failed",msg)


# ===========================================================================
if __name__=="__main__":
    def go():
        try:
            BrowserApp().mainloop()
        except Exception as e:
            print(f"App error: {e}")

    import clr
    clr.AddReference('System.Threading')
    from System.Threading import Thread, ApartmentState, ThreadStart
    
    t = Thread(ThreadStart(go))
    t.ApartmentState = ApartmentState.STA
    t.Start()
    t.Join()
