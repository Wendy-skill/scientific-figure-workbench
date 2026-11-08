#!/usr/bin/env python3
"""Generate reproducible, explicitly SYNTHETIC teaching data (not real measurements)."""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=Path('examples/demo_experiment.csv'))
    ap.add_argument('--n', type=int, default=180, help='Synthetic records per group')
    ap.add_argument('--seed', type=int, default=2026)
    args=ap.parse_args()
    if args.n < 5: raise ValueError('For this KDE demo, n must be at least 5 per group')
    rng=np.random.default_rng(args.seed)
    chunks=[]
    for group, shape, scale in [('Control', 16., .95), ('Treatment', 18., 1.32)]:
        response=rng.gamma(shape=shape,scale=scale,size=args.n)
        x1=0.55*response+rng.normal(1.5,1.4,args.n)
        x2=0.91*response+rng.normal(4.0,3.3,args.n)
        x3=0.045*response+rng.normal(0.12,0.13,args.n)
        chunks.append(pd.DataFrame({'Group':group,'Feature X1':x1,'Feature X2':x2,
                                    'Feature X3':x3,'Response Y':response}))
    data=pd.concat(chunks,ignore_index=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    data.to_csv(args.output,index=False,float_format='%.8f')
    print(f'Created {len(data)} SYNTHETIC rows. Not experimental or clinical evidence: {args.output}')

if __name__ == '__main__': main()