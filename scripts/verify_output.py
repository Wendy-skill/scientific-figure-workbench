#!/usr/bin/env python3
"""Independently verify an output package against its *original* CSV.

Checks file content/hash, per-group descriptive statistics, figure artifact
presence, PNG resolution, and presence of editable SVG <text> elements.
No recomputation mutates the CSV or outputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from PIL import Image

NAMES = (
    'R01_overview', 'R02_scatter3d', 'R03_violin', 'R04_bar_scatter',
    'R05_raincloud', 'R06_orthogonal_views',
)
STAT_KEYS = {
    'mean': lambda s: s.mean(),
    'sample_sd_ddof1': lambda s: s.std(ddof=1),
    'median': lambda s: s.median(),
    'q1': lambda s: s.quantile(.25),
    'q3': lambda s: s.quantile(.75),
    'min': lambda s: s.min(),
    'max': lambda s: s.max(),
}


def verify(source: Path, folder: Path) -> list[str]:
    errors: list[str] = []
    audit = json.loads((folder/'analysis_audit.json').read_text(encoding='utf-8'))
    config = json.loads((folder/'run_config.json').read_text(encoding='utf-8'))
    frame = pd.read_csv(source)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if audit['source_sha256'] != source_hash:
        errors.append('Input SHA256 differs from recorded value')
    if len(frame) != audit['source_rows']:
        errors.append('Source row count differs from audit')
    group_col = audit['group_column']
    value_col = audit['value_column']
    if audit.get('source_rows_dropped') != 0:
        errors.append('Audit indicates dropped rows')
    for label, recorded in audit['groups'].items():
        response = pd.to_numeric(frame.loc[frame[group_col].astype(str)==label,value_col],errors='raise')
        if len(response) != recorded['n']:
            errors.append(f'{label} sample size mismatch')
        for key, func in STAT_KEYS.items():
            actual = float(func(response))
            if not math.isclose(actual,recorded[key],rel_tol=1e-10,abs_tol=1e-10):
                errors.append(f'{label} {key} mismatch: {actual} != {recorded[key]}')
    if sum(int(v['n']) for v in audit['groups'].values()) != len(frame):
        errors.append('Group counts do not sum to dataset count')
    lo,hi = audit['shared_value_axis_range_B_C_D']
    values = pd.to_numeric(frame[value_col])
    if not (lo <= 0 <= hi and lo <= values.min() and hi >= values.max()):
        errors.append('Shared axis clips data or omits the mean-bar zero baseline')
    for group in audit['groups'].values():
        if group['mean'] - group['sample_sd_ddof1'] < lo or group['mean'] + group['sample_sd_ddof1'] > hi:
            errors.append('Shared axis clips mean ± sample SD')
    for stem in NAMES:
        for ext in ('png','svg','pdf'):
            target = folder/'figures'/f'{stem}.{ext}'
            if not target.is_file() or target.stat().st_size < 100:
                errors.append(f'Missing or empty figure: {target.name}')
        png = folder/'figures'/f'{stem}.png'
        if png.exists():
            with Image.open(png) as image:
                resolution = image.info.get('dpi', (0,0))
                if any(abs(x-config['dpi']) > 2 for x in resolution):
                    errors.append(f'{stem} PNG expected {config["dpi"]} dpi, got {resolution}')
        svg = folder/'figures'/f'{stem}.svg'
        if svg.exists():
            root = ET.parse(svg).getroot()
            if not any(el.tag.endswith('text') for el in root.iter()):
                errors.append(f'{stem} has no editable SVG text objects')
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',type=Path,required=True,help='Original CSV to independently re-read')
    ap.add_argument('--output',type=Path,required=True,help='Folder produced by plot_figures.py')
    args = ap.parse_args()
    errs = verify(args.input,args.output)
    if errs:
        print(f'FAILED: {len(errs)} issue(s) found')
        for e in errs:
            print(' -',e)
        raise SystemExit(1)
    print('PASS: input checksum, group statistics, shared axis limits, 18 figure files, PNG DPI and editable SVG text')


if __name__ == '__main__':
    main()