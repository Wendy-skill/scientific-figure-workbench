---
name: scientific-figure-workbench
description: Plan, produce, audit, and refine publication-quality scientific figures from real CSV or tabular research data. Use for experimental data, CFD results, distributions, multi-panel figures, violin/raincloud plots, scatterplots, bar-plus-raw-points, journal figures, and reproducible Python/SVG/PDF exports. Enforce data integrity and valid statistical interpretation before aesthetic refinement.
---

# Scientific Figure Workbench

Produce **scientifically defensible, publication-ready, editable and reproducible** figures. Use the user's scientific question to determine the graphic, not visual trends or fashionable chart types. This is a standalone skill: it does **not** require `scientific-figure-master` or `scientific-visualization` to be installed.

## Workflow (follow in order)

1. **Inspect inputs and question.** Identify observational unit, all candidate variables, units **explicitly provided by source**, class/group definitions, sample sizes, dependencies/repeated measures, and intended comparison. Read the original file and relevant paper/caption if available. Never infer units or independence from a column name.
2. **Audit before plotting.** Inspect total rows, per-group sample counts, null/invalid values, duplicates, extrema, numerical dtypes, and whether data are raw or already aggregated. Do not silently drop rows, remove outliers, interpolate, smooth raw coordinates, invent uncertainty, or transform values. For missing/invalid required data, stop and surface the issue, or agree a documented rule with the user. Distinguish source measurement from rendering jitter (only the display x-position may be jittered).
3. **Select the visual encoding.** Read `references/figure-decision-guide.md`. Prefer direct raw-point plots for small groups; line/scatter for paired and ordered changes; violin/raincloud only when density estimation is defensible. A bar alone hides distribution. 3D static scatters can obscure overlap: add 2D projections. **Four-panel mode is a demonstration, not a default for every dataset.**
4. **State a drawing contract** in the work log or concise message: intended claim, grouping, independent vs repeated design, chosen plot(s), axis limits and whether shared, palette, source units (or 'not provided'), reported variability (SD, SEM, CI, etc.), expected deliverables. Never add p-values, regression fits, prediction performance or causal/clinical claims without appropriate analysis and explicit user consent.
5. **Render reproducibly.** Use `scripts/plot_figures.py` for the supported four-panel showcase, or adapt it for other plot forms. Prefer clean axes, readable dimensions at final placement size, restrained colours with shape redundancy, external ticks, careful legends and group counts. Output individual panels and a composite if requested. Preserve point coordinates: jitter is on *categorical* positions only, never on the measured axis. KDE is a modelled density, not raw data or evidence of latent subgroups; choose bandwidth based on data and show points.
6. **Check validity and legibility.** Independently recompute group sizes, mean, sample SD (ddof=1), median, quartiles, min/max, all displayed error bars, and the source file checksum. Verify there are no clipped extrema, empty legends, swapped labels, misleading baseline, illegible mobile ticks, SVG rasterisation or unsupported interpretations. See `references/quality-checklist.md`.
7. **Run independent acceptance tests.** After rendering, call `python scripts/verify_output.py --input /path/to/plot_source.csv --output /path/to/figure_output` to re-read the CSV and verify the checksum, group statistics, shared limits, PNG resolution, output completeness and SVG text. If checks fail, diagnose rather than delivering.
8. **Revise without corrupting science.** When asked to improve aesthetics, preserve numeric data, group membership, descriptive statistics, axis mapping, and uncertainty definition. Any statistical/axis change requires explicit explanation.
9. **Deliver and explain.** Give PNG (300 DPI), SVG (editable vector components; editable text where supported), PDF, source Python, documented inputs/dependencies and `analysis_audit.json`. Say clearly when data are insufficient, panel was omitted or a file failed to export.

## Fast use: transparent synthetic demonstration

From this skill folder, run these commands. This demonstration uses generated **synthetic teaching data**, not actual research measurements, and must never be described as experimental evidence. The default theme is graphite grey + soft violet.

```bash
python -m pip install -r requirements.txt
python scripts/make_synthetic_demo.py --output examples/demo_experiment.csv --n 180
python scripts/plot_figures.py \
  --input examples/demo_experiment.csv --output examples/figure_output \
  --group 'Group' --x 'Feature X1' --y 'Feature X2' \
  --z 'Feature X3' --value 'Response Y' \
  --group-order Control,Treatment --ylim 0,50
python scripts/verify_output.py \
  --input examples/demo_experiment.csv --output examples/figure_output
```

These demo columns have **no physical units**. Group values overlap: do not make causal or inferential claims from the illustrative plots.

## For any real CSV

```bash
python scripts/plot_figures.py --input /path/to/my.csv --output ./figure_output \
  --group Treatment --x feature_1 --y feature_2 --z feature_3 \
  --value response --group-order 'Control,Treated' --unit 'unit if known'
```

If three numeric variables, per-row observations or adequate KDE sample sizes are absent, **do not force the four-panel script**. Use a suitable plot family based on the data, and document the decision. If data are repeated measures, do not treat measurements as independent just because they form separate CSV rows.

## Output and finish criteria

`figures/` contains an overview, four individual figures, and an orthogonal 2D-projections figure, each in PNG/SVG/PDF. The output folder also contains an analysis audit and run configuration, optionally a byte-for-byte source CSV snapshot (only with `--snapshot-input`). If any rule fails, report it clearly rather than marking the run complete. Call `python scripts/plot_figures.py --help` to view all options.