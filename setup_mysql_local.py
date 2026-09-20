import os
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

root = Path(r'C:\Users\Am\EMP-System-1')
setup_dir = root / 'mysql_setup'
setup_dir.mkdir(exist_ok=True)
log_path = root / 'mysql_setup.log'

urls = [
    'https://dev.mysql.com/get/Downloads/MySQL-8.0/mysql-8.0.40-winx64.zip',
    'https://cdn.mysql.com/Downloads/MySQL-8.0/mysql-8.0.40-winx64.zip',
    'https://dev.mysql.com/get/Downloads/MySQL-8.0/mysql-8.0.39-winx64.zip',
]

with log_path.open('w', encoding='utf-8') as log:
    log.write('START\n')
    log.write(f'Root={root}\n')
    for idx, url in enumerate(urls, 1):
        zip_path = setup_dir / f'mysql_{idx}.zip'
        log.write(f'Trying URL {idx}: {url}\n')
        try:
            urllib.request.urlretrieve(url, zip_path)
            log.write(f'Downloaded: {zip_path} size={zip_path.stat().st_size}\n')
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(setup_dir)
            log.write(f'Extracted: {setup_dir}\n')
            extracted = sorted(p for p in setup_dir.iterdir() if p.is_dir())
            log.write(f'Folders: {[str(p.name) for p in extracted]}\n')
            raise SystemExit(0)
        except Exception as exc:
            log.write(f'Error: {type(exc).__name__}: {exc}\n')
            if zip_path.exists():
                try:
                    zip_path.unlink()
                except Exception:
                    pass
    log.write('ALL_DOWNLOAD_ATTEMPTS_FAILED\n')
    raise SystemExit(1)
