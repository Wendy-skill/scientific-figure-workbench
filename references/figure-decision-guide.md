# Choose a figure by question, not novelty

| Scientific question | Recommended plot | Conditions / caution |
|---|---|---|
| How do the *distributions* of numeric responses differ across independent groups? | Raw points + boxplot; violin + points; raincloud | KDE needs enough spread/observations; the smoothed outline is not raw observations. Show sample size. |
| How do group *means* compare? | Mean and raw points with clearly labelled SD or CI; bar + points only if zero baseline is defensible | SD describes scatter, CI uncertainty of estimated mean, SEM not a substitute for SD. |
| How does a variable change across time / wind speed / spatial row? | Line plot + individual curves or uncertainty band | Respect pairing, repeated measures, and chronological order. |
| Which numerical features co-vary? | 2D scatter + optional small multiples; 3D scatter **with** orthogonal views | Axes not automatically comparable when measures/units differ. Avoid conclusions about predictive performance. |
| How does an outcome depend on two numerical inputs? | Colour-coded 2D scatter, contour only when interpolation/model is justified | Never interpolate sparse measurements without flagging the interpolation. |
| Are categories part of a composition? | Stacked bars with known denominators | Avoid 3D pie charts and truncated proportional axes. |
| Is this computational-field data (CFD)? | Mesh-aware scalar maps, contour plots, streamlines | State field normalization, colour range, sample plane, mesh/resolution, and avoid misleading interpolation. |

## Mandatory science checks

- What precisely is one row? Experimental run, sample, particle trajectory, sensor reading, or repeated measure?
- Does the numeric column have actual, documented units? If unknown, use bare feature label.
- Are there missing/invalid records? If yes, never hide or silently exclude them.
- Are displayed points raw values? Do not confuse categorical jitter with altered measurements.
- Is the intended comparison within matched samples? Use a paired display if so.
- Are bins, KDE bandwidth, smoothing, uncertainty and normalization documented?
- Is the figure intended for a paper or mobile social post? Check final *effective* type size and horizontal label crowding.
- Use the same limits for panels displaying the same quantitative feature and orientation. Different variables/units do **not** need common numerical limits.
- On mean bar charts, show a non-truncated zero baseline when meaningful, and ensure SD error bars are not clipped.

## Parameter guidance

- Do not prescribe `bw_method=0.4` just because group n < 30. For very small or zero-variance groups, use points + summaries instead of KDE.
- Do not prescribe scatter alpha=0.15 solely because n > 2000. Determine size, alpha, rasterisation policy and overplotting from final figure size and actual density.
- SVG text editability depends on backend/fonts. Matplotlib `svg.fonttype='none'` preserves text objects; missing fonts or downstream editor may change appearance. PDF is not inherently fully editable.
- If an axis has limits `0–30`, values and uncertainty must fit within them; otherwise expand limits or explicitly explain exclusion, never silently clip.