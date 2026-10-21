# Draft: paper plan

Status: outline only, analysis not started. Last updated 2026-10-20.

## 1. Research question and aim

The paper should answer one question: **where do highway incidents cluster, and where should Road Ranger stations sit so that most incidents are reached within a target response time?**

Working title: *Locating Road Ranger service patrol stations from incident hotspots: a spatial optimisation study of FDOT District 2 (Northeast Florida).*

Objectives:

1. Map where and when incidents concentrate on the network, by type (crash, disabled vehicle, debris).
2. Test whether those clusters are statistically significant and stable across years.
3. Choose station locations that maximise incidents covered within a response-time standard, and compare them with today's patrol coverage.

Why it matters: faster clearance cuts secondary crashes and congestion. A siting method built from incident data gives FDOT districts a repeatable, evidence-based way to place stations.

The contribution must be more than a hotspot map. The publishable part is the step from hotspots to an optimised station plan, with a measured gain over the current layout.

## 2. Literature review

Aim for 40 to 60 references across four strands. The gap to argue: hotspot studies stop at the map, and siting studies rarely use real, network-constrained incident data.

| Strand | What to cover | Foundational works to start from |
| --- | --- | --- |
| Freeway service patrols | Benefits of patrols, clearance time, secondary crashes, cost-benefit of Road Rangers and similar programs | FDOT Road Ranger program evaluations; FHWA Traffic Incident Management reports |
| Crash and incident hotspots | Planar KDE vs network KDE, Getis-Ord Gi*, local Moran's I, space-time clustering | Getis and Ord (1992); Okabe and Sugihara, network spatial analysis; Xie and Yan, network KDE for crashes |
| Facility location for emergency response | Coverage models (MCLP, LSCP), p-median, backup coverage, response-time standards | Church and ReVelle (1974) on MCLP; Toregas et al. (1971) on LSCP; Hakimi on p-median |
| Patrol beat and fleet design | Beat lengths, number of trucks, dynamic patrol allocation | Service-patrol beat optimisation papers in Transportation Research Record |

Search terms: "freeway service patrol" location, "Road Ranger" Florida, "network kernel density" crash, "maximal covering location" emergency, "incident hotspot" interstate.

The works above are named from memory as starting points. Check each citation in Google Scholar before using it.

## 3. Data

`Incidents.csv` is an event chronology log, not an incident list. It has about 9.2 million rows but only about 227,000 unique events. Each row is one update to an event: status, owner, severity, location and so on. The unit of analysis must be the event.

What the raw file holds:

| Variable | Meaning | Use in the paper |
| --- | --- | --- |
| `EVENT_ID` | Incident identifier | Unit of analysis |
| `CREATED_DATE_x` | Update timestamp, Eastern time, mixed -05:00 / -04:00 offsets | Start time, duration, hour, weekday, season |
| `Roadway` | Text such as "Columbia on I-75 Southbound, At MM 430" | County, route, direction, mile marker |
| `Event Type` | Crash, Disabled Vehicle, Debris and others | Which incidents Road Rangers serve |
| `CHRONOTYPE` / `CHRONO_DESC` | Update kind and value, such as ATIS SEVERITY = minor | Severity, status history, clearance time |
| `POINT_LATITUDE` / `POINT_LONGITUDE` | Coordinates in micro-degrees | Location, after dividing by 1,000,000 |
| Surface, weather, lighting codes | Conditions at the event | Covariates and descriptive context |
| `COLUMN1_*`, `lighting.short_name` | 55 to 89% missing | Drop |

Extra datasets the paper needs:

- **Road network**: FDOT Roadway Characteristics Inventory or OpenStreetMap interstates, for snapping incidents and computing drive times.
- **Traffic volume (AADT)**: FDOT traffic counts. Needed to turn counts into rates, so busy roads are not flagged only because they are busy.
- **Current Road Ranger beats and stations**: from FDOT district TIM offices. This is the baseline to beat.
- **Candidate station sites**: interchanges, rest areas, FHP stations and FDOT yards.
- **Boundaries**: county and FDOT district shapefiles.

Open question: who issued the export (FDOT SunGuide?), and does its use need permission or a data citation?

## 4. Data cleaning plan

Every cleaning rule should serve one goal: a trustworthy location and time for each incident a Road Ranger would respond to. Log the rows removed at each step; reviewers will ask for that table. Steps 1 to 9 and 11 are implemented in `preprocess_incidents.py`; step 10 needs the road network first.

