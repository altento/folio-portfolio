from __future__ import annotations
import hashlib, json, os, tempfile, zipfile
from pathlib import Path

package = Path(__file__).resolve().parents[1]
archive = package.parent / (package.name + '.zip')
excluded_dirs = {'__pycache__'}
files = {}
for path in package.rglob('*'):
    if not path.is_file() or path.name == 'manifest.sha256.json' or path.name.startswith('~$'):
        continue
    if path.parent.name == '01_Отчёты' and path.name in {'Отчет_ООП_Модуль_5.docx', 'Отчет_ООП_Модуль_5.pdf'}:
        continue
    if excluded_dirs.intersection(path.parts) or path.suffix == '.pyc':
        continue
    if path.name in {'portfolio_data.sqlite3', 'portfolio_data.json'}:
        raise SystemExit(f'Personal database must not be packaged: {path}')
    rel = path.relative_to(package).as_posix()
    data = path.read_bytes()
    files[rel] = {'path': rel, 'size_bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
manifest = {'algorithm': 'sha256', 'file_count_excluding_manifest': len(files), 'files': [files[k] for k in sorted(files)]}
(package / 'manifest.sha256.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
fd, temp_name = tempfile.mkstemp(prefix=archive.name + '.', suffix='.tmp', dir=archive.parent)
os.close(fd)
try:
    with zipfile.ZipFile(temp_name, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        prefix = package.name + '/'
        for rel in sorted(files):
            zf.write(package / Path(rel), prefix + rel)
        zf.write(package / 'manifest.sha256.json', prefix + 'manifest.sha256.json')
    Path(temp_name).replace(archive)
finally:
    if os.path.exists(temp_name):
        os.unlink(temp_name)
print(f'Created {archive.name}: {len(files)} files plus manifest, {archive.stat().st_size} bytes')
print(f'ZIP SHA256: {hashlib.sha256(archive.read_bytes()).hexdigest()}')
