"""
YTDROP PRO V2 - Browse YouTube + Download
Uses pywebview directly (no tkinter) for stability with PyInstaller.

INSTALL:
    pip install yt-dlp "pywebview<5" requests
"""
import os, re, ssl, sys, time, shutil, subprocess, threading, json
import yt_dlp
import webview

ssl._create_default_https_context = ssl._create_unverified_context

# ── FFmpeg ──
def _find_ffmpeg():
    p = shutil.which("ffmpeg")
    if p: return p
    local = os.environ.get("LOCALAPPDATA","")
    user = os.path.expanduser("~")
    cf = getattr(subprocess,"CREATE_NO_WINDOW",0)
    for base in [os.path.join(local,"Microsoft","WinGet","Packages")]:
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

QUAL={2160:("4K Ultra HD","4K","#ff9f0a"),1440:("2K QHD","2K","#ff9f0a"),
      1080:("1080p Full HD","FHD","#0a84ff"),720:("720p HD","HD","#64d2ff"),
      480:("480p SD","SD","#c7c7cc"),360:("360p","360","#8e8e93"),
      240:("240p","240","#636366"),144:("144p","144","#636366")}

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
        fps=best_f.get("fps",0) or 0
        size=fmt_bytes(best_f.get("filesize") or best_f.get("filesize_approx"))
        tbr=best_f.get("tbr",0) or 0; seen.add(h)
        out.append({"type":"video","label":label,"badge":badge,"color":color,
            "fps":f"{fps:.0f} fps" if fps else "","bitrate":f"{tbr:.0f} kbps" if tbr else "",
            "size":size,"format_str":fmt_str,"height":h})
    seen_ext=set()
    for f in audio_only:
        ext=f.get("ext","m4a")
        if ext in seen_ext: continue
        seen_ext.add(ext)
        out.append({"type":"audio","label":f"Audio {ext.upper()}","badge":ext.upper(),
            "color":"#ff375f","fps":"","bitrate":f"{f.get('abr',0) or 0:.0f} kbps" if f.get("abr") else "",
            "size":fmt_bytes(f.get("filesize") or f.get("filesize_approx")),
            "format_str":f.get("format_id","bestaudio"),"height":0,"mp3":False})
    if FFMPEG_OK:
        out.append({"type":"audio","label":"Audio MP3 (Best)","badge":"MP3","color":"#ff375f","fps":"","bitrate":"Best","size":"~varies","format_str":"bestaudio/best","height":0,"mp3":True})
    else:
        out.append({"type":"audio","label":"Audio M4A (Best)","badge":"M4A","color":"#ff375f","fps":"","bitrate":"Best","size":"~varies","format_str":"bestaudio[ext=m4a]/bestaudio","height":0,"mp3":False})
    return out

def friendly(raw):
    r=raw.lower()
    if "ffmpeg" in r: return "FFmpeg required. Install: winget install ffmpeg"
    if "ssl" in r or "certificate" in r: return "SSL error - update yt-dlp"
    if "sign in" in r or "age" in r: return "Age-restricted content"
    if "private" in r: return "This video is private"
    if "unavailable" in r or "removed" in r: return "Video unavailable"
    if "403" in r: return "Blocked - update: pip install -U yt-dlp"
    return f"Error: {raw[:180]}"