| Step | Variable | Rule | Why it matters for siting |
| --- | --- | --- | --- |
| 1 | All | Remove exact duplicates and repeated `EVENT_CHRONO_ID`s | Inflated counts would fake hotspots |
| 2 | `CREATED_DATE_x` | Parse as UTC, convert to America/New_York, drop unparseable values | Correct hour and weekday across daylight saving time |
| 3 | Coordinates | Divide by 1,000,000; keep only points inside Florida (lat 24.3 to 31.1, lon −87.7 to −79.8); drop (0, 0) | Points outside the state are errors |
| 4 | Coordinates per event | Use the latest reported location; flag events whose points move more than 1 km | Operators correct locations; the first point can be wrong |
| 5 | `Roadway` | Parse into county, route (I-75), direction, mile marker; standardise route names | Lets you check coordinates against mile markers and aggregate by corridor |
| 6 | `Event Type` | Harmonise labels; flag the in-scope set (crash, disabled vehicle, debris, abandoned vehicle) | Road Rangers do not respond to every event type |
| 7 | Event level | Collapse to one row per `EVENT_ID`: start time, end time, number of updates, final severity | Unit of analysis is the incident, not the update |
| 8 | Duration | Start to last update; flag durations under 1 minute or over 24 hours | Clearance time is a secondary outcome; outliers are often never-closed records |
| 9 | Conditions | Keep surface, weather and lighting labels; keep Unknown as its own category | Dropping Unknown biases the sample toward well-recorded events |
| 10 | Spatial | Snap each event to the nearest interstate segment; flag snaps over 200 m | Network methods need on-network points |
| 11 | Study window | Report the date range and flag partial years | Partial years skew seasonal and trend results |

Open questions to settle with the data owner: what each `CHRONOTYPE` value means, which status marks clearance, and whether test or training events exist (check `CREATED_BY`).

## 5. Methods

Four stages, each feeding the next:

1. **Describe** — incident counts by type, year, month, weekday and hour; heat table of hour × weekday; clearance-time distributions by type and severity.
2. **Find hotspots on the network**
    - Split interstates into equal segments (e.g. 0.5 mile) and count incidents per segment.
    - Network kernel density (NKDE), not planar KDE: incidents can only happen on the road, and planar KDE bleeds across medians and between parallel roads.
    - Getis-Ord Gi* on segment counts for statistical significance, with false discovery rate correction.
    - Repeat on rates (incidents per million vehicle-miles using AADT) so volume alone does not drive the result.
    - Space-time check: emerging hotspot analysis by year to show whether hotspots are persistent, new or fading.
    - Sensitivity: segment length and bandwidth, reported in a supplementary table.
3. **Site stations**
    - Demand points = segment centroids weighted by incident counts (optionally by severity or peak-hour share).
    - Supply points = candidate sites (interchanges, FDOT yards, rest areas, FHP stations).
    - Network travel times from each candidate to each demand point (OSMnx / networkx with posted speeds; peak-hour speeds if available).
    - Maximal Covering Location Problem: choose p stations to maximise incidents reachable within T minutes (e.g. 10, 15, 20).
    - p-median as a companion model: minimise average response time.
    - Evaluate the current Road Ranger layout under the same model; that is the baseline.
    - Trade-off curve: coverage vs number of stations p.
4. **Validate**
    - Temporal hold-out: fit on earlier years, test coverage on the last year.
    - Compare optimised vs current layout on held-out incidents.
    - Robustness to the response-time standard and to demand weighting.

Tools: Python with pandas, geopandas, osmnx, networkx, spaghetti / esda (PySAL) for network hotspots, PuLP or OR-Tools for the location models. Fix random seeds and publish the code for reproducibility.

## 6. Results

The full manuscript text, with figures and tables in the appendices, is in [`manuscript_draft.md`](manuscript_draft.md).

Sections 6.3.1 to 6.3.5 are drafted from the exploratory analysis (`eda.py`); sections 6.3.6 to 6.3.8 are placeholders for the network hotspot and station-location work. Figures are in `eda/figures/`; the data behind each table is in `eda/tables/`.

### 6.1 Figures

