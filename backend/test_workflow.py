import os, tempfile, unittest, subprocess, json, zipfile, io
from pathlib import Path
TEMP=tempfile.TemporaryDirectory()
os.environ['MAM_DATA_DIR']=str(Path(TEMP.name)/'data')
from fastapi.testclient import TestClient
from backend.main import app, ROOT

class Workflow(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.client=TestClient(app)
  cls.video=Path(TEMP.name)/'sample.mp4'
  subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=green:s=320x240:d=2','-f','lavfi','-i','sine=frequency=440:duration=2','-c:v','libx264','-threads','1','-c:a','aac','-shortest',str(cls.video)],check=True)
 def test_01_sources(self):
  c=self.client
  body={'title':'Ý tưởng thử nghiệm','url':'https://www.tiktok.com/@test/video/123','platform':'TikTok'}
  self.assertEqual(c.post('/api/sources',json=body).status_code,200)
  self.assertEqual(c.post('/api/sources',json=body).status_code,409)
  body['url']='https://127.0.0.1/private'
  self.assertEqual(c.post('/api/sources',json=body).status_code,400)
  self.assertEqual(c.post('/api/sources',json=body,headers={'Origin':'https://evil.example'}).status_code,403)
 def test_015_source_batch(self):
  content='Tên nguồn,Liên kết,Nền tảng\nNguồn mới,https://www.facebook.com/reel/456,Facebook\nNguồn trùng,https://www.facebook.com/reel/456,Facebook\nNguồn lỗi,http://localhost,Facebook\n'
  r=self.client.post('/api/sources/import',files={'file':('sources.csv',content.encode(),'text/csv')})
  self.assertEqual(r.status_code,200,r.text); self.assertEqual(len(r.json()['errors']),1)
  self.assertIn('1 nguồn trùng',r.json()['message'])
 def test_02_render_and_rights(self):
  c=self.client
  content=self.video.read_bytes()
  r=c.post('/api/assets',files={'file':('video.mp4',content,'video/mp4')}); self.assertEqual(r.status_code,200,r.text)
  self.assertEqual(c.post('/api/assets',files={'file':('other.mp4',content,'video/mp4')}).status_code,409)
  self.assertEqual(c.post('/api/assets',files={'file':('fake.mp4',b'not a video','video/mp4')}).status_code,400)
  asset=c.get('/api/state').json()['assets'][0]
  self.assertNotIn('path',asset)
  p={'asset':asset['id'],'title':'Video kiểm thử','channel':'Facebook','start':0,'end':1,'overlay':'Góc bếp nhỏ','subtitle':'1\n00:00:00,000 --> 00:00:00,900\nPhụ đề tiếng Việt\n','product':'Sản phẩm thử','affiliate':'https://s.shopee.vn/abc','caption':'Nội dung thử nghiệm','matched':True,'reviewed':True}
  self.assertEqual(c.post('/api/export',json=p).status_code,400)
  rights={'owner':'Tự tạo','evidence':'Video kiểm thử do bộ kiểm thử tạo bằng FFmpeg','channels':['Facebook'],'expiry':'2099-12-31','commercial':True,'edit':True,'music':True}
  self.assertEqual(c.put('/api/assets/'+asset['id']+'/rights',json=rights).status_code,200)
  blocked={**p,'channel':'TikTok'}
  self.assertEqual(c.post('/api/export',json=blocked).status_code,400)
  self.assertEqual(c.post('/api/export',json={**p,'matched':False}).status_code,400)
  for change in [{'music':False},{'expiry':'2020-01-01'}]:
   c.put('/api/assets/'+asset['id']+'/rights',json={**rights,**change})
   self.assertEqual(c.post('/api/export',json=p).status_code,400)
  c.put('/api/assets/'+asset['id']+'/rights',json=rights)
  saved=c.post('/api/projects',json=p).json(); self.assertTrue(saved['id'])
  r=c.post('/api/export',json=p); self.assertEqual(r.status_code,200,r.text)
  state=c.get('/api/state').json(); job=state['jobs'][0]; self.assertEqual(job['state'],'hoàn thành',job)
  z=c.get('/api/jobs/'+r.json()['id']+'/download'); self.assertEqual(z.status_code,200,z.text[:200] if z.status_code!=200 else '')
  with zipfile.ZipFile(io.BytesIO(z.content)) as archive:
   self.assertIn('video.mp4',archive.namelist()); self.assertIn('anh-bia.jpg',archive.namelist()); manifest=json.loads(archive.read('ho-so.json')); self.assertEqual(manifest['source_sha256'],asset['sha'])
   out=Path(TEMP.name)/'output.mp4'; out.write_bytes(archive.read('video.mp4'))
  probe=subprocess.run(['ffprobe','-v','error','-show_streams','-of','json',str(out)],capture_output=True,text=True,check=True)
  stream=next(s for s in json.loads(probe.stdout)['streams'] if s['codec_type']=='video')
  self.assertEqual((stream['width'],stream['height']),(720,1280))
  rights['expiry']='2020-01-01'; c.put('/api/assets/'+asset['id']+'/rights',json=rights)
  self.assertEqual(c.get('/api/jobs/'+r.json()['id']+'/download').status_code,400)
 def test_03_commission(self):
  c=self.client
  csv='Mã,Hoa hồng,Trạng thái\n001,10000,pending\n002,20000,approved\n003,không hợp lệ,paid\n'
  r=c.post('/api/conversions/preview',files={'file':('report.csv',csv.encode(),'text/csv')}); self.assertEqual(r.status_code,200)
  payload={'rows':r.json()['rows'],'code':'Mã','amount':'Hoa hồng','status':'Trạng thái'}
  first=c.post('/api/conversions',json=payload).json(); self.assertEqual(len(first['errors']),1)
  self.assertIn('bỏ qua 2',c.post('/api/conversions',json=payload).json()['message'])
  payload['rows'][0]['Trạng thái']='rejected'; c.post('/api/conversions',json=payload)
  rows=c.get('/api/state').json()['conversions']; self.assertEqual(len(rows),2); self.assertEqual(next(r for r in rows if r['code']=='001')['status'],'đã hủy')
 def test_04_live_backup(self):
  r=self.client.post('/api/backups'); self.assertEqual(r.status_code,200,r.text)
  r=self.client.get('/api/backups/'+r.json()['id']); self.assertEqual(r.status_code,200)
  with zipfile.ZipFile(io.BytesIO(r.content)) as z: self.assertIn('workspace.db',z.namelist())
 def test_05_backup(self):
  archive=Path(TEMP.name)/'backup.zip'; restore=Path(TEMP.name)/'restored'
  for args in [['backup',str(archive),'--data',str(ROOT)],['verify',str(archive)],['restore',str(archive),'--data',str(restore)]]:
   r=subprocess.run([os.sys.executable,'scripts/sao_luu.py',*args],capture_output=True,text=True); self.assertEqual(r.returncode,0,r.stderr)
  import sqlite3
  with sqlite3.connect(restore/'workspace.db') as c:
   self.assertEqual(c.execute('SELECT COUNT(*) FROM conversions').fetchone()[0],2)
   path=c.execute('SELECT path FROM assets').fetchone()[0]; self.assertTrue(Path(path).is_file())
   self.assertTrue(c.execute('SELECT rights FROM assets').fetchone()[0])
if __name__=='__main__': unittest.main()
