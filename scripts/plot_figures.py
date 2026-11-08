#!/usr/bin/env python3
"""Audited, reproducible, four-panel scientific figure demonstration.

The script is intentionally restricted to exactly two groups with three numeric
features and one numeric response. For other experimental designs, consult the
Skill and adapt the visual selection instead of coercing the data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde
import scipy


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True, type=Path, help='Original CSV containing per-row observations')
    p.add_argument('--output', required=True, type=Path, help='Directory for all figures/audits')
    p.add_argument('--group', default='Group', help='Class/group column')
    p.add_argument('--x', default='Feature X1', help='3D x-axis numeric feature')
    p.add_argument('--y', default='Feature X2', help='3D y-axis numeric feature')
    p.add_argument('--z', default='Feature X3', help='3D z-axis numeric feature')
    p.add_argument('--value', default='Response Y', help='Common numeric response for panels B/C/D')
    p.add_argument('--group-order', default=None, help='Comma separated order of the two group labels')
    p.add_argument('--ylim', default=None, help='Optional shared y limits of B/C/D as min,max; must include 0 for bars')
    p.add_argument('--unit', default=None, help='Response unit from source documentation ONLY; do not guess')
    p.add_argument('--colors', default='#7C8288,#8754B4', help='Two comma-separated hex colours')
    p.add_argument('--seed', type=int, default=17, help='RNG seed for categorical jitter only')
    p.add_argument('--dpi', type=int, default=300, help='PNG export resolution')
    p.add_argument('--snapshot-input', action='store_true', help='Copy full input CSV (avoid for restricted data)')
    return p.parse_args()


def die(msg):
    raise ValueError(msg)


def clean_and_audit(args):
    if not args.input.is_file():
        die(f'Input CSV does not exist: {args.input}')
    df = pd.read_csv(args.input, low_memory=False)
    if df.empty:
        die('Input CSV has no rows')
    requested = list(dict.fromkeys([args.group, args.x, args.y, args.z, args.value]))
    absent = [c for c in requested if c not in df.columns]
    if absent:
        die(f'Required column(s) missing: {absent}. Available columns: {df.columns.tolist()}')
    null_count = {c: int(df[c].isna().sum()) for c in requested}
    if any(null_count.values()):
        die(f'Required columns contain missing values (no automatic deletion/imputation): {null_count}')
    original_labels = df[args.group]
    if (original_labels.astype(str).str.strip() == '').any():
        die('Empty group labels detected')
    df[args.group] = original_labels.astype(str)
    numeric_cols = list(dict.fromkeys([args.x, args.y, args.z, args.value]))
    for c in numeric_cols:
        converted = pd.to_numeric(df[c], errors='coerce')
        if converted.isna().any() or not np.isfinite(converted.to_numpy(dtype=float)).all():
            die(f'Column {c!r} contains nonnumeric or nonfinite values; no rows were changed')
        df[c] = converted.astype(float)
    labels_found = df[args.group].unique().tolist()
    labels = [s.strip() for s in args.group_order.split(',')] if args.group_order else sorted(labels_found)
    if len(labels) != 2 or len(set(labels)) != 2 or set(labels) != set(labels_found):
        die(f'Four-panel demo needs exactly two groups. Found {labels_found}; order requested {labels}')
    colours = [x.strip() for x in args.colors.split(',')]
    if len(colours) != 2 or not all(mcolors.is_color_like(c) for c in colours):
        die(f'Expected two valid colours, got {colours}')
    groupdata = [df.loc[df[args.group] == label, args.value].to_numpy(dtype=float) for label in labels]
    if any(len(g) < 2 for g in groupdata):
        die('At least 2 observations per group are required for sample SD')
    sd = [float(np.std(g, ddof=1)) for g in groupdata]
    means = [float(np.mean(g)) for g in groupdata]
    min_needed = min(float(df[args.value].min()), *[m-s for m,s in zip(means, sd)], 0.0)
    max_needed = max(float(df[args.value].max()), *[m+s for m,s in zip(means, sd)], 0.0)
    if args.ylim:
        try:
            lo, hi = (float(s.strip()) for s in args.ylim.split(','))
        except Exception as exc:
            raise ValueError('--ylim must be min,max, e.g. 0,30') from exc
        if not np.isfinite([lo,hi]).all() or hi <= lo:
            die('Invalid --ylim range')
        if lo > 0 or hi < 0:
            die('Mean bars require a zero baseline in the shared y axis')
        if lo > min_needed + 1e-9 or hi < max_needed - 1e-9:
            die(f'--ylim {lo},{hi} clips raw values or mean±SD; required [{min_needed:.4g},{max_needed:.4g}]')
    else:
        r = max(max_needed-min_needed, 1.)
        lo,hi = min_needed-0.04*r, max_needed+0.07*r
        if min_needed >= 0:
            lo = 0.
    group_audit = {}
    for label, v in zip(labels, groupdata):
        group_audit[label] = {
            'n': len(v), 'mean': float(np.mean(v)),
            'sample_sd_ddof1': float(np.std(v, ddof=1)),
            'median': float(np.median(v)), 'q1': float(np.quantile(v, 0.25)),
            'q3': float(np.quantile(v, 0.75)),
            'min': float(np.min(v)), 'max': float(np.max(v))
        }
    checksum = hashlib.sha256(args.input.read_bytes()).hexdigest()
    audit = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'source_csv_path': str(args.input.resolve()), 'source_sha256': checksum,
        'source_rows': int(len(df)), 'source_columns': list(pd.read_csv(args.input, nrows=0).columns),
        'duplicate_full_rows_preserved': int(pd.read_csv(args.input).duplicated().sum()),
        'required_columns': requested, 'required_column_missing_counts': null_count,
        'group_column': args.group, 'groups': group_audit,
        'value_column': args.value, 'value_unit': args.unit,
        'three_dimensional_features': [args.x,args.y,args.z],
        'shared_value_axis_range_B_C_D': [lo,hi],
        'error_bars': 'arithmetic mean +/- sample SD, ddof=1',
        'point_jitter': 'visual displacement of categorical x-coordinate only; raw y-values unchanged',
        'kde': 'Gaussian KDE with Scott bandwidth, only if each group has >=5 nonconstant values',
        'source_rows_dropped': 0,
        'inferential_statistics': 'none',
        'warnings': ['Static 3D has depth ambiguity; see R06 orthogonal 2D projections.'],
        'packages': {'python': platform.python_version(), 'numpy': np.__version__,
                     'pandas': pd.__version__, 'matplotlib': matplotlib.__version__,
                     'scipy': scipy.__version__}
    }
    for label, g in zip(labels, groupdata):
        if len(g) < 5 or np.unique(g).size < 3 or np.std(g) < 1e-12:
            audit['warnings'].append(f'KDE omitted for group {label}: too few distinct observations')
    return df, labels, colours, groupdata, (lo,hi), audit


def style():
    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 10.5,
        'axes.labelsize': 11.5, 'axes.titlesize': 12.0,
        'xtick.labelsize': 10.5, 'ytick.labelsize': 10.5,
        'axes.linewidth': .85, 'xtick.major.width': .85,
        'ytick.major.width': .85, 'xtick.direction': 'out', 'ytick.direction': 'out',
        'xtick.major.size': 4, 'ytick.major.size': 4,
        'svg.fonttype': 'none', 'pdf.fonttype': 42,
        'savefig.facecolor': 'white', 'figure.facecolor': 'white',
    })


def decorate(ax):
    for side in ('top','right'):
        ax.spines[side].set_visible(False)
    for side in ('bottom','left'):
        ax.spines[side].set_linewidth(.9)
    ax.grid(axis='y', color='#e4e8ec', lw=.6, alpha=.65)
    ax.set_axisbelow(True)


def y_label(args):
    return args.value if not args.unit else f'{args.value} ({args.unit})'


def label_groups(ax, labels, data, ylim):
    ax.set_xticks([1,2], [f'{label}\n(n={len(v)})' for label,v in zip(labels,data)])
    ax.set_xlim(.45, 2.55)
    ax.set_ylim(*ylim)


def plot_3d(ax, df, args, labels, colours):
    for label, colour, marker in zip(labels, colours, ['o','s']):
        part = df[df[args.group] == label]
        ax.scatter(part[args.x], part[args.y], part[args.z],
                   c=colour, marker=marker, s=16, alpha=.52,
                   linewidths=.23, edgecolors='white', depthshade=False,
                   label=f'{label} (n={len(part)})', rasterized=False)
    ax.set_xlabel(args.x, labelpad=7)
    ax.set_ylabel(args.y, labelpad=7)
    ax.set_zlabel(args.z, labelpad=7)
    ax.view_init(elev=20, azim=-58)
    for axis in [ax.xaxis,ax.yaxis,ax.zaxis]:
        axis.pane.fill = False
        axis.line.set_color('#b9c3cb')
        axis._axinfo['grid']['color'] = (0.80,0.84,0.87,0.42)
    ax.tick_params(pad=0, labelsize=8.5)
    ax.set_box_aspect((1.1,1,.87))


def kde_ok(v):
    return len(v) >= 5 and np.unique(v).size >= 3 and np.std(v)>1e-12


def add_points(ax, groupdata, colours, seed, centers=(1,2), x_offset=0.0, spread=.11, alpha=.39, size=13):
    rng=np.random.default_rng(seed)
    for idx,(v,color) in enumerate(zip(groupdata,colours)):
        xs=centers[idx]+x_offset+rng.uniform(-spread,spread,len(v))
        ax.scatter(xs,v,s=size,c=color,alpha=alpha,edgecolors='white',
                   linewidths=.25,zorder=4,rasterized=False)


def plot_violin(ax,args,labels,colours,groupdata,ylim):
    for p,(v,color) in enumerate(zip(groupdata,colours),1):
        if kde_ok(v):
            vp=ax.violinplot([v],positions=[p],widths=.6,showmeans=False,
                             showmedians=False,showextrema=False,bw_method='scott',points=150)
            for body in vp['bodies']:
                body.set_facecolor(color);body.set_edgecolor(color)
                body.set_alpha(.23);body.set_linewidth(.9)
        q1,median,q3=np.quantile(v,[.25,.5,.75])
        ax.plot([p,p],[q1,q3],color='#28343f',linewidth=4,zorder=5,solid_capstyle='round')
        ax.scatter([p],[median],s=25,facecolors='white',edgecolors='#23313c',linewidths=.9,zorder=7)
    add_points(ax,groupdata,colours,args.seed+1,x_offset=.19,spread=.09,alpha=.30,size=9)
    label_groups(ax,labels,groupdata,ylim)
    ax.set_ylabel(y_label(args))
    decorate(ax)


def plot_bar_scatter(ax,args,labels,colours,groupdata,ylim):
    means=[np.mean(v) for v in groupdata]
    sds=[np.std(v,ddof=1) for v in groupdata]
    ax.bar([1,2],means,width=.55,color=colours,alpha=.25,
           edgecolor=colours,linewidth=1.3,zorder=1)
    ax.errorbar([1,2],means,yerr=sds,fmt='none',ecolor='#26323e',
                linewidth=1.2,capsize=5,capthick=1.2,zorder=6)
    add_points(ax,groupdata,colours,args.seed+2,spread=.22,alpha=.42,size=13)
    label_groups(ax,labels,groupdata,ylim)
    ax.set_ylabel(y_label(args))
    ax.text(.02,.98,'Bars: mean  |  error bars: sample SD',transform=ax.transAxes,
            ha='left',va='top',fontsize=8.4,color='#3d4b58')
    decorate(ax)


def plot_raincloud(ax,args,labels,colours,groupdata,ylim):
    rng=np.random.default_rng(args.seed+3)
    for pos,(v,color) in enumerate(zip(groupdata,colours),1):
        if kde_ok(v):
            # Limit KDE cloud to the observed range; otherwise a Gaussian estimate
            # would visually suggest measured support outside min/max.
            ys=np.linspace(float(v.min()),float(v.max()),300)
            density=gaussian_kde(v,bw_method='scott')(ys)
            den=density/max(float(np.max(density)),1e-12)*.35
            ax.fill_betweenx(ys,pos-.09-den,pos-.09,facecolor=color,
                             alpha=.26,edgecolor=color,linewidth=1,zorder=2)
        q1,med,q3=np.quantile(v,[.25,.5,.75])
        low,high=float(v.min()),float(v.max())
        mid=pos+.045
        ax.plot([mid,mid],[low,high],c='#34434f',lw=.8,zorder=5)
        ax.plot([mid-.055,mid+.055],[low,low],c='#34434f',lw=.8,zorder=5)
        ax.plot([mid-.055,mid+.055],[high,high],c='#34434f',lw=.8,zorder=5)
        ax.add_patch(Rectangle((mid-.09,q1),.18,q3-q1,
                               facecolor='white',edgecolor='#34434f',lw=1.1,zorder=6))
        ax.plot([mid-.09,mid+.09],[med,med],color=color,lw=2.1,zorder=7)
        # Plot every original response value. Spread changes categorical position only.
        xs=pos+.29+rng.uniform(-.085,.085,len(v))
        ax.scatter(xs,v,c=color,s=10,alpha=.36,edgecolors='white',
                   linewidths=.22,zorder=4)
    label_groups(ax,labels,groupdata,ylim)
    ax.set_xlim(.38,2.52)
    ax.set_ylabel(y_label(args))
    decorate(ax)


def plot_projections(fig,df,args,labels,colours):
    pairs=[(args.x,args.y),(args.x,args.z),(args.y,args.z)]
    axs=fig.subplots(1,3)
    for i,(ax,(x,y)) in enumerate(zip(axs,pairs)):
        for label,color,mark in zip(labels,colours,['o','s']):
            part=df.loc[df[args.group]==label]
            ax.scatter(part[x],part[y],c=color,marker=mark,s=13,alpha=.38,
                       linewidths=.2,edgecolors='white',rasterized=False)
        ax.set_xlabel(x,fontsize=10)
        ax.set_ylabel(y,fontsize=10)
        ax.set_title('('+ 'ABC'[i]+')',loc='left',fontweight='bold',fontsize=11)
        decorate(ax)
    fig.suptitle('Three orthogonal 2D projections',fontsize=15,y=.96)
    fig.legend(handles=legend_handles(labels,colours,df[args.group]),
               loc='upper center',bbox_to_anchor=(.5,.90),ncol=2,frameon=False)
    fig.subplots_adjust(top=.77,bottom=.17,left=.085,right=.98,wspace=.40)


def legend_handles(labels, colours, groups):
    return [Line2D([],[],linestyle='',marker=m,markersize=7,
                   markerfacecolor=c,markeredgecolor='white',
                   label=f'{label} (n={int((groups==label).sum())})')
            for label,c,m in zip(labels,colours,['o','s'])]


def save_all(fig,outbase,dpi):
    for ext in ('png','svg','pdf'):
        fig.savefig(outbase.with_suffix('.'+ext),dpi=dpi,facecolor='white')


def main():
    args=parse_args()
    df,labels,colours,groupdata,ylim,audit=clean_and_audit(args)
    style()
    args.output.mkdir(parents=True,exist_ok=True)
    figures=args.output/'figures'
    figures.mkdir(exist_ok=True)
    if args.snapshot_input:
        target=args.output/'plot_source.csv'
        if args.input.resolve() != target.resolve():
            shutil.copyfile(args.input,target)
        # The source may already be in this folder; do not overwrite itself.
    functions=[('R02_scatter3d',lambda ax:plot_3d(ax,df,args,labels,colours),True),
               ('R03_violin',lambda ax:plot_violin(ax,args,labels,colours,groupdata,ylim),False),
               ('R04_bar_scatter',lambda ax:plot_bar_scatter(ax,args,labels,colours,groupdata,ylim),False),
               ('R05_raincloud',lambda ax:plot_raincloud(ax,args,labels,colours,groupdata,ylim),False)]
    names=['3D feature space','Distribution + raw observations',
           'Group means + sample SD + observations','Raincloud: density + quartiles + observations']
    for (filename,fn,is3d),title in zip(functions,names):
        fig=plt.figure(figsize=(7.2,6.2))
        ax=fig.add_subplot(111,projection='3d') if is3d else fig.add_subplot(111)
        fn(ax)
        ax.set_title(title,loc='left',fontweight='bold',pad=16)
        if is3d:
            fig.subplots_adjust(left=.03,right=.97,top=.88,bottom=.08)
        else:
            fig.subplots_adjust(left=.16,right=.95,top=.88,bottom=.16)
        if is3d:
            fig.legend(handles=legend_handles(labels,colours,df[args.group]),
                       loc='lower center',bbox_to_anchor=(.5,.02),ncol=2,frameon=False)
        save_all(fig,figures/filename,args.dpi)
        plt.close(fig)
    fig=plt.figure(figsize=(12.8,12.0))
    fig.suptitle('One dataset, four complementary scientific figures',
                 fontsize=17,fontweight='bold',y=.985)
    fig.legend(handles=legend_handles(labels,colours,df[args.group]),
               loc='upper center',bbox_to_anchor=(.5,.948),ncol=2,
               frameon=False,fontsize=11)
    axes=[fig.add_subplot(2,2,1,projection='3d'),fig.add_subplot(2,2,2),
          fig.add_subplot(2,2,3),fig.add_subplot(2,2,4)]
    for i,((_,fn,_),ax,title) in enumerate(zip(functions,axes,names)):
        fn(ax)
        ax.set_title(f"{'ABCD'[i]}  {title}",fontsize=11.5,loc='left',fontweight='bold',pad=15)
    fig.subplots_adjust(left=.09,right=.975,top=.885,bottom=.075,wspace=.29,hspace=.38)
    save_all(fig,figures/'R01_overview',args.dpi)
    plt.close(fig)
    fig=plt.figure(figsize=(13.5,4.9))
    plot_projections(fig,df,args,labels,colours)
    save_all(fig,figures/'R06_orthogonal_views',args.dpi)
    plt.close(fig)
    config={
        'input': str(args.input.resolve()), 'output': str(args.output.resolve()),
        'group': args.group,'x':args.x,'y':args.y,'z':args.z,'value':args.value,
        'group_order':labels,'colors':colours,'ylim':list(ylim),
        'unit':args.unit,'seed':args.seed,'dpi':args.dpi,
        'snapshot_input':args.snapshot_input,
    }
    (args.output/'analysis_audit.json').write_text(
        json.dumps(audit,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    (args.output/'run_config.json').write_text(
        json.dumps(config,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    for label in labels:
        a=audit['groups'][label]
        print(f"{label}: n={a['n']} mean={a['mean']:.3f} sampleSD={a['sample_sd_ddof1']:.3f} median={a['median']:.3f}")
    print(f'Generated 6 figures × 3 formats in {figures.resolve()}')


if __name__=='__main__':
    main()