| No. | Caption | File | Status |
| --- | --- | --- | --- |
| Figure 1 | Spatial distribution of Road Ranger incidents in FDOT District 2, 2022–2024. (a) District overview; the dashed box marks panel (b). (b) Central Jacksonville; red circles mark 14 of the 15 busiest 1 km grid cells (the 15th lies on I-75 near Gainesville). Hexagon shading shows incident counts on a logarithmic scale. | `Figure1_spatial_distribution.png` | Done |
| Figure 2 | Mean number of Road Ranger incidents per hour, by hour of day and day of week, 2022–2024. | `Figure2_hour_by_weekday.png` | Done |
| Figure 3 | The 15 one-kilometre grid cells with the highest mean annual number of Road Ranger incidents. Labels give the most frequent location description in each cell; annotations give incidents per year and the share of crashes. | `Figure3_top_hotspot_cells.png` | Done |
| Figure 4 | Event duration (first to last log update) by incident type. Boxes show the interquartile range, whiskers the 5th–95th percentiles; logarithmic scale. Events shorter than 1 min or longer than 24 h are excluded (n = 5,189). | `Figure4_event_duration.png` | Done |
| Figure 5 | Network kernel density and Getis-Ord Gi* hotspots on 0.5-mile segments, counts vs AADT-based rates. | — | Pending network data |
| Figure 6 | Share of incidents covered within 10, 15 and 20 minutes as a function of the number of stations. | — | Pending |
| Figure 7 | Optimised vs current Road Ranger station locations and their coverage areas. | — | Pending station data |
| Figure S1 | Frequency of all recorded event types, 2022–2024. Blue bars mark the four Road Ranger service types analysed. | `FigureS1_event_types.png` | Done |
| Figure S2 | Monthly number of Road Ranger incidents by type, January 2022–December 2024. | `FigureS2_monthly_trend.png` | Done |
| Figure S3 | Hourly distribution of incidents within each type (% of the type's total). | `FigureS3_hourly_profile_by_type.png` | Done |
| Figure S4 | Road Ranger incidents by route and incident type, for the eight routes with the most incidents. | `FigureS4_routes_by_type.png` | Done |
| Figure S5 | Emerging hotspot categories by year. | — | Pending |
| Figure S6 | Sensitivity of hotspots and station solutions to segment length, bandwidth and demand weights. | — | Pending |

### 6.2 Tables

| No. | Title | File | Status |
| --- | --- | --- | --- |
| Table 1 | Data processing summary. | below | Done; per-reason drop counts need `incidents_summary.json` |
| Table 2 | Characteristics of Road Ranger incidents by type, FDOT District 2, 2022–2024. | `Table2_incident_characteristics.csv` | Done |
| Table 3 | Top 20 hotspot segments: route, county, location, incidents per year, rate per AADT, Gi* z-score. | — | Pending network data |
| Table 4 | Current vs optimised station layouts: incidents covered, mean response time, hold-out performance. | — | Pending |
| Table S1 | Completeness and variability of candidate explanatory variables (Road Ranger incidents). | `TableS1_data_quality.csv` | Done |
| Table S2 | The 50 one-kilometre grid cells with the most Road Ranger incidents. | `TableS2_top50_hotspot_cells_1km.csv` | Done |
| Table S3 | Road Ranger incidents by county. | `TableS3_county_counts.csv` | Done |

**Table 1. Data processing summary.**

| Stage | Records | Note |
| --- | ---: | --- |
| Raw chronology records (`Incidents.csv`) | 9,206,764 | One row per update to an event |
| Records retained after cleaning | 9,206,301 | 463 removed: missing ID, invalid timestamp, coordinates outside Florida, duplicates (per-reason counts in `incidents_summary.json`) |
| Unique events | 227,196 | One row per `EVENT_ID`; median 30 updates per event |
| Road Ranger service events (analysis sample) | 173,198 | Disabled vehicle, crash, debris, abandoned vehicle (76.2% of events) |
| Excluded from duration analysis only | 5,189 | Duration < 1 min (1,257) or > 24 h (3,932) |
| Study period and area | 1 Jan 2022 – 31 Dec 2024 | 15 counties, FDOT District 2 |

**Table 2. Characteristics of Road Ranger incidents by type, FDOT District 2, 2022–2024.**

| Incident type | n | % | 2022 | 2023 | 2024 | Median duration, min (IQR) | Weekday % | 15:00–17:59 % | AVL-detected % |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Disabled vehicle | 101,933 | 58.9 | 33,260 | 32,828 | 35,845 | 13.4 (4.9–31.7) | 75.4 | 23.0 | 67.9 |
| Crash | 44,158 | 25.5 | 14,401 | 15,013 | 14,744 | 56.7 (29.9–88.2) | 77.4 | 25.3 | 4.9 |
| Debris on roadway | 16,979 | 9.8 | 5,822 | 5,529 | 5,628 | 12.8 (3.8–28.6) | 78.0 | 22.1 | 36.3 |
| Abandoned vehicle | 10,128 | 5.8 | 3,284 | 3,080 | 3,764 | 4.7 (3.0–9.9) | 75.0 | 12.5 | 86.8 |
| **All** | **173,198** | **100.0** | **56,767** | **56,450** | **59,981** | **18.9 (5.7–45.6)** | **76.2** | **22.9** | **49.8** |

*Duration excludes 5,189 flagged events (Table 1). AVL-detected: event created by the Road Ranger automatic vehicle location subsystem.*

### 6.3 Results text (draft)

#### 6.3.1 Sample characteristics

Between 1 January 2022 and 31 December 2024, the traffic management system recorded 227,196 unique events in FDOT District 2, compiled from 9.2 million chronology updates (Table 1). The four Road Ranger service types made up 173,198 events (76.2%) and form the analysis sample; the rest were traffic-management events such as congestion, scheduled road work and bridge openings (Figure S1). Disabled vehicles were the most frequent incident type (58.9%), followed by crashes (25.5%), debris on the roadway (9.8%) and abandoned vehicles (5.8%) (Table 2). Annual totals varied by less than 7% (56,450–59,981), and no type showed a sustained trend (Figure S2).

*Interpretation.* Demand for Road Ranger service is dominated by non-crash assistance and is stable from year to year. Station locations derived from the pooled 2022–2024 data should therefore represent current demand rather than a transient pattern.

#### 6.3.2 Temporal patterns

Road Ranger incidents were concentrated on weekdays, which accounted for 76.2% of events; the mean daily count was 28% higher on weekdays than at weekends (168.7 vs 131.5 incidents per day). Within the week, incidents peaked between 15:00 and 17:59, reaching a maximum on Fridays from 15:00 to 15:59 (14.7 incidents per hour on average), against about two per hour between 01:00 and 04:59 (Figure 2). Crashes showed a morning peak at 07:00 (5.9% of crashes) and a larger evening peak at 17:00 (9.0%). Debris showed a broad midday plateau. Abandoned vehicles were concentrated at 07:00–08:59 (24.6%) (Figure S3).

*Interpretation.* The weekday peaks match commuter traffic, which suggests exposure, not time of day as such, drives incident frequency. The morning concentration of abandoned vehicles most plausibly reflects when vehicles left overnight are detected on the first patrols, not when they were abandoned. Because demand rises about sevenfold from night to the afternoon peak, the siting analysis should be evaluated separately for peak and off-peak periods.

#### 6.3.3 Spatial distribution and concentration

Incidents were confined to the limited-access network (Figure 1a). Duval County accounted for 53.2% of incidents (Table S3). Five routes, I-75 (26.3%), I-95 (22.3%), I-10 (18.5%), I-295 W (14.4%) and I-295 E (8.8%), together carried 90.3% of incidents (Figure S4). The incident mix differed by corridor: crashes were 34.8% of incidents on I-95 but 8.9% on I-75, where disabled vehicles made up 76.0%.

Demand was spatially concentrated. Of the 983 one-kilometre grid cells with at least one incident, 145 (14.8%) contained half of all incidents, and the 15 busiest cells contained 9.9% (Figure 3; Table S2). Fourteen of these fifteen cells lie in central Jacksonville, in four clusters: the Buckman Bridge on I-295 W, the I-95/I-10 interchange downtown, I-95 at Butler Boulevard, and I-295 E at Butler Boulevard (Figure 1b). The fifteenth lies on I-75 near Gainesville (mile marker 386). Most hotspots fell into one of two types. Interchange cells had crash shares of 40–48% (for example, I-95 at the I-10 ramp, 41%; I-95 at MLK Parkway, 48%). Bridge and rural cells were dominated by disabled vehicles, with crash shares of 6–11% (the Buckman Bridge cells and I-75 near Gainesville). The remaining cells, such as the Buckman Bridge approach at San Jose Boulevard (26%), were mixed.

*Interpretation.* Strong spatial concentration is the precondition for coverage-based siting: a few well-placed stations can serve a large share of demand. The two hotspot types call for different responses. Interchange hotspots need rapid crash clearance to limit secondary crashes. Bridge and rural hotspots need fast vehicle removal where shoulders are absent or response distances are long. These results use a planar 1 km grid and are descriptive; the network-constrained analysis (Section 6.3.6) will test their statistical significance and normalise for traffic volume.

#### 6.3.4 Event duration

The median event duration, measured from the first to the last log update, was 18.9 minutes (IQR 5.7–45.6) (Table 2). Crash events remained open for a median of 56.7 minutes (IQR 29.9–88.2), about four times longer than disabled vehicles (13.4 minutes) and debris (12.8 minutes). Abandoned vehicles had the shortest durations (4.7 minutes) (Figure 4).

*Interpretation.* Longer crash events tie up patrol units for longer, so a crash-dominated hotspot consumes more service capacity than its incident count suggests. Weighting demand by expected service time is a candidate sensitivity analysis for the location models. Duration here measures how long an event stayed open in the log, not on-scene clearance time, and should be reported as such.

#### 6.3.5 Data quality and detection

Half of all incidents (49.8%) were created automatically by the Road Ranger AVL subsystem, ranging from 4.9% of crashes to 86.8% of abandoned vehicles (Table 2). By corridor, the share ranged from 35% on I-95 to 73% on I-75. Several candidate covariates showed almost no variation: 99.9% of incidents were recorded as minor severity, 98.8% occurred on dry pavement and 98.3% in clear weather. Mile markers were missing for 53.0% of incidents (Table S1).

*Interpretation.* The high AVL share means many incidents are detected by patrols themselves, so recorded demand may partly reflect where patrols already operate (detection bias). The hotspot analysis should be repeated without AVL-detected events as a robustness check, and this limitation should be stated explicitly. Severity and weather variables are not informative in this dataset and are excluded from modelling. Locations will be referenced by snapped coordinates, not mile markers.

#### 6.3.6 Network hotspots (pending)

Placeholder for Figure 5, Figure S5 and Table 3: network KDE, Gi* on counts and AADT rates, persistence across years.

#### 6.3.7 Station location (pending)

Placeholder for Figure 6, Figure 7 and Table 4: MCLP and p-median solutions, coverage curve, comparison with current stations.

#### 6.3.8 Validation and sensitivity (pending)

Placeholder for the hold-out results and Figure S6: coverage of 2024 incidents by layouts fitted on 2022–2023, and sensitivity to segment length, bandwidth, response-time standard and demand weights.

## 7. Paper structure and target journals

Structure (about 7,000 to 8,000 words):

1. Introduction — problem, Road Ranger context, gap, contribution
2. Literature review — the four strands above
3. Data — sources, cleaning, data processing summary (Table 1)
4. Methods — hotspot detection, location models, validation
5. Results — sample (Table 2), temporal (Figure 2), spatial (Figures 1 and 3), duration (Figure 4), data quality, then hotspots, siting and validation (Figures 5–7, Tables 3–4); see section 6
6. Discussion — what FDOT should do, limitations (reporting bias, coordinate accuracy, travel-time assumptions, no dispatch data)
7. Conclusion
8. Data and code availability statement

Candidate journals, in rough order of fit:

- Transportation Research Record (TRB; strong fit for Road Ranger/TIM work, also the TRB Annual Meeting route)
- Journal of Transport Geography
- Accident Analysis & Prevention
- Journal of Intelligent Transportation Systems
- Applied Geography
- Socio-Economic Planning Sciences (location-modelling angle)

Check each journal's scope, word limit and open-access fees before choosing.

## 8. Checklist

Data
- [ ] Confirm data source, permission and how to cite it
- [ ] Run `preprocess_incidents.py` on the full file and save the cleaning log
- [ ] Settle open questions on `CHRONOTYPE` values and event types in scope
- [ ] Get the road network, AADT, current Road Ranger stations/beats and candidate sites
- [ ] Snap incidents to the network (cleaning step 10)

Literature
- [ ] Collect and verify 40 to 60 references in a reference manager (Zotero)
- [ ] Write the gap statement in one paragraph

Analysis
- [x] Descriptive statistics (Tables 1–2, Figures 1–4, S1–S4)
- [ ] Network hotspots: NKDE, Gi*, rates, emerging hotspots (Figure 5, Figure S5, Table 3)
- [ ] Location models: MCLP and p-median, current-layout baseline (Figures 6–7, Table 4)
- [ ] Hold-out validation and sensitivity analysis (Figure S6)

Writing
- [ ] Methods and data sections first (they are fixed by the work)
- [ ] Results, then discussion, then introduction and abstract last
- [ ] Format to the target journal, data/code availability statement
- [ ] Internal review by co-author (Sando), then submit
