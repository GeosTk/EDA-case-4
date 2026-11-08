"""Build the four-page submission and matching readable Markdown from outputs."""
from pathlib import Path
import json
import html
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs'
REPORT = ROOT/'report'


def run():
    REPORT.mkdir(exist_ok=True)
    summary = json.loads((OUT/'summary.json').read_text())
    assert summary['top_five'] == ['Kasese','Rukungiri','Tororo','Bugiri','Isingiro'], 'Updated data require report narrative review'
    assert summary['funded_facilities'] == 32 and summary['installation_usd'] == 790000, 'Updated policy requires report narrative review'
    ranked = pd.read_csv(OUT/'district_ranking.csv')
    funding = pd.read_csv(OUT/'district_budget.csv')
    costs = pd.read_csv(OUT/'cost_sensitivity.csv')
    navy, teal, grey = colors.HexColor('#143e52'), colors.HexColor('#237d81'), colors.HexColor('#52626c')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCustom', fontName='Helvetica-Bold', fontSize=22, leading=25, textColor=navy, spaceAfter=9))
    styles.add(ParagraphStyle(name='Deck', fontName='Helvetica', fontSize=11, leading=15, textColor=grey, spaceAfter=13))
    styles.add(ParagraphStyle(name='BodyCustom', fontName='Helvetica', fontSize=9.1, leading=12.3, spaceAfter=7, textColor=colors.HexColor('#24363f')))
    styles.add(ParagraphStyle(name='HeadingCustom', fontName='Helvetica-Bold', fontSize=11.5, leading=14, spaceBefore=9, spaceAfter=6, textColor=teal))
    styles.add(ParagraphStyle(name='SmallCustom', fontName='Helvetica', fontSize=7.7, leading=10.1, spaceAfter=5, textColor=grey))
    styles.add(ParagraphStyle(name='CellCustom', fontName='Helvetica', fontSize=8.0, leading=10.3))
    styles.add(ParagraphStyle(name='HeaderCell', fontName='Helvetica-Bold', fontSize=8.0, leading=10.3, textColor=colors.white))
    story, markdown = [], []

    def text(value, style='BodyCustom'):
        story.append(Paragraph(value, styles[style]))
        markdown.append(value.replace('<b>','**').replace('</b>','**').replace('<br/>','\n'))

    def heading(value):
        text(value, 'HeadingCustom')
        markdown[-1] = '## '+markdown[-1]

    def table(headers, rows, widths):
        content = [[Paragraph(html.escape(str(v)), styles['HeaderCell']) for v in headers]]
        content += [[Paragraph(html.escape(str(v)), styles['CellCustom']) for v in row] for row in rows]
        t = Table(content, colWidths=widths, repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),navy),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#eef4f5'),colors.white]),
            ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
            ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
            ('LINEBELOW',(0,-1),(-1,-1),.4,colors.HexColor('#b8cbd1'))]))
        story.append(t); story.append(Spacer(1,7))
        markdown.extend(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,row))+' |' for row in rows])

    def page():
        story.append(PageBreak()); markdown.append('\n---\n')

    text('Powering primary care in Uganda', 'TitleCustom')
    text('A USD 1 million healthcare electrification plan<br/>Case Study 4 | 9 November 2026 | Fresh EAE data', 'Deck')
    heading('1. Decision and health rationale')
    text('Fund <b>32 conditional critical-service upgrades</b> across eight districts. Prioritise Kasese, Rukungiri, Tororo, Bugiri and Isingiro, while reserving installation funds for remote facilities elsewhere. The plan allocates <b>USD 790,000 to installations, USD 50,000 to verification/design, USD 100,000 to five-year maintenance and USD 60,000 to contingency</b>. These are proposed awards, subject to current site and funding checks.')
    text('Electricity enables lighting, vaccine refrigeration, diagnostics, communication and water services. Interruptions can disrupt treatment and cold chains. The Ministry must balance the concentration of unserved facilities, people potentially served, clinical energy requirements and the higher delivery costs of remote locations. Electricity is one input: staffing, equipment and medicines also constrain outcomes. [3,4]')
    heading('2. EAE evidence, filters and index choice')
    text('All geospatial inputs were downloaded afresh from the live EAE catalogue and its linked public storage on 8 November 2026 (UTC). The inventory contains <b>4,938 facilities</b>: 582 recorded without electricity and 130 with unavailable status. Retain government HC II/HC III facilities with both electricity fields equal to "No"; exclude two ERT-flagged records and retain <b>527 candidates in 104 districts</b>. Match points to the 146 EAE district polygons. These are historical records, not a 2026 field census. [1]')
    table(['EAE layer / vintage','Purpose and decision choice'], [
        ['Health facilities / 2023','Public HC II/III, no electricity; use prospective daily kWh, not observed consumption.'],
        ['WorldPop / 2022','Allocate people to the nearest of ALL facilities, within 5 km; avoid overlap.'],
        ['Distribution / 2024','Greater distance indicates assistance need; retain remote sites, with no maximum-distance exclusion.'],
        ['Relative wealth / 2021','Lower RWI raises public-support priority; it is a relative asset proxy, not household income.'],
        ['Solar GHI / 2024','Check PV feasibility; annual averages do not determine seasonal battery adequacy.'],
    ], [133,378])
    text('EAE website exploration used <b>Assistance Need Index</b>, district output, and importance 5/5/4/4/1 for health/population/distribution/wealth/GHI, with health proximity 0-5 km. The packaged export required login. Native area rankings can include already served urban facilities; marker visibility is not proof of a raster status filter. The final funding ranking therefore uses the auditable, facility-specific extension below, computed from the downloaded EAE data. It is <b>not labelled as EAE\'s native district ANI</b>. [1,2]')

    page()
    heading('3. Reproducible healthcare priority ranking')
    text('<b>Facility score = 0.45P + 0.25E + 0.20D + 0.10W.</b> P is log(1 + allocated population), divided by log(1 + the candidate 95th percentile, 17,583.6 people). E applies the same transform to prospective daily energy, capped at the 95th percentile of 26.67 kWh/day. D is line distance/10 km; W = (2 - RWI)/4. Clip all components to [0,1]. Population and clinical services receive 70% together; infrastructure gaps receive 20%; wealth adds an equity signal. These weights are explicit policy choices.')
    text('Rank districts by the <b>sum of eligible facility scores</b>, representing the stock of candidate interventions. This favours districts with more unserved facilities; it is not a per-capita need rate. Ten candidates need median imputation for missing raster attributes; no funded facility does. Do not treat narrow score differences as precise clinical priorities.')
    top = ranked.head(10)
    table(['Rank','District','Eligible sites','Priority sum','Modelled people','Median line km'], [
        [int(r['rank']),r['district'],int(r['unserved_candidates']),f"{r['priority_sum']:.2f}",f"{r['catchment_people']:,.0f}",f"{r['median_line_km']:.0f}"] for _,r in top.iterrows()
    ], [36,95,72,82,130,96])
    descriptions = {
        'Kasese':'leads with 29 candidates and about 235,569 modelled catchment residents; its larger unserved service footprint dominates the district score.',
        'Rukungiri':'has 26 candidates and about 124,786 modelled residents; low wealth and numerous unserved facilities support priority even near distribution infrastructure.',
        'Tororo':'combines 22 candidates with about 204,765 modelled residents and comparatively strong GHI, supporting the concentration of prospective demand.',
        'Bugiri':'has 19 candidates and about 183,932 modelled residents; high modelled catchment demand drives priority despite short line-proximity values.',
        'Isingiro':'has 17 candidates, about 147,191 modelled residents and the lowest mean RWI of the top five; it also includes a more distant candidate.'}
    for name in summary['top_five']:
        text('<b>'+name+'</b> '+descriptions[name])
    text('A recorded distance of 0 km means the same coarse grid vicinity, not a verified connection. Near-line facilities can still be unelectrified because of connection charges, last-mile works or missing equipment; the data do not establish which barrier applies. EAE reports prospective energy demand, not patient volumes or avoided mortality.', 'SmallCustom')
    story.append(Image(str(OUT/'figures/national_priorities.png'), width=511, height=184))
    markdown.append('![National priority map and ranking](../outputs/figures/national_priorities.png)')

    page()
    heading('4. Budget, facility selection and people potentially reached')
    text('The official Ministry HFSE announcement reports USD 5 million for 250 facilities: a <b>USD 20,000 programme-average comparator</b>. Its detailed scope and unit prices are unavailable. Assume USD 20,000 per HC II critical-service system, USD 40,000 per HC III, and a 25% logistics uplift where line proximity exceeds 5 km. The HC III premium and remote uplift are analyst assumptions, not quoted prices. [4]')
    text('Reserve one candidate in each top-five district; allocate at least USD 240,000 (30% of the USD 800,000 installation ceiling) to remote candidates nationally. Then fill by descending facility score within the top five, followed by remaining districts if funds permit. Cap each district at ten facilities. This transparent heuristic is not a mathematical health-outcome optimum. Remote reservation adds Agago, Kassanda and Kyenjojo to the main five.')
    table(['District','Facilities','Installation USD','Modelled people','USD/person*'], [
        [r.district,int(r.facilities),f'{r.installation_usd:,.0f}',f'{r.modelled_people:,.0f}',f'{r.installation_usd_per_modelled_person:.2f}'] for r in funding.itertuples()
    ], [104,66,119,125,97])
    table(['Funding item','USD'], [
        ['Installed critical-service systems (27 HC II, 5 HC III)','790,000'],
        ['Verification, design and duplicate-funding checks','50,000'],
        ['Five-year maintenance reserve','100,000'],
        ['Contingency and unused installation balance','60,000'],
        ['TOTAL','1,000,000'],
    ], [382,129])
    text('*Installation cost per modelled catchment resident; audit, maintenance and contingency are excluded from district unit ratios. Seven remote facilities receive USD 250,000. Maintenance averages USD 625 per funded facility per year for five years; bids must validate this allowance and identify battery-replacement funding.')
    heading('Population estimate and technical scope')
    text(f'The funded locations have <b>{summary["modelled_people_5km"]:,.0f} modelled potential beneficiaries</b>, equivalent to USD {summary["full_budget_usd_per_modelled_person"]:.2f} per person using the entire budget. Assign each positive WorldPop cell inside Uganda to its nearest facility among all 4,938 records, within 5 km of its centre; co-located facilities share their assigned population. This produces disjoint modelled populations. The source Catch_pop field repeats service-level planning standards, so it is not summed as unique people.')
    text('These residents are not verified patients or newly connected households. Service choice, terrain, referrals and new facilities can change the estimate. Fund <b>critical circuits</b>, with clinical staff defining protected loads. Two selected HC IIIs have prospective full-facility demand above 130 kWh/day; their planning packages cannot be assumed to meet full demand. Require site-specific load measurements, seasonal PV/storage design and priced bids before approving their scope.')

    page()
    heading('5. Sensitivity and the equity/value trade-off')
    text('Re-run the same selection rules at changed installation prices, retaining USD 50,000 for audits, USD 100,000 for maintenance and at least USD 50,000 contingency. Lower prices expand the programme; higher prices reduce awards. Contingency remains protected in these scenarios rather than automatically financing inflation.')
    table(['Price change','Facilities','Installation USD','Modelled people','Contingency USD'], [
        [f'{int(r.cost_change_pct):+d}%',int(r.facilities),f'{r.installation_usd:,.0f}',f'{r.modelled_people:,.0f}',f'{r.contingency_usd:,.0f}'] for r in costs.itertuples()
    ], [81,67,116,121,126])
    text('Population-heavy weights (65/15/10/10) and equity-heavy weights (25/15/40/20) retain the same top five districts. This demonstrates stability to these tested preferences, not all possible choices. Changing the catchment radius from 5 km to 3 or 10 km changes the baseline funded sites\' potential population from 323,772 to 246,627 or 348,521; this is a catchment sensitivity, without re-optimising site selection.')
    text('Under the same budget and district-cap rules, prioritising people per dollar and dropping the remote reserve funds <b>40 sites and 475,246 modelled residents, with no remote sites</b>. The recommended plan funds 32 sites and 323,772 residents, including seven remote sites. Agago costs USD 6.57 per modelled resident in installation spending, versus Kasese USD 1.72. The equity plan accepts that difference to reach remote service locations; cost per resident is not cost per health outcome.')
    heading('6. Limits and Ministry next steps')
    text('<b>Validate eligibility first:</b> the health layer is dated 2023; new connections and the HFSE programme can make its status obsolete. Reconcile named sites and unique IDs with district teams, ERT and current donor awards. Missing-status facilities and unreliable on-grid/off-grid facilities were not ranked as unserved; survey them separately. The five selected HC IIIs need particular scrutiny of load scope and costs.')
    text('<b>Validate benefit and supply:</b> 1 km rasters and straight-line catchments do not represent walking times or service-specific access. Population (2022), wealth (2021), boundaries and network data (2024) have different vintages. Distribution data include some under-construction segments, so proximity can overstate current supply. Annual GHI at funded sites ranges about 1,517-2,192 kWh/m2; test seasonal yield, shading, network capacity and outage history. Require competitive quotes, maintenance responsibilities and commissioning tests before releasing installation funds. Monitor power-related service interruptions and repair response; do not infer deaths averted from this screening model.')
    heading('Sources and reproducibility')
    text('[1] EAE Uganda live catalogue and linked storage: MoH/WRI health (2023), UBOS districts (2024), WorldPop population (2022), Meta RWI (2021), ESGWG distribution (2024), WBG/ESMAP/Solargis GHI. Accessed 8 Nov 2026 UTC. Exact URLs, metadata, licences, timestamps and SHA-256 hashes: data/download_manifest.jsonl and docs/sources.json. All calculations: src/analyse.py; full 104-district ranking and named awards: outputs/.', 'SmallCustom')
    text('[2] Mentis et al. 2019. <a href="https://www.wri.org/research/energy-access-explorer-data-and-methods" color="#237d81">Energy Access Explorer: Data and Methods</a>. [3] Sinclair-Lecaros et al. 2023. <a href="https://www.wri.org/research/gis-assessment-electricity-health-care-uganda" color="#237d81">A GIS-Based Demand Assessment Methodology ... Uganda</a>. These explain the EAE framework and prospective demand approach; final weights and award rules are analyst choices.', 'SmallCustom')
    text('[4] Uganda Ministry of Health, 31 Jul 2025. <a href="https://health.go.ug/ministry-of-health-to-solarize-250-health-facilities-under-the-health-facility-solar-electrification-hfse-project/" color="#237d81">Health Facility Solar Electrification project announcement</a>. USD 5 million / 250 facilities supplies the cost comparator. An announcement is not completion evidence. This is the sole external quantitative source beyond EAE; no earlier local analysis or exports were used.', 'SmallCustom')

    def decorate(canvas, doc):
        canvas.saveState(); w,h=A4
        canvas.setStrokeColor(colors.HexColor('#c6d9dd')); canvas.setLineWidth(.6)
        canvas.line(42,h-29,w-42,h-29)
        canvas.setFont('Helvetica',7.2); canvas.setFillColor(grey)
        canvas.drawString(42,h-22,'UGANDA HEALTHCARE ELECTRIFICATION | DECISION BRIEF')
        canvas.drawString(42,23,'Fresh EAE data | Conditional planning scenario | 9 November 2026')
        canvas.drawRightString(w-42,23,str(doc.page)); canvas.restoreState()

    doc=SimpleDocTemplate(str(REPORT/'case_study_4_report.pdf'),pagesize=A4,
        leftMargin=42,rightMargin=42,topMargin=42,bottomMargin=39,
        title='Powering primary care in Uganda - Case Study 4',author='EDA-case-4')
    doc.build(story,onFirstPage=decorate,onLaterPages=decorate)
    (REPORT/'case_study_4_report.md').write_text('\n\n'.join(markdown)+'\n',encoding='utf-8')


if __name__ == '__main__':
    run()
