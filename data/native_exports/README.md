# Native EAE analysis exports

These files were downloaded through the signed-in Energy Access Explorer website on **9 November 2026**, using the recorded Uganda district Assistance Need Index settings. The original EAE ZIP and its four extracted members are preserved byte for byte.

## Download

- [Original EAE export ZIP](assistance_need/202611091724-eae-export.zip)
- [Native summary presentation](assistance_need/eae-summary.pptx) - 15 slides, including the selected layers, filters, weights, four index summaries and top districts.
- [Native Assistance Need Index GeoTIFF](assistance_need/eae-assistance-need-index-map.tif)
- [Native district priority CSV](assistance_need/eae-assistance-need-index-high-priority-areas.csv) - 146 districts.
- [Native population and area-share CSV](assistance_need/eae-population-area-share.csv) - summaries for assistance need, energy access potential, demand and supply.
- [Export settings and checksums](manifest.json)
- [Screenshot of the exported analysis](assistance_need/eae_native_ani_view.png)

## Settings recorded in the native presentation

| Layer | Selected range | Importance |
| --- | --- | --- |
| Population Count | 0-20,000 people | 5 |
| Relative Wealth Index | -2 to 2 RWI | 4 |
| Health facilities | 0-5 km proximity | 5 |
| Global Horizontal Irradiation | 500-2,800 kWh/m2 | 1 |
| Distribution Lines | 0-700 km proximity | 4 |

Geography: Uganda. Analysis area: District. Selected index: Assistance Need Index. On-grid, off-grid and unavailable-status health markers were hidden in the interface; marker visibility must not be interpreted as a proven filter on the index raster or district aggregates.

## Relationship to the submitted analysis

This is supplemental native EAE evidence collected **after** the original report and notebook were completed. Their model uses the earlier, freshly downloaded EAE source layers and applies explicit public-facility, electricity-status, programme-flag, catchment and funding rules. The native district ANI and the report's facility-based district priority score answer different questions.

The native ANI top five are **Wakiso, Kampala, Amudat, Buvuma and Kasese**. The report's eligible-facility priorities are **Kasese, Rukungiri, Tororo, Bugiri and Isingiro**. Use each ranking with its documented method; these export files do not reproduce the report's funding ranking by themselves. The native CSV contains general healthcare facility counts, rather than the report's screened public unserved HC II/HC III candidates.

## Native-file cautions

- Slides 6-7 label every unit as "proximity in km", including population, wealth and GHI. The native CSV column headers and EAE layer metadata give their intended units. This presentation-label issue is preserved in the original file.
- The native area-share rows sum to 127,413 selected square-kilometre units, while the native TIFF has 127,414 valid cells. The selected ANI population plus the outside population sums to 46,050,200, compared with the interface's displayed 46,050,198. These small source differences are recorded without altering the original files; their causes are not verified.
- TIFF values run from 0 to 254; NoData is 255. They are raw exported index values, not probabilities or verified electricity-access percentages.
- Data-source vintages and reuse terms remain in the source metadata. Generating a new export does not update the underlying facility observations.

Run `python src/verify_native_exports.py` to check ZIP/member integrity, district coverage, native slide settings, raster metadata and embedded-service-token absence.
