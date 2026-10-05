"""Generate a portable SVG directly from evaluated counts (standard library)."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
rows = json.loads((root / 'results/reviewed_evaluation.json').read_text(encoding='utf-8'))
svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="560" viewBox="0 0 960 560">',
       '<rect width="960" height="560" fill="#101d29"/>',
       '<g font-family="Arial, sans-serif" fill="#edf4f7">',
       '<text x="45" y="52" font-size="27">Flores visibles: revisión de seis sectores</text>',
       '<text x="45" y="86" font-size="16">229 / 286 confirmadas detectadas · 80,1 % · tolerancia 15 cm</text>']
for i, row in enumerate(rows):
    y = 125 + i * 53
    matched, missed = row['matched'], row['missed']
    svg += [f'<text x="45" y="{y+22}" font-size="18">{row["sector"]}</text>',
            f'<rect x="110" y="{y}" width="{matched*10}" height="30" rx="3" fill="#36c6a0"/>',
            f'<rect x="{110+matched*10}" y="{y}" width="{missed*10}" height="30" fill="#ffbb66"/>',
            f'<text x="710" y="{y+22}" font-size="17">{matched}/{row["reference"]} · {100*row["recall"]:.1f}%</text>']
svg += ['<rect x="45" y="463" width="14" height="14" fill="#36c6a0"/>',
        '<text x="68" y="476" font-size="16">Detectadas</text>',
        '<rect x="230" y="463" width="14" height="14" fill="#ffbb66"/>',
        '<text x="253" y="476" font-size="16">Omitidas</text>',
        '<text x="45" y="514" font-size="14">Muestra dirigida de un mosaico. Incluye 15 referencias añadidas tras revisar predicciones.</text>',
        '<text x="45" y="538" font-size="14">2 dudosas excluidas. Revisión asistida; no representa exactitud en todo el lote.</text>',
        '</g></svg>']
target = root / 'docs/results.svg'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text('\n'.join(svg), encoding='utf-8')
print(target)
