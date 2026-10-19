from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime, timezone, timedelta
import sqlite3, json, hashlib, uuid, subprocess, shutil, csv, io, zipfile, os, threading
from urllib.parse import urlsplit

ROOT = Path(os.environ.get('MAM_DATA_DIR', str(Path(__file__).resolve().parents[1] / 'data'))).resolve()
ROOT.mkdir(exist_ok=True)
app = FastAPI(title='Xưởng nội dung')
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])
@app.middleware('http')
async def local_requests(request, call_next):
    origin=request.headers.get('origin')
    if request.method not in ('GET','HEAD','OPTIONS') and origin:
        parsed=urlsplit(origin)
        if parsed.hostname not in ('localhost','127.0.0.1') or parsed.port not in (3000,8000,None):
            return JSONResponse({'detail':'Yêu cầu không đến từ ứng dụng trên máy'},status_code=403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    return response
EXPORT_LOCK=threading.Lock()
def db():
    c=sqlite3.connect(ROOT/'workspace.db'); c.row_factory=sqlite3.Row; return c
with db() as c:
    c.executescript('''CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,title TEXT,url TEXT UNIQUE,platform TEXT,created TEXT);
    CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY,title TEXT,sha TEXT UNIQUE,path TEXT,metadata TEXT,rights TEXT);
    CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,body TEXT);
    CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,state TEXT,message TEXT,output TEXT);
    CREATE TABLE IF NOT EXISTS conversions(code TEXT PRIMARY KEY,amount INTEGER,status TEXT,updated TEXT);
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,kind TEXT,body TEXT,created TEXT);''')
def now(): return datetime.now(timezone.utc).isoformat()
def uid(): return uuid.uuid4().hex

def audit(c,kind,body): c.execute('INSERT INTO audit(kind,body,created) VALUES(?,?,?)',(kind,json.dumps(body,ensure_ascii=False),now()))
def safe_url(url):
    p=urlsplit(url)
    if p.scheme!='https' or not p.hostname or p.username or p.password: raise HTTPException(400,'Cần đường dẫn HTTPS hợp lệ')
    host=p.hostname.lower()
    if not any(host==h or host.endswith('.'+h) for h in ['shopee.vn','shope.ee','s.shopee.vn','tiktok.com','facebook.com','fb.watch','youtube.com','youtu.be']): raise HTTPException(400,'Nguồn chưa được hỗ trợ; chỉ nhận liên kết Shopee, Facebook, TikTok, YouTube')
    return url
class Source(BaseModel):
    title: str
    url: str
    platform: str
@app.get('/api/state')
def state():
    with db() as c:
        result={k:[dict(r) for r in c.execute('SELECT * FROM '+k+' ORDER BY rowid DESC')] for k in ['sources','assets','jobs','conversions']}
        result['projects']=[json.loads(r['body']) for r in c.execute('SELECT body FROM projects')]
        for j in result['jobs']: j.pop('output')
        for a in result['assets']:
            a.pop('path'); a['metadata']=json.loads(a['metadata']); a['rights']=json.loads(a['rights']); a['metadata'].get('format',{}).pop('filename',None)
        return result
@app.post('/api/sources')
def source(s:Source):
    safe_url(s.url)
    if not s.title.strip(): raise HTTPException(400,'Nhập tên nguồn')
    p=urlsplit(s.url); canonical=p._replace(fragment='').geturl()
    with db() as c:
        try: c.execute('INSERT INTO sources VALUES(?,?,?,?,?)',(uid(),s.title,canonical,s.platform,now()))
        except sqlite3.IntegrityError: raise HTTPException(409,'Nguồn này đã có trong kho')
        audit(c,'thêm nguồn',s.model_dump())
    return {'message':'Đã lưu nguồn tham khảo'}
@app.post('/api/assets')
async def upload(file:UploadFile=File(...)):
    ident=uid(); path=ROOT/(ident+'.media'); size=0; h=hashlib.sha256()
    try:
        with path.open('wb') as out:
            while chunk:=await file.read(1024*1024):
                size+=len(chunk)
                if size>1024**3: raise HTTPException(400,'Tệp vượt giới hạn 1 GB')
                out.write(chunk); h.update(chunk)
        probe=subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)],capture_output=True,text=True,timeout=60)
        if probe.returncode: raise HTTPException(400,'Không đọc được video; kiểm tra định dạng tệp')
        meta=json.loads(probe.stdout)
        if not any(s.get('codec_type')=='video' for s in meta['streams']): raise HTTPException(400,'Tệp không có hình ảnh video')
        with db() as c:
            try: c.execute('INSERT INTO assets VALUES(?,?,?,?,?,?)',(ident,file.filename,h.hexdigest(),str(path),json.dumps(meta),'{}'))
            except sqlite3.IntegrityError: raise HTTPException(409,'Video trùng nội dung với tệp đã nhập')
            audit(c,'nhập video',{'id':ident,'sha256':h.hexdigest()})
        return {'message':'Đã nhập video; bổ sung quyền trước khi xuất'}
    except Exception:
        path.unlink(missing_ok=True); raise
