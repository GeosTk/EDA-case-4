"""Create a portable explanatory notebook; optionally execute it end to end."""
from pathlib import Path
import argparse
import json
import os
import sys
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def run(execute=False):
    cells = []

    def md(text): cells.append(nbformat.v4.new_markdown_cell(text))
    def code(text): cells.append(nbformat.v4.new_code_cell(text))

    md('# Uganda healthcare electrification: a fresh EAE analysis\n\n'
       '**Case Study 4 | USD 1,000,000 | 9 November 2026**\n\n'
       'All geospatial inputs were downloaded from the live Energy Access Explorer catalogue and its linked public storage. '
       'No previous local exports, notebook, report or generated tables are analytical inputs. '
       'The assignment and lecture supplied the brief only. The Ministry of Health project announcement is the sole external cost comparator.\n\n'
       'The decision is how to combine concentrated unserved healthcare need with support for more expensive remote facilities. '
       'The four-page report is in `report/case_study_4_report.pdf`. This notebook exposes the reproducible calculations and their limits.')
    md('## 1. Sources and environment\n\n'
       'Install `requirements.txt`, start Jupyter from the repository, and run all cells. The pipeline modules contain the complete implementation; '
       'the notebook executes them and shows the saved evidence. Network access is required only to refresh downloads or install dependencies. '
       'The saved analysis is reproducible offline. UTC retrieval dates, URLs and SHA-256 hashes are retained in the manifest.')
    code("from pathlib import Path\nimport sys, json\nimport pandas as pd\nfrom IPython.display import display, Image\nROOT = Path.cwd().resolve()\nif not (ROOT/'config.json').exists():\n    ROOT = ROOT.parent\nassert (ROOT/'config.json').exists(), 'Run from the repository or notebooks directory'\nsys.path.insert(0, str(ROOT))\nmanifest = pd.read_json(ROOT/'data/download_manifest.jsonl', lines=True)\ndisplay(manifest[['file','retrieved_utc','bytes','sha256']])\nconfig = json.loads((ROOT/'config.json').read_text())\ndisplay(config)")
    md('## 2. Re-run the complete spatial analysis\n\n'
       'The source inventory has 4,938 facilities. Match them geometrically to 2024 districts. Keep government HC II/HC III records with '
       'both electricity fields equal to `No`, excluding ERT-flagged sites. All other records remain in the audit. '
       'The older electricity-status data require field verification before awards. Off-grid is not equivalent to unelectrified.\n\n'
       'Population is allocated to the nearest facility among **all** facilities, including private and electrified alternatives. '
       'Cells are counted once; co-located facilities share the assigned population. Distances are measured from 1 km cell centres in EPSG:3857 '
       'at radii of 3, 5 and 10 km. This approximates geographic access, not patient choice or walking time. The categorical `Catch_pop` values are not summed as unique people.')
    code("from src.analyse import run\nsummary = run()\ndisplay(pd.Series(summary, name='Result'))\ndisplay(pd.read_json(ROOT/'outputs/catchment_audit.json', typ='series'))")
    md('## 3. Eligibility and missing data\n\n'
       'A candidate\'s missing raster attributes are median-imputed for scoring and explicitly marked in `imputed_fields`. '
       'The current funded set contains no imputed records. Near-line distances are screening indicators from coarse rasters; '
       'zero does not establish a connection or reliable supply. Solar GHI is a feasibility input, rather than a reward for easier sites.')
    code("audit = pd.read_csv(ROOT/'outputs/facility_audit.csv')\neligible = pd.read_csv(ROOT/'outputs/eligible_facilities.csv')\ndisplay(audit.groupby(['ELECTRIFIC','LEVEL']).size().unstack(fill_value=0))\ndisplay(eligible[eligible.imputed_fields.notna()][['id','FACILITY_N','district','imputed_fields']])\nprint('Eligible facilities:',len(eligible),'Districts:',eligible.district.nunique())")
    md('## 4. Priority score and district ranking\n\n'
       '**Score = 0.45 population + 0.25 clinical energy + 0.20 infrastructure gap + 0.10 poverty.** '
       'Population and energy use log(1+x) scaling anchored to the candidate 95th percentile. '
       'Infrastructure gap = line distance/10 km; poverty = (2-RWI)/4. Components are clipped to [0,1]. '
       'District totals sum eligible facility scores, favouring a larger stock of unserved service locations. '
       'This is a transparent extension from EAE layers, **not EAE\'s native district Assistance Need Index**. '
       'The website session and its exploratory native settings are documented in `docs/eae_session.json`.')
    code("ranking = pd.read_csv(ROOT/'outputs/district_ranking.csv')\ndisplay(ranking.head(15).round(3))\nfrom src.make_figures import run as make_figures\nmake_figures()\ndisplay(Image(filename=str(ROOT/'outputs/figures/national_priorities.png')))")
    md('## 5. Budget and named conditional awards\n\n'
       'Official cost comparator: the Ministry\'s 2025 HFSE announcement reports USD 5 million for 250 facilities (USD 20,000 average). '
       'Assume critical-service packages of USD 20,000 for HC II and USD 40,000 for HC III, with a 25% uplift beyond 5 km from distribution. '
       'These are planning assumptions, not tender prices or full-facility energy guarantees.\n\n'
       'Reserve one facility in each top-five district, commit at least USD 240,000 of the installation ceiling to remote sites nationally, '
       'then fill by score within the top five and finally elsewhere if necessary. Cap each district at ten facilities. '
       'Maintenance and audit reserves remain protected. The report discusses the two large HC III full-load profiles separately.')
    code("funded = pd.read_csv(ROOT/'outputs/funded_facilities.csv')\ndisplay(pd.read_csv(ROOT/'outputs/budget.csv'))\ndisplay(pd.read_csv(ROOT/'outputs/district_budget.csv').round(2))\ndisplay(funded[['id','FACILITY_N','LEVEL','district','daily_kwh','line_km','installation_usd','catchment_5km']].round(2))\nassert len(funded)==32 and funded.id.is_unique\nassert funded.imputed_fields.isna().all()\nassert pd.read_csv(ROOT/'outputs/budget.csv').usd.sum()==1_000_000")
    md('## 6. Cost, preference and catchment sensitivity\n\n'
       'Cost scenarios re-run awards rather than changing the unit price of a fixed list. '
       'Weight scenarios test the stability of district priorities. The catchment-radius comparison keeps the selected facilities fixed. '
       'A value-first comparison removes the remote reservation while retaining the top-five seed, geographic cap and budget rules; '
       'it is a heuristic comparison, not a globally optimal health-benefit frontier.')
    code("display(pd.read_csv(ROOT/'outputs/cost_sensitivity.csv'))\ndisplay(pd.read_csv(ROOT/'outputs/weight_sensitivity.csv'))\ndisplay(Image(filename=str(ROOT/'outputs/figures/cost_sensitivity.png')))\ndisplay(pd.DataFrame({'radius_km':[3,5,10], 'modelled_people':[summary['modelled_people_3km'],summary['modelled_people_5km'],summary['modelled_people_10km']]}).round())\nprint('Equity plan:',summary['funded_facilities'],'sites;',round(summary['modelled_people_5km']),'modelled residents;',summary['remote_facilities_funded'],'remote sites')\nprint('Value-first plan:',summary['value_first_facilities'],'sites;',round(summary['value_first_modelled_people']),'modelled residents;',summary['value_first_remote_facilities'],'remote sites')")
    md('## 7. Evidence limits and sources\n\n'
       'Population estimates are potential beneficiaries of improved power at their assigned facility, not verified patients, households electrified, '
       'or avoided deaths. Historical status, mixed data vintages, unmeasured outages, road access, equipment and staffing can change recommendations. '
       'Before procurement, reconcile named sites against current MoH and donor projects, verify loads and reliability, obtain connection offers and bids, '
       'and agree maintenance responsibilities.\n\n'
       '- [Energy Access Explorer](https://www.energyaccessexplorer.org/) and public layer metadata in `data/raw/uganda-datasets.json`.\n'
       '- [EAE: Data and Methods (Mentis et al. 2019)](https://www.wri.org/research/energy-access-explorer-data-and-methods).\n'
       '- [Uganda healthcare demand method (Sinclair-Lecaros et al. 2023)](https://www.wri.org/research/gis-assessment-electricity-health-care-uganda).\n'
       '- [Official MoH HFSE cost comparator, 31 July 2025](https://health.go.ug/ministry-of-health-to-solarize-250-health-facilities-under-the-health-facility-solar-electrification-hfse-project/).\n\n'
       'Original data-owner citations and licences are preserved in the EAE catalogue. `docs/sources.json` records attribution and cost interpretation.')
    nb = nbformat.v4.new_notebook(cells=cells, metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}})
    if execute:
        work = ROOT/'tmp/notebook'
        spec = work/'kernels/eae_case4'
        spec.mkdir(parents=True, exist_ok=True)
        (spec/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-X','utf8','-m','ipykernel_launcher','-f','{connection_file}'], 'display_name':'EAE Case 4','language':'python'}))
        os.environ['JUPYTER_PATH'] = str(work)
        os.environ['JUPYTER_RUNTIME_DIR'] = str(work/'runtime')
        os.environ['IPYTHONDIR'] = str(work/'ipython')
        os.environ['MPLCONFIGDIR'] = str(work/'matplotlib')
        NotebookClient(nb, timeout=180, kernel_name='eae_case4', resources={'metadata':{'path':str(ROOT)}}).execute()
    nbformat.validate(nb)
    target = ROOT/'notebooks/healthcare_electrification.ipynb'
    target.parent.mkdir(exist_ok=True)
    nbformat.write(nb,target)
    print(f'Wrote {target}; executed={execute}; code cells={sum(c.cell_type=="code" for c in nb.cells)}')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--execute',action='store_true')
    run(parser.parse_args().execute)
