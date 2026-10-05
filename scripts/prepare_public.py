"""Build an allowlisted public directory; preserve all source/private files."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from PIL import Image

FILES = [
    'README.md', '.gitignore', 'requirements.txt', 'requirements-detector.txt',
    'scripts/detect.py', 'scripts/evaluate.py', 'scripts/test_evaluate.py',
    'scripts/make_figure.py', 'scripts/export_figures_qgis.py', 'scripts/prepare_public.py',
    'data/initial_samples.json', 'data/reviewed_samples.json',
    'results/reviewed_evaluation.json', 'results/detector_reproduction.json',
    'docs/results.svg', 'docs/FIGURES.md', 'docs/rgb_flowers.png', 'docs/ndvi_mean.png',
]


def png_chunks(path):
    data = path.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    offset, chunks = 8, []
    while offset < len(data):
        length = struct.unpack('>I', data[offset:offset+4])[0]
        chunks.append(data[offset+4:offset+8].decode('ascii'))
        offset += 12+length
    assert offset == len(data)
    return chunks


def build(source, output):
    if output.exists():
        raise FileExistsError('Choose a new output directory; existing directories are not overwritten')
    # Validate before creating the destination.
    for name in FILES:
        if not (source/name).is_file():
            raise FileNotFoundError(name)
    for name in ['initial', 'reviewed']:
        data = json.loads((source/f'data/{name}_samples.json').read_text(encoding='utf-8'))
        assert data['coordinate_system'] == 'Local origin per sector; not georeferenced'
        for sector in data['samples']:
            for key in ['reference', 'predictions', 'uncertain']:
                assert all(len(p)==2 and all(0 <= v <= 5 for v in p) for p in sector[key])
    output.mkdir(parents=True)
    records = []
    for name in FILES:
        src, dst = source/name, output/name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() == '.png':
            with Image.open(src) as img:
                pixels = img.convert('RGB')
                clean = Image.frombytes('RGB', pixels.size, pixels.tobytes())
                clean.save(dst, format='PNG')
            chunks = png_chunks(dst)
            assert set(chunks) <= {'IHDR', 'IDAT', 'IEND'}, chunks
            with Image.open(dst) as check:
                assert not check.info and not check.getexif()
            record = dict(file=name, png_chunks=sorted(set(chunks)), metadata_removed=True)
        else:
            text = src.read_text(encoding='utf-8')
            # Reject absolute Windows user paths and explicit metadata coordinate tags.
            assert not re.search(r'[A-Za-z]:[\\/]Users[\\/]', text), name
            if src.suffix.lower() in {'.json', '.svg'}:
                assert not re.search(r'GPSLatitude|GPSLongitude|geotransform', text, re.I), name
            dst.write_text(text, encoding='utf-8')
            record = dict(file=name)
        record['sha256'] = hashlib.sha256(dst.read_bytes()).hexdigest()
        records.append(record)
    report = dict(scope='Allowlisted public package only; originals unchanged',
                  excluded=['data/private', 'GeoTIFF', 'GeoPackage', 'QGIS projects', 'world files', '__pycache__'],
                  limitation='Visible landscape can still be recognized; no claim of visual anonymity', files=records)
    (output/'publication_audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return len(records)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print('Files prepared:', build(Path(__file__).resolve().parents[1], args.output.resolve()))
