from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs'
FIG = OUT/'figures'


def run():
    FIG.mkdir(exist_ok=True)
    ranking = pd.read_csv(OUT/'district_ranking.csv')
    funded = pd.read_csv(OUT/'funded_facilities.csv')
    sensitivity = pd.read_csv(OUT/'cost_sensitivity.csv')
    boundaries = json.loads((ROOT/'data/raw/districts.geojson').read_text())['features']
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'savefig.dpi': 180, 'font.family': 'DejaVu Sans'})
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.1), gridspec_kw={'width_ratios':[1,1.2]})
    scores = dict(zip(ranking.district, ranking.priority_sum))
    patches, values = [], []
    for f in boundaries:
        g = f['geometry']
        polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
        for poly in polys:
            patches.append(Polygon(np.asarray(poly[0]), closed=True))
            values.append(scores.get(f['properties']['district'], 0))
    coll = PatchCollection(patches, cmap='YlGnBu', edgecolor='#a0b2ba', linewidth=.25)
    coll.set_array(np.asarray(values)); axes[0].add_collection(coll); axes[0].autoscale_view()
    axes[0].scatter(funded.longitude, funded.latitude, c='#c8592c', s=12, edgecolors='white', linewidths=.3, zorder=3)
    axes[0].set_aspect('equal'); axes[0].set_axis_off(); axes[0].set_title('National screening and funded candidates', fontsize=11)
    fig.colorbar(coll, ax=axes[0], shrink=.65, label='Sum of facility priority scores')
    top = ranking.head(10).iloc[::-1]
    axes[1].barh(top.district, top.priority_sum, color=['#72a7ae']*5+['#174b63']*5)
    axes[1].set_xlabel('District assistance priority (sum of facility scores)')
    axes[1].set_title('Top ten districts', fontsize=11)
    for i, row in enumerate(top.itertuples()):
        axes[1].text(row.priority_sum+.15, i, f'{row.unserved_candidates} sites', va='center', fontsize=8)
    axes[1].set_xlim(0, top.priority_sum.max()+4)
    fig.tight_layout(); fig.savefig(FIG/'national_priorities.png', bbox_inches='tight'); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.4))
    axes[0].bar(sensitivity.cost_change_pct.astype(str)+'%', sensitivity.facilities, color='#174b63')
    axes[0].set(xlabel='Change in installation prices', ylabel='Conditional facilities funded')
    for i, n in enumerate(sensitivity.facilities): axes[0].text(i, n+.4, str(n), ha='center')
    axes[0].set_ylim(0, 48)
    axes[1].bar(sensitivity.cost_change_pct.astype(str)+'%', sensitivity.modelled_people/1000, color='#c8592c')
    axes[1].set(xlabel='Change in installation prices', ylabel='Modelled potential beneficiaries (thousands)')
    fig.tight_layout(); fig.savefig(FIG/'cost_sensitivity.png', bbox_inches='tight'); plt.close(fig)


if __name__ == '__main__':
    run()