@app.get('/api/assets/{ident}/video')
def video(ident:str):
    with db() as c: a=c.execute('SELECT * FROM assets WHERE id=?',(ident,)).fetchone()
    if not a: raise HTTPException(404,'Không tìm thấy video')
    return FileResponse(a['path'],media_type='video/mp4')
class Rights(BaseModel):
    owner:str
    evidence:str
    channels:list[str]
    expiry:str
    commercial:bool
    edit:bool
    music:bool
@app.put('/api/assets/{ident}/rights')
def rights(ident:str,r:Rights):
    if not r.owner.strip() or not r.evidence.strip(): raise HTTPException(400,'Cần chủ sở hữu và bằng chứng quyền sử dụng')
    try: datetime.strptime(r.expiry,'%Y-%m-%d')
    except ValueError: raise HTTPException(400,'Ngày hết hạn không hợp lệ')
    with db() as c:
        if not c.execute('SELECT id FROM assets WHERE id=?',(ident,)).fetchone(): raise HTTPException(404,'Không có video')
        c.execute('UPDATE assets SET rights=? WHERE id=?',(r.model_dump_json(),ident)); audit(c,'cập nhật quyền',{'asset':ident,**r.model_dump()})
    return {'message':'Đã lưu hồ sơ quyền do bạn xác nhận'}
@app.post('/api/sources/import')
async def import_sources(file:UploadFile=File(...)):
    raw=await file.read(5*1024*1024+1)
    if len(raw)>5*1024*1024: raise HTTPException(400,'CSV vượt 5 MB')
    try:
        text=raw.decode('utf-8-sig'); dialect=csv.Sniffer().sniff(text[:8192],delimiters=',;\t'); rows=list(csv.DictReader(io.StringIO(text),dialect=dialect))
    except Exception: raise HTTPException(400,'Không đọc được CSV UTF-8')
    added=duplicate=0; errors=[]
    for i,row in enumerate(rows):
        try:
            s=Source(title=row['Tên nguồn'],url=row['Liên kết'],platform=row['Nền tảng'])
            source(s); added+=1
        except HTTPException as e:
            if e.status_code==409: duplicate+=1
            else: errors.append({'line':i+2,'message':str(e.detail)})
        except Exception: errors.append({'line':i+2,'message':'Thiếu cột Tên nguồn, Liên kết hoặc Nền tảng'})
    return {'message':f'Đã thêm {added} nguồn; {duplicate} nguồn trùng; {len(errors)} dòng lỗi','errors':errors}

class Project(BaseModel):
    id:str=''
    asset:str
    title:str
    channel:str='Facebook'
    start:float=0
    end:float=15
    overlay:str=''
    subtitle:str=''
    caption:str=''
    product:str=''
    affiliate:str=''
    matched:bool=False
    reviewed:bool=False
@app.post('/api/projects')
def save(p:Project):
    if not p.id: p.id=uid()
    with db() as c: c.execute('INSERT OR REPLACE INTO projects VALUES(?,?)',(p.id,p.model_dump_json()))
    return {'message':'Đã lưu bản nháp','id':p.id}
def gate(p):
    with db() as c: a=c.execute('SELECT * FROM assets WHERE id=?',(p.asset,)).fetchone()
    if not a: raise HTTPException(400,'Chọn video nguồn')
    r=json.loads(a['rights'])
    if not all(r.get(k) for k in ['owner','evidence','commercial','edit','music']) or p.channel not in r.get('channels',[]) or r.get('expiry','')<datetime.now(timezone(timedelta(hours=7))).date().isoformat(): raise HTTPException(400,'Quyền sử dụng thiếu, hết hạn hoặc không cho phép kênh đích')
    duration=float(json.loads(a['metadata'])['format']['duration'])
    if not 0<=p.start<p.end<=duration: raise HTTPException(400,'Điểm cắt phải nằm trong thời lượng video')
    if not p.product.strip() or not p.matched: raise HTTPException(400,'Cần xác nhận video đúng sản phẩm và biến thể')
    safe_url(p.affiliate)
    if urlsplit(p.affiliate).hostname not in ('shope.ee','s.shopee.vn','shopee.vn','www.shopee.vn'): raise HTTPException(400,'Liên kết tiếp thị phải thuộc Shopee')
    if not p.reviewed or not p.caption.strip(): raise HTTPException(400,'Cần duyệt nội dung, link tiếp thị liên kết và lời công bố')
    if p.channel not in ['Facebook','TikTok']: raise HTTPException(400,'Kênh xuất chưa hỗ trợ')
    return dict(a)
