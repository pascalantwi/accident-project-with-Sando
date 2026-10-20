# Draft: paper plan

Status: outline only, analysis not started. Last updated 2026-10-20.

## 1. Research question and aim

The paper should answer one question: **where do highway incidents cluster, and where should Road Ranger stations sit so that most incidents are reached within a target response time?**

Working title: *Locating Road Ranger service patrol stations from incident hotspots: a spatial optimisation study of Florida's interstate network.*

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

## 6. Results the paper must show

| # | Exhibit | Type |
| --- | --- | --- |
| T1 | Cleaning log: rows in, rows dropped per step, events out | Table |
| T2 | Descriptive statistics by event type: count, share, median clearance time | Table |
| F1 | Study area: interstates, districts, current Road Ranger stations | Map |
| F2 | Temporal profile: hour × weekday heat map; monthly trend | Chart |
| F3 | Network KDE of incidents, statewide plus zoom on the top corridors | Map |
| F4 | Gi* hotspot and coldspot segments, counts vs AADT rates side by side | Map |
| F5 | Emerging hotspot categories by year | Map |
| T3 | Top 20 hotspot segments: route, county, mile markers, incidents per year, rate | Table |
| F6 | Coverage vs number of stations, for 10 / 15 / 20 minute standards | Chart |
| F7 | Optimised station locations vs current, with coverage areas | Map |
| T4 | Current vs optimised: % incidents covered, mean response time, hold-out results | Table |
| S1 | Sensitivity to segment length, bandwidth and demand weights | Supplementary |

## 7. Paper structure and target journals

Structure (about 7,000 to 8,000 words):

1. Introduction — problem, Road Ranger context, gap, contribution
2. Literature review — the four strands above
3. Data — sources, cleaning, cleaning log (T1)
4. Methods — hotspot detection, location models, validation
5. Results — descriptive, hotspots, siting, validation
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
- [ ] Descriptive statistics (T2, F2)
- [ ] Network hotspots: NKDE, Gi*, rates, emerging hotspots (F3 to F5, T3)
- [ ] Location models: MCLP and p-median, current-layout baseline (F6, F7, T4)
- [ ] Hold-out validation and sensitivity analysis (S1)

Writing
- [ ] Methods and data sections first (they are fixed by the work)
- [ ] Results, then discussion, then introduction and abstract last
- [ ] Format to the target journal, data/code availability statement
- [ ] Internal review by co-author (Sando), then submit