# ═══════════════════════════════════════════════════════════════════
# INJECTED JS/CSS - Download overlay inside YouTube
# ═══════════════════════════════════════════════════════════════════
INJECT_JS = r"""
(function(){
if(document.getElementById('ytdrop-fab')) return;

var style=document.createElement('style');
style.textContent=`
#ytdrop-fab{position:fixed;bottom:24px;right:24px;width:56px;height:56px;border-radius:50%;
background:linear-gradient(135deg,#0a84ff,#5e5ce6);color:#fff;font-size:24px;display:none;
align-items:center;justify-content:center;cursor:pointer;z-index:99999;
box-shadow:0 4px 20px rgba(10,132,255,.5);transition:transform .2s,box-shadow .2s;border:none}
#ytdrop-fab:hover{transform:scale(1.1);box-shadow:0 6px 28px rgba(10,132,255,.7)}
#ytdrop-panel{position:fixed;bottom:0;left:0;right:0;max-height:420px;background:rgba(18,18,18,.97);
backdrop-filter:blur(20px);border-top:1px solid #2c2c2e;z-index:99998;display:none;
flex-direction:column;overflow-y:auto;font-family:'Segoe UI',sans-serif;padding:0}
#ytdrop-panel *{box-sizing:border-box}
.yd-hdr{display:flex;align-items:center;justify-content:space-between;padding:14px 20px;
border-bottom:1px solid #2c2c2e}
.yd-hdr h3{margin:0;color:#fff;font-size:15px;font-weight:600}
.yd-close{background:none;border:none;color:#8e8e93;font-size:22px;cursor:pointer;padding:4px 8px}
.yd-close:hover{color:#ff453a}
.yd-status{padding:12px 20px;color:#ff9f0a;font-size:13px;text-align:center}
.yd-grid{display:flex;flex-wrap:wrap;gap:8px;padding:8px 20px}
.yd-card{background:#1f1f1f;border:1px solid #2c2c2e;border-radius:8px;padding:10px 14px;
cursor:pointer;min-width:110px;flex:1;max-width:180px;transition:border-color .2s,background .2s}
.yd-card:hover{border-color:#409cff;background:#1a1a2e}
.yd-card.sel{border-color:#0a84ff;background:#002A5A}
.yd-badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;color:#fff;margin-bottom:4px}
.yd-meta{color:#8e8e93;font-size:10px;margin-top:2px}
.yd-section{padding:4px 20px;color:#8e8e93;font-size:11px;font-weight:700;text-transform:uppercase}
.yd-controls{display:flex;align-items:center;gap:10px;padding:12px 20px;border-top:1px solid #2c2c2e}
.yd-dir{flex:1;background:#1f1f1f;border:1px solid #2c2c2e;border-radius:6px;color:#ebebf5;
padding:6px 10px;font-size:12px;font-family:inherit}
.yd-btn{padding:8px 20px;border-radius:8px;border:none;font-size:13px;font-weight:600;
cursor:pointer;transition:background .2s}
.yd-btn-primary{background:#0a84ff;color:#fff}
.yd-btn-primary:hover{background:#409cff}
.yd-btn-primary:disabled{background:#2c2c2e;color:#636366;cursor:default}
.yd-btn-browse{background:#2c2c2e;color:#c7c7cc}
.yd-btn-browse:hover{background:#3a3a3c}
.yd-progress{padding:12px 20px;display:none}
.yd-pbar-bg{background:#1f1f1f;border-radius:4px;height:6px;overflow:hidden}
.yd-pbar{height:100%;background:linear-gradient(90deg,#0a84ff,#5e5ce6);width:0%;transition:width .3s;border-radius:4px}
.yd-pinfo{display:flex;justify-content:space-between;margin-top:6px;color:#8e8e93;font-size:11px}
.yd-cancel{background:none;border:1px solid #ff453a;color:#ff453a;padding:4px 14px;border-radius:6px;
cursor:pointer;font-size:11px;margin-left:10px}
.yd-cancel:hover{background:rgba(255,69,58,.15)}
`;
document.head.appendChild(style);

var fab=document.createElement('div');
fab.id='ytdrop-fab';
fab.innerHTML='<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12l7 7 7-7"/></svg>';
document.body.appendChild(fab);

var panel=document.createElement('div');
panel.id='ytdrop-panel';
panel.innerHTML=`
<div class="yd-hdr"><h3 id="yd-title">YTDROP PRO V2</h3><button class="yd-close" id="yd-close">&times;</button></div>
<div id="yd-status" class="yd-status" style="display:none"></div>
<div id="yd-formats"></div>
<div id="yd-controls" class="yd-controls" style="display:none">
  <span style="color:#8e8e93;font-size:11px">Save to:</span>
  <input type="text" class="yd-dir" id="yd-dir" readonly>
  <button class="yd-btn yd-btn-browse" id="yd-browse">Browse</button>
  <button class="yd-btn yd-btn-primary" id="yd-dl" disabled>Select quality</button>
</div>
<div id="yd-progress" class="yd-progress">
  <div class="yd-pbar-bg"><div class="yd-pbar" id="yd-pbar"></div></div>
  <div class="yd-pinfo"><span id="yd-ppct">0%</span><span id="yd-pspeed"></span><span id="yd-peta"></span>
  <button class="yd-cancel" id="yd-pcancel">Cancel</button></div>
</div>`;
document.body.appendChild(panel);

var selectedIdx=-1;
var panelOpen=false;

document.getElementById('yd-close').onclick=function(){panel.style.display='none';panelOpen=false;};
document.getElementById('yd-browse').onclick=function(){pywebview.api.browse_folder().then(function(d){document.getElementById('yd-dir').value=d;});};
document.getElementById('yd-dl').onclick=function(){
  if(selectedIdx<0)return;
  this.disabled=true;this.textContent='Downloading...';
  document.getElementById('yd-progress').style.display='block';
  pywebview.api.start_download(selectedIdx);
};
document.getElementById('yd-pcancel').onclick=function(){pywebview.api.cancel_download();};

fab.onclick=function(){
  if(panelOpen){panel.style.display='none';panelOpen=false;return;}
  panel.style.display='flex';panelOpen=true;selectedIdx=-1;
  document.getElementById('yd-status').style.display='block';
  document.getElementById('yd-status').textContent='Loading formats...';
  document.getElementById('yd-formats').innerHTML='';
  document.getElementById('yd-controls').style.display='none';
  document.getElementById('yd-progress').style.display='none';
  pywebview.api.get_save_dir().then(function(d){document.getElementById('yd-dir').value=d;});
  pywebview.api.fetch_formats(window.location.href);
};

// URL monitoring
var origPush=history.pushState,origReplace=history.replaceState;
function checkUrl(){
  var u=window.location.href;
  var isVid=u.indexOf('/watch')>-1||u.indexOf('/shorts/')>-1||u.indexOf('youtu.be/')>-1;
  fab.style.display=isVid?'flex':'none';
  if(!isVid&&panelOpen){panel.style.display='none';panelOpen=false;}
}
history.pushState=function(){origPush.apply(this,arguments);setTimeout(checkUrl,200);};
history.replaceState=function(){origReplace.apply(this,arguments);setTimeout(checkUrl,200);};
window.addEventListener('popstate',function(){setTimeout(checkUrl,200);});
setInterval(checkUrl,1000);
checkUrl();

// Functions called from Python
window.ytdropShowFormats=function(formats,title,duration){
  document.getElementById('yd-status').style.display='none';
  document.getElementById('yd-title').textContent=title.substring(0,70)+(title.length>70?'...':'')+'  ('+duration+')';
  var html='';
  var videos=formats.filter(function(f){return f.type==='video';});
  var audios=formats.filter(function(f){return f.type==='audio';});
  if(videos.length){
    html+='<div class="yd-section">VIDEO</div><div class="yd-grid">';
    videos.forEach(function(f,i){
      var idx=formats.indexOf(f);
      html+='<div class="yd-card" data-idx="'+idx+'" onclick="ytdropPick('+idx+')"><span class="yd-badge" style="background:'+f.color+'">'+f.badge+'</span>';
      html+='<div class="yd-meta">'+[f.fps,f.bitrate,f.size].filter(Boolean).join(' · ')+'</div></div>';
    });
    html+='</div>';
  }
  if(audios.length){
    html+='<div class="yd-section">AUDIO</div><div class="yd-grid">';
    audios.forEach(function(f,i){
      var idx=formats.indexOf(f);
      html+='<div class="yd-card" data-idx="'+idx+'" onclick="ytdropPick('+idx+')"><span class="yd-badge" style="background:'+f.color+'">'+f.badge+'</span>';
      html+='<div class="yd-meta">'+[f.bitrate,f.size].filter(Boolean).join(' · ')+'</div></div>';
    });
    html+='</div>';
  }
  document.getElementById('yd-formats').innerHTML=html;
  document.getElementById('yd-controls').style.display='flex';
  var dlBtn=document.getElementById('yd-dl');dlBtn.disabled=true;dlBtn.textContent='Select quality';
};

window.ytdropPick=function(idx){
  selectedIdx=idx;
  document.querySelectorAll('.yd-card').forEach(function(c){c.classList.remove('sel');});
  var card=document.querySelector('.yd-card[data-idx="'+idx+'"]');
  if(card)card.classList.add('sel');
  var dlBtn=document.getElementById('yd-dl');dlBtn.disabled=false;
  var badge=card?card.querySelector('.yd-badge').textContent:'';
  dlBtn.textContent='Download '+badge;
};

window.ytdropShowError=function(msg){
  document.getElementById('yd-status').style.display='block';
  document.getElementById('yd-status').textContent='Error: '+msg;
  document.getElementById('yd-status').style.color='#ff453a';
};

window.ytdropProgress=function(pct,speed,eta){
  var bar=document.getElementById('yd-pbar');bar.style.width=(pct*100)+'%';
  document.getElementById('yd-ppct').textContent=Math.round(pct*100)+'%';
  document.getElementById('yd-pspeed').textContent=speed;
  document.getElementById('yd-peta').textContent=eta?'ETA '+eta:'';
};

window.ytdropDone=function(path){
  document.getElementById('yd-pbar').style.width='100%';
  document.getElementById('yd-pbar').style.background='#32d74b';
  document.getElementById('yd-ppct').textContent='Done!';
  document.getElementById('yd-pspeed').textContent='Saved';
  document.getElementById('yd-peta').textContent='';
  document.getElementById('yd-pcancel').style.display='none';
  var dlBtn=document.getElementById('yd-dl');dlBtn.disabled=false;dlBtn.textContent='Download another';
};

window.ytdropFail=function(msg){
  document.getElementById('yd-pbar').style.background='#ff453a';
  document.getElementById('yd-ppct').textContent='Failed';
  document.getElementById('yd-pspeed').textContent=msg;
  document.getElementById('yd-peta').textContent='';
  var dlBtn=document.getElementById('yd-dl');dlBtn.disabled=false;dlBtn.textContent='Retry';
};
})();
"""