def render(ident,p):
    folder=ROOT/ident; folder.mkdir(exist_ok=True)
    try:
        a=gate(p)
        with db() as c: c.execute('UPDATE jobs SET state=? WHERE id=?',('đang xử lý',ident))
        fontfile=None
        for candidate in [Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/'arial.ttf',Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]:
            if candidate.is_file():
                fontfile=folder/'font.ttf'; shutil.copyfile(candidate,fontfile); break
        font_option='fontfile=font.ttf:' if fontfile else ''
        filters=['scale=720:1280:force_original_aspect_ratio=increase','crop=720:1280','setsar=1']
        if p.overlay.strip():
            (folder/'title.txt').write_text(p.overlay,encoding='utf-8'); filters.append('drawtext='+font_option+'textfile=title.txt:fontsize=38:fontcolor=white:box=1:boxcolor=black@0.5:x=(w-tw)/2:y=120')
        if p.subtitle.strip():
            (folder/'subtitles.srt').write_text(p.subtitle,encoding='utf-8'); filters.append('subtitles=subtitles.srt:fontsdir=.')
        out=folder/'video.mp4'
        cmd=['ffmpeg','-y','-ss',str(p.start),'-i',a['path'],'-t',str(p.end-p.start),'-vf',','.join(filters),'-c:v','libx264','-preset','fast','-crf','22','-threads','2','-c:a','aac','-movflags','+faststart',str(out)]
        result=subprocess.run(cmd,cwd=folder,capture_output=True,timeout=1800)
        if result.returncode: raise RuntimeError('Không kết xuất được video. Kiểm tra phụ đề SRT và bộ lọc FFmpeg.')
        gate(p)
        if fontfile: fontfile.unlink(missing_ok=True)
        subprocess.run(['ffmpeg','-y','-i',str(out),'-frames:v','1',str(folder/'anh-bia.jpg')],capture_output=True,check=True,timeout=60)
        (folder/'noi-dung.txt').write_text(p.caption+'\n\nTiếp thị liên kết: tôi có thể nhận hoa hồng khi bạn mua qua liên kết.\n'+p.affiliate,encoding='utf-8')
        manifest={'project':p.model_dump(),'rights':json.loads(a['rights']),'source_sha256':a['sha'],'created':now(),'files':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in folder.iterdir() if f.is_file()}}
        (folder/'ho-so.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        archive=ROOT/(ident+'.zip')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for f in folder.iterdir(): z.write(f,f.name)
        gate(p)
        with db() as c:
            c.execute('UPDATE jobs SET state=?,message=?,output=? WHERE id=?',('hoàn thành','Gói nội dung đã sẵn sàng',str(archive),ident)); audit(c,'xuất gói',manifest)
    except Exception as e:
        with db() as c: c.execute('UPDATE jobs SET state=?,message=? WHERE id=?',('thất bại',str(e),ident))
    finally: shutil.rmtree(folder,ignore_errors=True)
@app.post('/api/export')
def export(p:Project,tasks:BackgroundTasks):
    gate(p)
    with EXPORT_LOCK, db() as c:
        if c.execute("SELECT id FROM jobs WHERE state IN ('đang chờ','đang xử lý')").fetchone(): raise HTTPException(409,'Đang có tác vụ kết xuất; vui lòng đợi hoàn tất')
        ident=uid(); c.execute('INSERT INTO jobs VALUES(?,?,?,?)',(ident,'đang chờ','Chuẩn bị kết xuất',''))
    tasks.add_task(render,ident,p)
    return {'message':'Đã đưa vào hàng đợi','id':ident}
@app.get('/api/jobs/{ident}/download')
def download(ident:str):
    with db() as c: j=c.execute('SELECT * FROM jobs WHERE id=?',(ident,)).fetchone()
    if not j or j['state']!='hoàn thành': raise HTTPException(404,'Gói chưa sẵn sàng')
    with zipfile.ZipFile(j['output']) as z: p=Project(**json.loads(z.read('ho-so.json'))['project'])
    gate(p)
    return FileResponse(j['output'],filename='goi-noi-dung.zip')
class ImportRows(BaseModel):
    rows:list[dict]
    code:str
    amount:str
    status:str
STATUS={'pending':'chờ duyệt','approved':'đã duyệt','paid':'đã thanh toán','rejected':'đã hủy','reversed':'đã hủy','chờ duyệt':'chờ duyệt','đã duyệt':'đã duyệt','đã thanh toán':'đã thanh toán','đã hủy':'đã hủy'}
@app.post('/api/conversions/preview')
async def preview(file:UploadFile=File(...)):
    raw=await file.read(10*1024*1024+1)
    if len(raw)>10*1024*1024: raise HTTPException(400,'CSV vượt 10 MB')
    try:
        text=raw.decode('utf-8-sig'); dialect=csv.Sniffer().sniff(text[:8192],delimiters=',;\t'); reader=csv.DictReader(io.StringIO(text),dialect=dialect); rows=list(reader)
    except Exception: raise HTTPException(400,'Không đọc được CSV UTF-8; kiểm tra dấu phân cách và tiêu đề')
    return {'columns':reader.fieldnames,'rows':rows,'count':len(rows)}
@app.post('/api/conversions')
def conversions(body:ImportRows):
    valid=[]; errors=[]
    for i,r in enumerate(body.rows):
        try:
            code=str(r[body.code]).strip(); amount=int(str(r[body.amount]).strip()); status=STATUS[str(r[body.status]).strip().lower()]
            if not code or not 0<=amount<=9_000_000_000_000_000: raise ValueError()
            valid.append((code,amount,status))
        except Exception: errors.append({'line':i+2,'message':'Thiếu mã, số tiền VND nguyên không hợp lệ hoặc trạng thái chưa hỗ trợ'})
    added=updated=duplicate=0
    with db() as c:
        for code,amount,status in valid:
            old=c.execute('SELECT * FROM conversions WHERE code=?',(code,)).fetchone()
            if old and old['amount']==amount and old['status']==status: duplicate+=1; continue
            if old: updated+=1
            else: added+=1
            c.execute('INSERT OR REPLACE INTO conversions VALUES(?,?,?,?)',(code,amount,status,now())); audit(c,'đối soát',{'code':code,'before':dict(old) if old else None,'amount':amount,'status':status})
    return {'message':f'Đã thêm {added}, cập nhật {updated}, bỏ qua {duplicate} bản ghi trùng; {len(errors)} dòng lỗi','errors':errors}
@app.get('/api/health')
def health(): return {'status':'sẵn sàng','ffmpeg':bool(shutil.which('ffmpeg'))}
with db() as c: c.execute("UPDATE jobs SET state='thất bại',message='Ứng dụng đã khởi động lại; hãy xuất lại bản nháp' WHERE state IN ('đang chờ','đang xử lý')")

BACKUPS=ROOT.parent/'backups'
@app.post('/api/backups')
def backup():
    if not EXPORT_LOCK.acquire(blocking=False): raise HTTPException(409,'Đang xử lý tác vụ khác')
    try:
        with db() as c:
            if c.execute("SELECT id FROM jobs WHERE state IN ('đang chờ','đang xử lý')").fetchone(): raise HTTPException(409,'Chờ kết xuất hoàn tất trước khi sao lưu')
        BACKUPS.mkdir(exist_ok=True)
        ident=uid(); archive=BACKUPS/(ident+'.zip')
        # SQLite backup gives a consistent database image while the app runs.
        snapshot=BACKUPS/(ident+'.db')
        with db() as source_db, sqlite3.connect(snapshot) as dest: source_db.backup(dest)
        try:
            with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
                manifest={}
                for f in ROOT.rglob('*'):
                    if f.is_file() and f.name not in ('workspace.db','workspace.db-wal','workspace.db-shm'):
                        name=f.relative_to(ROOT).as_posix(); z.write(f,name); manifest[name]=hashlib.sha256(f.read_bytes()).hexdigest()
                z.write(snapshot,'workspace.db'); manifest['workspace.db']=hashlib.sha256(snapshot.read_bytes()).hexdigest()
                z.writestr('_backup_manifest.json',json.dumps(manifest))
        finally: snapshot.unlink(missing_ok=True)
        return {'message':'Đã tạo bản sao lưu gồm dữ liệu, video và gói xuất','id':ident}
    finally: EXPORT_LOCK.release()
@app.get('/api/backups/{ident}')
def backup_download(ident:str):
    if len(ident)!=32 or any(x not in '0123456789abcdef' for x in ident): raise HTTPException(404,'Không tìm thấy bản sao lưu')
    path=BACKUPS/(ident+'.zip')
    if not path.is_file(): raise HTTPException(404,'Không tìm thấy bản sao lưu')
    return FileResponse(path,filename='sao-luu-mam.zip')
@app.get('/api/audit')
def audit_list():
    with db() as c: return [dict(r) for r in c.execute('SELECT id,kind,created FROM audit ORDER BY id DESC LIMIT 100')]
