# EAE supporting source files

[Download the verified source bundle](eae_source_downloads.zip).

The bundle contains the exact EAE resources used in the report and notebook, downloaded on 8 November 2026 UTC. All nine source-file hashes are checked before packaging and verified again inside the ZIP.

| File | Use |
| --- | --- |
| [health-facilities.geojson](raw/health-facilities.geojson) | 4,938 facility locations, ownership, electricity status and prospective load attributes |
| [districts.geojson](raw/districts.geojson) | District boundaries for the point-in-polygon join |
| [population.tif](raw/population.tif) | Population used in the disjoint nearest-facility catchments |
| [distribution-distance.tif](raw/distribution-distance.tif) | Distribution-infrastructure proximity |
| [wealth.tif](raw/wealth.tif) | Relative wealth values used in the assistance score |
| [solar-ghi.tif](raw/solar-ghi.tif) | Solar-resource feasibility evidence |
| [uganda-datasets.json](raw/uganda-datasets.json) | Original sources, dates, cautions, licence text and download endpoints |
| [uganda-geographies.json](raw/uganda-geographies.json) | EAE Uganda geography metadata |
| [selected-categories.json](raw/selected-categories.json) | Native units, domains and index definitions |

[The download manifest](download_manifest.jsonl) gives exact live URLs, UTC retrieval times and SHA-256 hashes. [Source definitions](../docs/sources.json) retain attribution and interpretation.

## Native analysis-export status

After EAE account sign-in, the [native PowerPoint/CSV/TIFF analysis-export package](native_exports/README.md) was downloaded on 9 November 2026 as supplemental evidence. That package was not an input to the original analysis. The source-download ZIP linked above contains EAE **source layers and metadata**.

The report's [district ranking](../outputs/district_ranking.csv), [named facility awards](../outputs/funded_facilities.csv), [district budget](../outputs/district_budget.csv) and [cost sensitivity](../outputs/cost_sensitivity.csv) are independently calculated results. The [website session record](../docs/eae_session.json) documents the separate exploratory Assistance Need Index settings.