# ═══════════════════════════════════════════════════════════════════
# Python API exposed to JavaScript
# ═══════════════════════════════════════════════════════════════════
class Api:
    def __init__(self):
        self.window = None
        self._save_dir = os.path.expanduser("~/Downloads")
        self._info = None
        self._formats = []
        self._dl_active = False
        self._cancel_flag = False

    def get_save_dir(self):
        return self._save_dir

    def browse_folder(self):
        try:
            result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
            if result and len(result) > 0:
                self._save_dir = result[0]
                return result[0]
        except: pass
        return self._save_dir

    def fetch_formats(self, url):
        def _work():
            try:
                info, client = fetch_robust(url)
                self._info = info
                self._formats = extract_formats(info)
                fj = json.dumps(self._formats)
                t = json.dumps(info.get("title","Unknown"))
                d = json.dumps(fmt_dur(info.get("duration")))
                self.window.evaluate_js(f'ytdropShowFormats({fj},{t},{d})')
            except Exception as e:
                msg = json.dumps(friendly(str(e)))
                self.window.evaluate_js(f'ytdropShowError({msg})')
        threading.Thread(target=_work, daemon=True).start()

    def start_download(self, format_index):
        if self._dl_active or format_index < 0 or format_index >= len(self._formats):
            return
        fmt = self._formats[format_index]
        save = self._save_dir
        os.makedirs(save, exist_ok=True)
        self._dl_active = True
        self._cancel_flag = False
        url = self.window.evaluate_js("window.location.href")

        def _work():
            title = clean(self._info.get("title","video"))
            def hook(d):
                if self._cancel_flag: raise ValueError("Cancelled")
                if d["status"]=="downloading":
                    dl=d.get("downloaded_bytes"); tot=d.get("total_bytes") or d.get("total_bytes_estimate")
                    pct=(dl/tot) if (dl and tot and tot>0) else 0
                    speed=re.sub(r'\x1b\[[0-9;]*m','',d.get("_speed_str","").strip() or "")
                    eta=re.sub(r'\x1b\[[0-9;]*m','',d.get("_eta_str","").strip() or "")
                    try: self.window.evaluate_js(f'ytdropProgress({pct},{json.dumps(speed)},{json.dumps(eta)})')
                    except: pass

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

            success=False
            for client in CLIENTS:
                if self._cancel_flag: break
                o=dict(opts); o["extractor_args"]={"youtube":{"player_client":client}}
                try:
                    with yt_dlp.YoutubeDL(o) as ydl: ydl.download([url])
                    success=True; break
                except Exception as e:
                    if self._cancel_flag or "cancel" in str(e).lower(): break
                    if "ffmpeg" in str(e).lower(): break

            self._dl_active=False
            if success:
                try: self.window.evaluate_js(f'ytdropDone({json.dumps(save)})')
                except: pass
            elif self._cancel_flag:
                try: self.window.evaluate_js('ytdropFail("Cancelled")')
                except: pass
            else:
                try: self.window.evaluate_js('ytdropFail("Download failed")')
                except: pass

        threading.Thread(target=_work, daemon=True).start()

    def cancel_download(self):
        self._cancel_flag = True

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    api = Api()
    user_data = os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "YTDrop_V2_Data"
    )
    os.makedirs(user_data, exist_ok=True)

    window = webview.create_window(
        'YTDROP PRO V2',
        'https://www.youtube.com',
        js_api=api,
        width=1100,
        height=780,
        min_size=(900, 600),
    )
    api.window = window

    def on_loaded():
        try:
            window.evaluate_js(INJECT_JS)
        except: pass

    window.events.loaded += on_loaded

    webview.start(
        private_mode=False,
        storage_path=user_data,
    )
