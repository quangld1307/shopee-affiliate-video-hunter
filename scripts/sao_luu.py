"""Dừng ứng dụng trước khi sao lưu/khôi phục. Không ghi đè dữ liệu hiện có."""
import argparse, zipfile, sqlite3, json, hashlib
from pathlib import Path
from datetime import datetime
p=argparse.ArgumentParser(description='Sao lưu và kiểm tra dữ liệu Mầm')
p.add_argument('action',choices=['backup','verify','restore'])
p.add_argument('archive',type=Path)
p.add_argument('--data',type=Path,default=Path(__file__).resolve().parents[1]/'data')
a=p.parse_args()
if a.action=='backup':
    if a.archive.exists(): p.error('Tệp sao lưu đã tồn tại; chọn tên khác')
    if not (a.data/'workspace.db').is_file(): p.error('Không tìm thấy dữ liệu')
    with zipfile.ZipFile(a.archive,'x',zipfile.ZIP_DEFLATED) as z:
        manifest={}
        for f in a.data.rglob('*'):
            if f.is_file():
                name=f.relative_to(a.data).as_posix(); manifest[name]=hashlib.sha256(f.read_bytes()).hexdigest(); z.write(f,name)
        z.writestr('_backup_manifest.json',json.dumps(manifest))
    print('Đã sao lưu. Chạy verify và thử restore vào thư mục mới để xác minh.')
else:
    with zipfile.ZipFile(a.archive) as z:
        manifest=json.loads(z.read('_backup_manifest.json'))
        for name,sha in manifest.items():
            path=Path(name)
            if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name: p.error('Đường dẫn sao lưu không an toàn')
            if hashlib.sha256(z.read(name)).hexdigest()!=sha: p.error('Checksum không khớp: '+name)
        if a.action=='restore':
            if a.data.exists() and any(a.data.iterdir()): p.error('Chỉ khôi phục vào thư mục trống để bảo vệ dữ liệu hiện có')
            a.data.mkdir(parents=True,exist_ok=True)
            for name in manifest:
                f=a.data/name; f.parent.mkdir(parents=True,exist_ok=True); f.write_bytes(z.read(name))
            # Absolute storage paths must follow the restored folder.
            with sqlite3.connect(a.data/'workspace.db') as c:
                for table,column in [('assets','path'),('jobs','output')]:
                    for ident,path in c.execute(f'SELECT id,{column} FROM {table}').fetchall():
                        if path: c.execute(f'UPDATE {table} SET {column}=? WHERE id=?',(str((a.data/Path(path).name).resolve()),ident))
                if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok': p.error('Cơ sở dữ liệu không toàn vẹn')
            print('Đã khôi phục; kiểm tra video, quyền và gói trước khi sử dụng.')
        else: print('Checksum toàn bộ bản sao lưu hợp lệ.')
