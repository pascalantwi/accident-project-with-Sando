# Manuscript draft

**Locating Road Ranger service patrol stations from incident hotspots: a spatial optimisation study of FDOT District 2, Northeast Florida**

Pascal Antwi¹, [Co-author] Sando²

¹ [Affiliation] · ² [Affiliation]
Corresponding author: [name, email]

*Draft of 21 October 2026. Sections 4.6–4.8 and the parts of the Abstract, Discussion and Conclusion that depend on them are placeholders, marked [pending]. All figures and tables are in the appendices: [Appendix A](#appendix-a-figures) (figures), [Appendix B](#appendix-b-tables) (tables) and [Appendix C](#appendix-c-supplementary-material) (supplementary material).*

---

## Abstract

Freeway service patrols such as Florida's Road Rangers reduce incident clearance times and secondary crashes, but where they are based is rarely derived from incident data. This study uses three years (2022–2024) of traffic management records from Florida Department of Transportation (FDOT) District 2 to identify where Road Ranger incidents concentrate and to propose station locations that maximise timely coverage. The records, comprising 9.2 million chronology updates, were reconstructed into 227,196 unique events, of which 173,198 were Road Ranger service incidents: disabled vehicles (58.9%), crashes (25.5%), debris (9.8%) and abandoned vehicles (5.8%). Demand was stable across years and strongly concentrated in space and time. Five interstate corridors carried 90.3% of incidents, half of all incidents fell within 14.8% of occupied 1 km grid cells, and 14 of the 15 busiest cells lay in central Jacksonville. Incidents peaked on weekday afternoons between 15:00 and 17:59. Crash events remained open about four times longer than other incident types (median 56.7 vs 13.4 minutes for disabled vehicles), and crash-dominated interchange hotspots were distinct from bridge and rural hotspots dominated by disabled vehicles. [pending: network hotspot results; optimal station locations; coverage gain over the current layout.] The findings provide an evidence base for siting service patrol stations and highlight detection bias from patrol-generated records as a methodological concern for incident-based planning.

**Keywords:** freeway service patrol; Road Rangers; traffic incident management; hotspot analysis; maximal covering location problem; Florida

---

## 1. Introduction

Traffic incidents such as crashes, disabled vehicles and debris are a leading cause of non-recurrent congestion on freeways, and each minute an incident remains on the roadway raises the risk of a secondary crash [REF: secondary crash risk and incident duration]. Freeway service patrols shorten detection, response and clearance times by keeping roving units on the network [REF: FHWA Traffic Incident Management handbook]. In Florida, the Road Ranger program provides this service free of charge on limited-access highways in every FDOT district [REF: FDOT Road Ranger program description; benefit–cost evaluation].

Patrol effectiveness depends on where units are based and how far they must travel to reach an incident. Station and staging locations, however, are typically set by operational convenience and historical practice rather than by systematic analysis of where incidents occur. Incident records from traffic management centres now allow demand to be mapped at fine spatial and temporal resolution, but they are rarely linked to formal facility-location methods.

This study addresses that gap for FDOT District 2 in Northeast Florida. It has three objectives: (i) to characterise the temporal and spatial distribution of Road Ranger incidents; (ii) to identify statistically significant incident hotspots on the road network; and (iii) to determine station locations that maximise the share of incidents reachable within a response-time standard and compare them with the current layout. The contribution is a reproducible workflow that moves from raw incident chronology logs to an optimised station plan, together with an assessment of how patrol-generated records may bias incident-based planning.

## 2. Literature review

[To be written. Four strands, 40–60 references; see `draft.md` §2.]

1. **Freeway service patrols.** Effects on clearance time and secondary crashes; benefit–cost evaluations of Road Rangers and comparable programmes [REF].
2. **Crash and incident hotspot detection.** Planar versus network kernel density estimation (Xie and Yan, 2008; Okabe et al., 2009); local spatial statistics (Getis and Ord, 1992; Ord and Getis, 1995).
3. **Facility location for emergency response.** Set covering (Toregas et al., 1971), maximal covering (Church and ReVelle, 1974) and p-median (Hakimi, 1964) models.
4. **Patrol beat and fleet design.** Beat length, fleet size and dynamic allocation of service patrols [REF].

*Gap to argue:* hotspot studies typically stop at the map, and location studies rarely use network-constrained, real-world incident demand.

## 3. Data and methods

### 3.1 Study area and data

The study area is FDOT District 2, covering 15 counties of Northeast Florida, including Jacksonville (Duval County), Gainesville (Alachua County) and Lake City (Columbia County). Incident data were obtained from the regional traffic management system as an event chronology export (`Incidents.csv`, 2.7 GB) covering 1 January 2022 to 31 December 2024 [REF: data source and permission]. Each record is one update to an event (e.g., status, ownership, severity or location change) and carries the event identifier, timestamp, event type, roadway description, coordinates and recorded road surface, weather and lighting conditions.

Supplementary datasets for the network analysis are the road network from OpenStreetMap (Boeing, 2017), annual average daily traffic (AADT) from the FDOT Transportation Data and Analytics Office, county boundaries from US Census TIGER/Line files, and current Road Ranger station and beat locations from FDOT District 2 [pending].

### 3.2 Data processing

Records were cleaned in chunks and reconstructed into one row per event. Exact duplicates and repeated chronology identifiers were removed. Timestamps, recorded with mixed UTC offsets of −05:00 and −04:00, were parsed in UTC and converted to US Eastern time so that hour and weekday are correct across daylight-saving transitions. Coordinates, stored as integer micro-degrees, were rescaled, and records falling outside Florida's bounding box were removed. Four attributes with more than 50% missing values were dropped.

Each event took its type and conditions from its first record and its location from its latest record, because operators correct locations as an event unfolds. Roadway descriptions were parsed into county, route, direction and mile marker. Event duration was defined as the time between the first and last log update. Durations under 1 minute or over 24 hours were flagged and excluded from duration analyses only. The analysis sample comprises the four event types served by Road Rangers: disabled vehicle, crash, debris on roadway and abandoned vehicle. The processing stages and record counts are summarised in [Table 1](#table-1).

### 3.3 Exploratory analysis

Incidents were aggregated by month, weekday and hour to describe temporal patterns. Spatial concentration was assessed on a 1 km × 1 km grid in a local equal-distance projection. For each occupied cell, the mean annual number of incidents, the share of crashes and the modal location description were recorded, and cells were ranked by incident count. Spatial density was visualised with hexagonal binning on a logarithmic scale. This grid-based analysis is descriptive and planar; network-constrained inference follows in Section 3.4.

### 3.4 Network hotspot detection [pending]

Incidents will be snapped to the limited-access network and aggregated to 0.5-mile segments. Network kernel density estimation (Okabe et al., 2009) will map continuous intensity along the network, and the Getis-Ord Gi* statistic (Getis and Ord, 1992) will identify statistically significant hot and cold segments, with false discovery rate correction (Benjamini and Hochberg, 1995). The analysis will be repeated on incident rates per million vehicle-miles travelled using AADT, and year by year to assess persistence.

### 3.5 Station location models [pending]

Station sites will be selected with the maximal covering location problem (MCLP; Church and ReVelle, 1974). Let *I* be the set of demand segments with weights *aᵢ* (incidents per year), *J* the set of candidate sites, *tᵢⱼ* the network travel time from site *j* to segment *i*, *T* the response-time standard and *p* the number of stations:

$$
\max \sum_{i \in I} a_i y_i \quad \text{s.t.} \quad \sum_{j \in N_i} x_j \ge y_i \;\; \forall i \in I, \qquad \sum_{j \in J} x_j = p, \qquad x_j, y_i \in \{0, 1\},
$$

where *Nᵢ* = {*j* ∈ *J* : *tᵢⱼ* ≤ *T*}. The p-median model (Hakimi, 1964) will be solved as a companion to minimise demand-weighted mean travel time. The current Road Ranger layout will be evaluated under both models as the baseline.

### 3.6 Validation and sensitivity [pending]

Layouts will be fitted on 2022–2023 incidents and evaluated on 2024 incidents. Sensitivity will be tested for segment length, kernel bandwidth, response-time standard (*T* = 10, 15 and 20 minutes), demand weighting (counts, crash-weighted, duration-weighted), and exclusion of patrol-detected (AVL) incidents.

## 4. Results

### 4.1 Sample characteristics

Between 1 January 2022 and 31 December 2024, the traffic management system recorded 227,196 unique events in District 2, reconstructed from 9,206,764 chronology records ([Table 1](#table-1)). The four Road Ranger service types made up 173,198 events (76.2%) and form the analysis sample. The remaining events were traffic-management notices such as congestion (22,053), scheduled road work (12,658) and bridge openings (4,392) ([Figure S1](#figure-s1)). Disabled vehicles were the most frequent incident type (58.9%), followed by crashes (25.5%), debris on the roadway (9.8%) and abandoned vehicles (5.8%) ([Table 2](#table-2)). Annual totals varied by less than 7% (56,450 in 2023 to 59,981 in 2024), and no incident type showed a sustained trend over the 36 months ([Figure S2](#figure-s2)).

**Interpretation.** Road Ranger demand in District 2 is dominated by non-crash assistance: disabled vehicles alone outnumber crashes by more than two to one ([Table 2](#table-2)). Service planning based on crash data alone would therefore miss most of the patrol workload. The year-to-year stability seen in [Figure S2](#figure-s2) indicates that pooling 2022–2024 yields a representative demand surface for the location models (Section 3.5), rather than one shaped by a transient surge.

### 4.2 Temporal patterns

Weekdays accounted for 76.2% of incidents ([Table 2](#table-2)), and the mean daily count was 28% higher on weekdays than at weekends (168.7 vs 131.5 incidents per day). Incidents peaked between 15:00 and 17:59 from Monday to Friday, with a maximum on Friday from 15:00 to 15:59 (14.7 incidents per hour on average), against about two per hour between 01:00 and 04:59 ([Figure 2](#figure-2)). The hourly profiles differed by type ([Figure S3](#figure-s3)). Crashes had a morning peak at 07:00 (5.9% of crashes) and a larger evening peak at 17:00 (9.0%). Debris showed a broad midday plateau from 09:00 to 16:00, and abandoned vehicles were concentrated between 07:00 and 08:59 (24.6%).

**Interpretation.** The weekday afternoon peak in [Figure 2](#figure-2) coincides with commuter traffic, consistent with exposure (vehicle-miles travelled) rather than time of day per se driving incident occurrence. The sevenfold difference between overnight and peak demand suggests that station requirements should be assessed separately for peak and off-peak periods. The morning concentration of abandoned vehicles in [Figure S3](#figure-s3) most plausibly reflects when vehicles left overnight are found on the first patrols, rather than when they were abandoned; it should not be read as an occurrence pattern.

### 4.3 Spatial distribution and concentration

Road Ranger incidents were confined to the limited-access network and concentrated around Jacksonville ([Figure 1a](#figure-1)). Duval County accounted for 53.2% of incidents, followed by Alachua (12.8%) and Columbia (10.6%) ([Table S3](#table-s3)). Five routes, I-75 (26.3%), I-95 (22.3%), I-10 (18.5%), I-295 W (14.4%) and I-295 E (8.8%), carried 90.3% of incidents ([Figure S4](#figure-s4)). The incident mix differed by corridor: crashes made up 34.8% of incidents on I-95 but 8.9% on I-75, where disabled vehicles accounted for 76.0% ([Figure S4](#figure-s4)).

Demand was strongly concentrated. Of the 983 occupied 1 km grid cells, 145 (14.8%) contained half of all incidents. The 15 busiest cells contained 9.9% ([Figure 3](#figure-3)) and the 50 busiest 24.2% ([Table S2](#table-s2)). Fourteen of the 15 busiest cells lie in central Jacksonville and form four clusters: the Buckman Bridge on I-295 W, the I-95/I-10 interchange downtown, I-95 at Butler Boulevard and I-295 E at Butler Boulevard ([Figure 1b](#figure-1)). The fifteenth lies on I-75 near Gainesville (mile marker 386). Most leading cells fell into one of two types ([Figure 3](#figure-3)). Interchange cells had crash shares of 40–48%, for example I-95 at the I-10 ramp (41.0%) and I-95 at MLK Parkway (48.3%). Bridge and rural cells were dominated by disabled vehicles, with crash shares of 6–11%: the three Buckman Bridge cells and I-75 near Gainesville. Further down the ranking, several interchange cells exceeded 55% crashes, among them I-95 at 8th Street (60.1%), I-295 W at Blanding Boulevard (58.2%) and I-95 at Airport Road (58.2%) ([Table S2](#table-s2)).

**Interpretation.** The concentration shown in [Figure 3](#figure-3) and [Table S2](#table-s2) is the precondition for coverage-based siting: a few well-placed stations can reach a large share of demand. [Figure 1b](#figure-1) shows that the busiest cells form a small number of contiguous clusters rather than isolated points, which suggests that each cluster is a single candidate service zone. The two hotspot types call for different responses. Crash-dominated interchange hotspots need rapid clearance to limit secondary crashes and queueing. Bridge and rural hotspots, where shoulders are limited or response distances long, need fast vehicle removal. The corridor differences in [Figure S4](#figure-s4) point the same way: I-75 demand is mostly disabled vehicles on long rural sections, whereas I-95 through Jacksonville carries the highest crash load. These results are planar and descriptive; Section 4.6 tests their statistical significance on the network and adjusts for traffic volume.

### 4.4 Event duration

The median event duration was 18.9 minutes (IQR 5.7–45.6) ([Table 2](#table-2)). Crash events remained open for a median of 56.7 minutes (IQR 29.9–88.2), about four times longer than disabled vehicles (13.4 minutes) and debris (12.8 minutes). Abandoned vehicles had the shortest durations (4.7 minutes) ([Figure 4](#figure-4)). The 5,189 events (3.0%) flagged as shorter than 1 minute or longer than 24 hours were excluded ([Table 1](#table-1)).

**Interpretation.** Because crash events occupy patrol units about four times longer ([Figure 4](#figure-4)), a crash-dominated hotspot consumes more service capacity than its incident count alone implies. This supports weighting demand by expected service time as a sensitivity case in the location models (Section 3.6). Duration here is measured from log updates and reflects how long an event remained open in the system, not on-scene clearance time; it is therefore an upper-bound proxy for patrol occupancy.

### 4.5 Data quality and detection

Half of all incidents (49.8%) were created automatically by the Road Ranger automatic vehicle location (AVL) subsystem ([Table S1](#table-s1)). The share ranged from 4.9% of crashes to 86.8% of abandoned vehicles ([Table 2](#table-2)), and from 35% on I-95 to 73% on I-75. Several candidate covariates showed almost no variation: 99.9% of incidents were recorded as minor severity, 98.8% occurred on dry pavement and 98.3% in clear weather. Mile markers were missing for 53.0% of incidents ([Table S1](#table-s1)).

**Interpretation.** The AVL shares in [Table 2](#table-2) imply that many non-crash incidents are discovered by patrols themselves. Recorded demand may therefore partly reflect where patrols already operate, a detection bias that could reinforce existing deployment if left uncorrected. The near-absence of crashes among AVL records suggests that crash detection relies on other channels (e.g., 911 and law enforcement), so crash locations are less affected by this bias. The hotspot and location analyses will be repeated without AVL-detected incidents (Section 3.6). The near-constant severity and weather variables in [Table S1](#table-s1) are uninformative in this dataset and are excluded from modelling, and locations are referenced by coordinates rather than by mile markers.

### 4.6 Network hotspots [pending]

[Figure 5, Figure S5 and Table 3: network KDE and Gi* hotspots on counts and AADT-based rates; persistence across years.]

### 4.7 Optimal station locations [pending]

[Figure 6, Figure 7 and Table 4: coverage curve by number of stations; MCLP and p-median solutions; comparison with the current Road Ranger layout.]

### 4.8 Validation and sensitivity [pending]

[Hold-out coverage of 2024 incidents; Figure S6: sensitivity to segment length, bandwidth, response-time standard, demand weights and exclusion of AVL-detected incidents.]

## 5. Discussion

### 5.1 Implications for station siting

The exploratory results establish three conditions that favour data-driven siting. Demand is stable from year to year (Section 4.1), concentrated in a few clusters (Section 4.3), and strongly time-dependent (Section 4.2). Central Jacksonville, which contains 14 of the 15 busiest cells, is the obvious focus for station capacity, while the I-75 corridor near Gainesville is the leading rural candidate. The distinction between crash-dominated interchange hotspots and assistance-dominated bridge and rural hotspots suggests that station siting and unit specification (e.g., heavy towing capability) should be planned together. [pending: discussion of optimised layouts and coverage gains.]

### 5.2 Limitations

First, the data cover one FDOT district, and results may not transfer to districts with different network structure or patrol coverage. Second, half of the incidents were detected by patrols, so recorded demand may be biased toward currently patrolled segments (Section 4.5). Third, event duration is a log-based proxy, not measured clearance time. Fourth, the grid-based concentration measures are planar and do not adjust for traffic volume; the network and rate-based analyses (Sections 3.4 and 4.6) address this. Fifth, the records do not include dispatch or arrival times, so response times will be modelled from network travel times rather than observed.

### 5.3 Future work

[pending: dynamic, time-of-day station or staging plans; integration with dispatch data; extension to other districts.]

## 6. Conclusion

Three years of traffic management records show that Road Ranger demand in FDOT District 2 is dominated by disabled vehicles, stable over time, peaked on weekday afternoons and concentrated in a small number of clusters, most of them in central Jacksonville. Crash-dominated interchange hotspots and assistance-dominated bridge and rural hotspots differ in the service they require. [pending: optimised station locations and expected coverage gain.]

## Declarations

- **Data availability.** Incident data were provided by [FDOT District 2 / data owner] and are not publicly available. Processed event-level data are available from the authors on reasonable request, subject to the data owner's permission.
- **Code availability.** Processing and analysis code: [repository URL or DOI on publication].
- **Author contributions (CRediT).** [pending]
- **Funding.** [pending]
- **Competing interests.** [pending]

## References

*Verify every entry before submission; [REF] markers in the text still need sources.*

- Benjamini, Y., Hochberg, Y., 1995. Controlling the false discovery rate: a practical and powerful approach to multiple testing. *Journal of the Royal Statistical Society: Series B* 57(1), 289–300.
- Boeing, G., 2017. OSMnx: new methods for acquiring, constructing, analyzing, and visualizing complex street networks. *Computers, Environment and Urban Systems* 65, 126–139.
- Church, R., ReVelle, C., 1974. The maximal covering location problem. *Papers of the Regional Science Association* 32, 101–118.
- Getis, A., Ord, J.K., 1992. The analysis of spatial association by use of distance statistics. *Geographical Analysis* 24(3), 189–206.
- Hakimi, S.L., 1964. Optimum locations of switching centers and the absolute centers and medians of a graph. *Operations Research* 12(3), 450–459.
- Okabe, A., Satoh, T., Sugihara, K., 2009. A kernel density estimation method for networks, its computational method and a GIS-based tool. *International Journal of Geographical Information Science* 23(1), 7–32.
- Ord, J.K., Getis, A., 1995. Local spatial autocorrelation statistics: distributional issues and an application. *Geographical Analysis* 27(4), 286–306.
- Toregas, C., Swain, R., ReVelle, C., Bergman, L., 1971. The location of emergency service facilities. *Operations Research* 19(6), 1363–1373.
- Xie, Z., Yan, J., 2008. Kernel density estimation of traffic accidents in a network space. *Computers, Environment and Urban Systems* 32(5), 396–406.

---

## Appendix A. Figures

<a id="figure-1"></a>**Figure 1.** Spatial distribution of Road Ranger incidents in FDOT District 2, 2022–2024. (a) District overview; the dashed box marks panel (b). (b) Central Jacksonville; red circles mark 14 of the 15 busiest 1 km grid cells (the 15th lies on I-75 near Gainesville). Hexagon shading shows incident counts on a logarithmic scale.

![Figure 1](eda/figures/Figure1_spatial_distribution.png)

<a id="figure-2"></a>**Figure 2.** Mean number of Road Ranger incidents per hour, by hour of day and day of week, 2022–2024.

![Figure 2](eda/figures/Figure2_hour_by_weekday.png)

<a id="figure-3"></a>**Figure 3.** The 15 one-kilometre grid cells with the highest mean annual number of Road Ranger incidents. Labels give the most frequent location description in each cell; annotations give incidents per year and the share of crashes. Rows 3 and 4 are adjacent cells on the Buckman Bridge.

![Figure 3](eda/figures/Figure3_top_hotspot_cells.png)

<a id="figure-4"></a>**Figure 4.** Event duration (first to last log update) by incident type. Boxes show the interquartile range, the vertical line the median and whiskers the 5th–95th percentiles; logarithmic scale. Events shorter than 1 minute or longer than 24 hours are excluded (n = 5,189).

![Figure 4](eda/figures/Figure4_event_duration.png)

**Figure 5.** [pending] Network kernel density and Getis-Ord Gi* hotspots on 0.5-mile segments: counts and AADT-based rates.

**Figure 6.** [pending] Share of incidents covered within 10, 15 and 20 minutes by number of stations.

**Figure 7.** [pending] Optimised and current Road Ranger station locations with coverage areas.

## Appendix B. Tables

<a id="table-1"></a>**Table 1.** Data processing summary.

| Stage | Records | Note |
| --- | ---: | --- |
| Raw chronology records (`Incidents.csv`) | 9,206,764 | One row per update to an event |
| Records retained after cleaning | 9,206,301 | 463 removed: missing identifier, invalid timestamp, coordinates outside Florida, duplicates [per-reason counts pending] |
| Unique events | 227,196 | One row per event; median 30 updates per event |
| Road Ranger service incidents (analysis sample) | 173,198 | Disabled vehicle, crash, debris, abandoned vehicle (76.2% of events) |
| Excluded from duration analysis only | 5,189 | Duration < 1 min (1,257) or > 24 h (3,932) |
| Study period and area | 1 Jan 2022 – 31 Dec 2024 | 15 counties, FDOT District 2 |

<a id="table-2"></a>**Table 2.** Characteristics of Road Ranger incidents by type, FDOT District 2, 2022–2024.

| Incident type | n | % | 2022 | 2023 | 2024 | Median duration, min (IQR) | Weekday % | 15:00–17:59 % | AVL-detected % |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Disabled vehicle | 101,933 | 58.9 | 33,260 | 32,828 | 35,845 | 13.4 (4.9–31.7) | 75.4 | 23.0 | 67.9 |
| Crash | 44,158 | 25.5 | 14,401 | 15,013 | 14,744 | 56.7 (29.9–88.2) | 77.4 | 25.3 | 4.9 |
| Debris on roadway | 16,979 | 9.8 | 5,822 | 5,529 | 5,628 | 12.8 (3.8–28.6) | 78.0 | 22.1 | 36.3 |
| Abandoned vehicle | 10,128 | 5.8 | 3,284 | 3,080 | 3,764 | 4.7 (3.0–9.9) | 75.0 | 12.5 | 86.8 |
| **All** | **173,198** | **100.0** | **56,767** | **56,450** | **59,981** | **18.9 (5.7–45.6)** | **76.2** | **22.9** | **49.8** |

*Note:* Duration excludes 5,189 flagged events ([Table 1](#table-1)). AVL-detected: event created by the Road Ranger automatic vehicle location subsystem. IQR: interquartile range.

**Table 3.** [pending] Top 20 hotspot segments: route, county, location, incidents per year, rate per AADT, Gi* z-score.

**Table 4.** [pending] Current and optimised station layouts: incidents covered, mean response time, hold-out performance.

## Appendix C. Supplementary material

<a id="figure-s1"></a>**Figure S1.** Frequency of all recorded event types, 2022–2024. Blue bars mark the four Road Ranger service types analysed; grey bars are traffic-management events excluded from the analysis.

![Figure S1](eda/figures/FigureS1_event_types.png)

<a id="figure-s2"></a>**Figure S2.** Monthly number of Road Ranger incidents by type, January 2022 – December 2024.

![Figure S2](eda/figures/FigureS2_monthly_trend.png)

<a id="figure-s3"></a>**Figure S3.** Hourly distribution of incidents within each type, as a percentage of the type's total.

![Figure S3](eda/figures/FigureS3_hourly_profile_by_type.png)

<a id="figure-s4"></a>**Figure S4.** Road Ranger incidents by route and incident type for the eight routes with the most incidents, 2022–2024.

![Figure S4](eda/figures/FigureS4_routes_by_type.png)

**Figure S5.** [pending] Emerging hotspot categories by year.

**Figure S6.** [pending] Sensitivity of hotspots and station solutions to segment length, bandwidth, response-time standard and demand weights.

<a id="table-s1"></a>**Table S1.** Completeness and variability of candidate explanatory variables (Road Ranger incidents, n = 173,198).

| Indicator | Share of incidents (%) |
| --- | ---: |
| Severity recorded as "minor" | 99.9 |
| Road surface "Dry" | 98.8 |
| Weather "Clear" | 98.3 |
| Lighting code 16 (code meaning undocumented) | 91.7 |
| Mile marker missing | 53.0 |
| Created by Road Ranger AVL subsystem | 49.8 |
| Duration > 24 h (flagged) | 2.3 |
| Duration < 1 min (flagged) | 0.7 |
| County not parsed from roadway text | < 0.1 |

<a id="table-s2"></a>**Table S2.** The 50 one-kilometre grid cells with the most Road Ranger incidents, 2022–2024. Together they contain 24.2% of incidents. Coordinates are cell centroids (WGS84).

| Rank | Location (most frequent description) | Route | Incidents per year | Crash share (%) | Latitude | Longitude |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | Duval on I-295 W, Before between Buckman Bridge/San Jose Blvd | I-295 W | 530.7 | 26.1 | 30.1834 | -81.6331 |
| 2 | Duval on I-95, Ramp To I-10 | I-95 | 479.7 | 41.0 | 30.3211 | -81.6838 |
| 3 | Duval on I-295 W, At Buckman Bridge | I-295 W | 429.3 | 10.6 | 30.1923 | -81.6665 |
| 4 | Duval on I-295 W, At Buckman Bridge | I-295 W | 408.3 | 8.9 | 30.1878 | -81.6665 |
| 5 | Duval on I-95, At Butler Blvd/SR-202 | I-95 | 393.3 | 40.3 | 30.2486 | -81.5930 |
| 6 | Duval on I-10, At Stockton St | I-10 | 375.7 | 43.3 | 30.3211 | -81.6951 |
| 7 | Duval on I-95, At MLK Pkwy/20th St Expressway | I-95 | 366.3 | 48.3 | 30.3568 | -81.6680 |
| 8 | Duval on I-295 W, At West End of Buckman Bridge | I-295 W | 351.0 | 6.3 | 30.1913 | -81.6869 |
| 9 | Duval on I-295 W, Ramp To US-17/Roosevelt Blvd | I-295 W | 350.0 | 45.0 | 30.1923 | -81.7054 |
| 10 | Duval on I-95, Beyond Church St | I-95 | 349.7 | 44.2 | 30.3301 | -81.6755 |
| 11 | Duval on I-95, At South End of Fuller Warren Bridge | I-95 | 339.3 | 25.0 | 30.3143 | -81.6648 |
| 12 | Duval on I-295 E, At Butler Blvd | I-295 E | 336.7 | 43.8 | 30.2548 | -81.5169 |
| 13 | Duval on I-95, At Emerson St | I-95 | 336.0 | 46.3 | 30.2918 | -81.6315 |
| 14 | Duval on I-95, Before between MM 349/MM 350 | I-95 | 330.3 | 36.0 | 30.3134 | -81.6535 |
| 15 | Alachua on I-75, Beyond MM 386 | I-75 | 313.0 | 6.2 | 29.6482 | -82.4093 |
| 16 | Alachua on I-75, Before Rest Area (MM 381) | I-75 | 310.7 | 7.0 | 29.5902 | -82.3627 |
| 17 | Duval on I-295 W, Before between Buckman Bridge/US-17 | I-295 W | 298.0 | 18.3 | 30.1915 | -81.6954 |
| 18 | Duval on I-95, At 8th St | I-95 | 289.7 | 60.1 | 30.3470 | -81.6685 |
| 19 | Duval on I-295 E, At South End of Dames Point Bridge | I-295 E | 287.7 | 24.1 | 30.3645 | -81.5528 |
| 20 | Duval on I-295 W, Ramp To Normandy Blvd/SR-228 | I-295 W | 287.0 | 32.6 | 30.2935 | -81.7714 |
| 21 | Columbia on I-75, At I-10 | I-75 | 279.7 | 13.9 | 30.2662 | -82.7540 |
| 22 | Duval on I-95, At Bowden Rd | I-95 | 262.3 | 56.8 | 30.2668 | -81.6103 |
| 23 | Duval on I-10, At McDuff Ave | I-10 | 261.7 | 55.9 | 30.3209 | -81.7051 |
| 24 | Alachua on I-75, At MM 378 | I-75 | 260.7 | 7.0 | 29.5495 | -82.3377 |
| 25 | Duval on I-295 W, At I-10 | I-295 W | 255.7 | 38.3 | 30.3136 | -81.7698 |
| 26 | Duval on I-95, At Airport Rd/Duval Rd | I-95 | 241.7 | 58.2 | 30.4818 | -81.6438 |
| 27 | Duval on I-295 E, At Dames Point Bridge | I-295 E | 237.7 | 14.0 | 30.3798 | -81.5543 |
| 28 | Duval on I-295 W, Ramp From Old St Augustine Rd | I-295 W | 237.3 | 37.4 | 30.1688 | -81.6018 |
| 29 | Duval on I-95, At Fuller Warren Bridge | I-95 | 236.7 | 15.5 | 30.3151 | -81.6711 |
| 30 | Columbia on I-75, At Rest Area (MM 411) | I-75 | 230.7 | 10.8 | 29.9772 | -82.5782 |
| 31 | Alachua on I-75, Ramp From CR-234 | I-75 | 230.7 | 17.8 | 29.4986 | -82.2953 |
| 32 | Duval on I-95, At I-295S | I-295 E | 229.3 | 26.5 | 30.1659 | -81.5512 |
| 33 | Duval on I-295 W, At SR-21/Blanding Blvd | I-295 W | 229.0 | 58.2 | 30.1954 | -81.7385 |
| 34 | Duval on I-10, At Lenox Ave | I-10 | 228.3 | 45.7 | 30.3207 | -81.7172 |
| 35 | Duval on I-10, At Cassat Ave | I-10 | 228.0 | 52.0 | 30.3180 | -81.7286 |
| 36 | Alachua on I-75, At MM 392 | I-75 | 220.3 | 7.4 | 29.7153 | -82.4655 |
| 37 | Duval on I-95, Ramp To Union St | I-95 | 219.3 | 56.4 | 30.3375 | -81.6687 |
| 38 | Alachua on I-75, At US-441 | I-75 | 217.7 | 21.0 | 29.8028 | -82.5138 |
| 39 | St. Johns on I-95, At Rest Area (MM 331) | I-95 | 216.7 | 24.2 | 30.0942 | -81.4984 |
| 40 | Alachua on I-75, At MM 393 | I-75 | 214.3 | 7.3 | 29.7291 | -82.4727 |
| 41 | Duval on I-295 W, At East End of Buckman Bridge | I-295 W | 211.0 | 9.6 | 30.1893 | -81.6443 |
| 42 | Duval on I-295 W, At I-95S/I-295 E | I-295 W | 211.0 | 23.5 | 30.1673 | -81.5586 |
| 43 | Alachua on I-75, At MM 395 | I-75 | 208.7 | 5.9 | 29.7515 | -82.4916 |
| 44 | Duval on I-95, Before between Emerson St/University Blvd | I-95 | 207.7 | 35.8 | 30.2808 | -81.6204 |
| 45 | Alachua on I-75, At SR-121 | I-75 | 203.3 | 22.5 | 29.6028 | -82.3736 |
| 46 | Duval on I-295 E, Ramp To Heckscher Dr/Zoo Parkway | I-295 E | 203.3 | 24.6 | 30.4000 | -81.5634 |
| 47 | Alachua on I-75, At SR-222/NW 39th Ave | I-75 | 203.0 | 19.9 | 29.6883 | -82.4455 |
| 48 | Duval on I-295 E, At St Johns Bluff Rd/UNF | I-295 E | 202.7 | 55.3 | 30.2674 | -81.5202 |
| 49 | Duval on I-295 W, Beyond MM 2 | I-295 W | 201.0 | 19.9 | 30.1684 | -81.5895 |
| 50 | Duval on I-295 W, Beyond MM 1 | I-295 W | 200.7 | 23.6 | 30.1672 | -81.5712 |

<a id="table-s3"></a>**Table S3.** Road Ranger incidents by county, 2022–2024.

| County | Incidents | Share (%) |
| --- | ---: | ---: |
| Duval | 92,165 | 53.2 |
| Alachua | 22,206 | 12.8 |
| Columbia | 18,369 | 10.6 |
| St. Johns | 9,577 | 5.5 |
| Hamilton | 8,681 | 5.0 |
| Suwannee | 7,800 | 4.5 |
| Baker | 5,723 | 3.3 |
| Nassau | 3,143 | 1.8 |
| Madison | 3,058 | 1.8 |
| Clay | 2,358 | 1.4 |
| Levy | 25 | < 0.1 |
| Dixie | 23 | < 0.1 |
| Taylor | 17 | < 0.1 |
| Putnam | 9 | < 0.1 |
| Bradford | 4 | < 0.1 |
