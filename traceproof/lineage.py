"""Local, explainable content relationship hints. Not provenance or authorship proof."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from difflib import SequenceMatcher

MAX_FILE = 20_000_000
MAX_FILES = 200
IMAGE_SUFFIXES = {'.png','.jpg','.jpeg','.webp','.bmp','.tif','.tiff'}
TEXT_SUFFIXES = {'.txt','.md','.csv','.json','.html','.xml','.log','.py','.js','.ts','.css'}


def _read(path):
    p=Path(path)
    if not p.is_file() or p.is_symlink() or p.stat().st_size > MAX_FILE:
        raise ValueError('File unavailable, symbolic link, or exceeds 20 MB')
    return p.read_bytes()


def _normalize(data):
    try:
        text=data.decode('utf-8-sig')
    except UnicodeError:
        return None
    return ' '.join(re.findall(r'\w+',text.casefold(),flags=re.UNICODE))


def image_hash(data):
    """64-bit difference hash: similarity hint, never provenance proof."""
    from io import BytesIO
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return None
    try:
        with Image.open(BytesIO(data)) as img:
            img = ImageOps.exif_transpose(img)
            img = img.convert('L').resize((9, 8), Image.Resampling.LANCZOS)
            px = list(img.getdata())
            bits = sum((1 << (r * 8 + c)) for r in range(8) for c in range(8)
                       if px[r * 9 + c] > px[r * 9 + c + 1])
            return f'{bits:016x}'
    except (OSError, ValueError, Image.DecompressionBombError):
        return None


def image_crop_hashes(data):
    """Nine overlapping 70%-size crops; heuristic, not provenance proof."""
    from io import BytesIO
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return []
    try:
        with Image.open(BytesIO(data)) as im:
            im = ImageOps.exif_transpose(im).convert('RGB')
            w, h = im.size
            if min(w,h) < 32: return []
            cw, ch = int(w*.7), int(h*.7)
            result=[]
            for fy in (0,.5,1):
                for fx in (0,.5,1):
                    x,y=round((w-cw)*fx),round((h-ch)*fy)
                    tile=im.crop((x,y,x+cw,y+ch))
                    buf=BytesIO();tile.save(buf,format='PNG')
                    result.append(image_hash(buf.getvalue()))
            return [v for v in result if v]
    except (OSError,ValueError,Image.DecompressionBombError):
        return []


def crop_candidate(x,y,threshold=5):
    a,b=x.get('image_dhash'),y.get('image_dhash')
    if not a or not b:return None
    distances=[image_distance(a,h) for h in y.get('image_crop_hashes',[])]
    distances += [image_distance(b,h) for h in x.get('image_crop_hashes',[])]
    return min(distances) if distances and min(distances)<=threshold else None


def image_distance(a, b):
    return (int(a, 16) ^ int(b, 16)).bit_count()


def fingerprint_bytes(data, name):
    if len(data)>MAX_FILE: raise ValueError("File exceeds 20 MB")
    return _fingerprint_data(data, name)

def _fingerprint_data(data, name):
    p=Path(name)
    text=_normalize(data) if p.suffix.lower() in TEXT_SUFFIXES else None
    return {'image_crop_hashes':image_crop_hashes(data) if p.suffix.lower() in IMAGE_SUFFIXES else [],'image_dhash':image_hash(data) if p.suffix.lower() in IMAGE_SUFFIXES else None,'name':p.name,'sha256':hashlib.sha256(data).hexdigest(),'size':len(data),
            'text_fingerprint':hashlib.sha256(text.encode()).hexdigest() if text is not None else None,
            '_text':text}


def fingerprint(path):
    return _fingerprint_data(_read(path), Path(path).name)

def compare_bytes(a, a_name, b, b_name):
    return compare_fingerprints(fingerprint_bytes(a,a_name), fingerprint_bytes(b,b_name))

def compare_fingerprints(x,y):
    exact=x['sha256']==y['sha256']
    normalized= x['_text'] is not None and y['_text'] is not None and x['text_fingerprint']==y['text_fingerprint']
    ratio=None
    if not exact and not normalized and x['_text'] is not None and y['_text'] is not None:
        # Avoid unbounded quadratic comparisons and misleading cross-language conclusions.
        if max(len(x['_text']),len(y['_text'])) <= 100_000:
            ratio=round(SequenceMatcher(None,x['_text'],y['_text'],autojunk=False).ratio(),4)
    distance = image_distance(x['image_dhash'], y['image_dhash']) if x['image_dhash'] and y['image_dhash'] else None
    crop_distance=crop_candidate(x,y)
    if exact: relation='byte_identical'
    elif normalized: relation='text_normalization_match'
    elif distance is not None and distance <= 6: relation='image_similarity_candidate'
    elif crop_distance is not None: relation='image_crop_candidate'
    elif ratio is not None and ratio >= .85: relation='text_similarity_candidate'
    else: relation='unresolved'
    for obj in (x,y):obj.pop('_text');obj.pop('image_crop_hashes',None)
    return {'schema':'traceproof.lineage.v1','left':x,'right':y,'relation':relation,
            'text_similarity':ratio,'image_hamming_distance':distance,'crop_hamming_distance':crop_distance,'direction':'unknown',
            'warning':'Similarity does not establish origin, editing direction, chronology, identity or AI authorship.'}


def compare(a,b):
    return compare_fingerprints(fingerprint(a),fingerprint(b))

def scan_fingerprints(fingerprints):
    """Compute relationships without retaining source bytes in the returned graph."""
    if len(fingerprints)>MAX_FILES:raise ValueError("More than 200 files")
    edges=[]
    for i,x in enumerate(fingerprints):
        for j in range(i+1,len(fingerprints)):
            y=fingerprints[j]
            if x["sha256"]==y["sha256"]:kind="byte_identical"
            elif x["text_fingerprint"] is not None and x["text_fingerprint"]==y["text_fingerprint"]:kind="text_normalization_match"
            elif x["image_dhash"] and y["image_dhash"] and image_distance(x["image_dhash"],y["image_dhash"])<=6:kind="image_similarity_candidate"
            elif crop_candidate(x,y) is not None:kind="image_crop_candidate"
            else:continue
            edges.append({"left":i,"right":j,"relation":kind,"direction":"unknown"})
    safe=[{k:v for k,v in f.items() if k not in ("_text","image_crop_hashes")} for f in fingerprints]
    return {"schema":"traceproof.lineage.scan.v1","files":safe,"edges":edges,"limitations":["Only explicitly selected files are scanned","Similarity is heuristic, not provenance proof","No inference of original/repost direction","No external clock or identity verification"]}

def scan_bytes(items):
    """Accept (name, bytes) pairs; useful for local HTTP and tests."""
    if len(items)>MAX_FILES:raise ValueError("More than 200 files")
    return scan_fingerprints([fingerprint_bytes(data,name) for name,data in items])

def scan(directory):
    root=Path(directory)
    if not root.is_dir():raise ValueError('Not a directory')
    paths=sorted(p for p in root.iterdir() if p.is_file() and not p.is_symlink())
    if len(paths)>MAX_FILES:raise ValueError('More than 200 files')
    fingerprints=[fingerprint(p) for p in paths]
    return scan_fingerprints(fingerprints)