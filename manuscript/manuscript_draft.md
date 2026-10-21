# Locating freeway service patrol stations with deep spatio-temporal incident forecasting: a predict-then-optimise study of FDOT District 2, Northeast Florida

Pascal Antwi¹, Thobias Sando²,
¹University of North Florida · ²University of North Florida · Corresponding author: Thobias Sando, t.sando@unf.edu

## 1. Introduction <a id="sec-1"></a>

## 2. Methodology <a id="sec-2"></a>

### 2.1 Study area <a id="sec-2-1"></a>

The study area is Florida Department of Transportation (FDOT) District 2, which covers 18 counties of Northeast and North Central Florida: Alachua, Baker, Bradford, Clay, Columbia, Dixie, Duval, Gilchrist, Hamilton, Lafayette, Levy, Madison, Nassau, Putnam, St. Johns, Suwannee, Taylor and Union ([Figure 1](#figure-1)a). It combines the Jacksonville metropolitan area (Duval County), a second urban centre at Gainesville (Alachua County) and large rural areas.

The limited-access network comprises three interstates and an urban beltway. I-95 follows the Atlantic coast through Nassau, Duval and St. Johns counties; I-10 runs west from Jacksonville through Baker, Columbia, Suwannee and Madison counties; and I-75 crosses Hamilton, Columbia and Alachua counties, meeting I-10 near Lake City. I-295 encircles Jacksonville, and limited-access state roads such as SR-202 (J. Turner Butler Boulevard), SR-9B and SR-115 (Arlington Expressway) link it with the city centre and the beaches ([Figure 1](#figure-1)b). These roads are patrolled by FDOT's Road Ranger freeway service patrol, which provides free roadside assistance and incident support as part of the state's traffic incident management programme.

The incidents analysed ([Section 2.2](#sec-2-2)) lie in 15 of the 18 counties; Gilchrist, Lafayette and Union counties, which have no interstate highway, recorded none. The region's humid subtropical climate, with frequent warm-season storms, motivates the inclusion of precipitation ([Section 2.6](#sec-2-6)).

<a id="figure-1"></a>

![Figure 1](../results/figures/Figure1_spatial_distribution.png)

**Figure 1.** Spatial distribution of incidents in FDOT District 2, 2022–2024. (a) District overview; the dashed box marks panel (b). (b) Central Jacksonville; red circles mark 14 of the 15 busiest 1 km grid cells. Hexagon shading shows incident counts on a logarithmic scale.

### 2.2 Data <a id="sec-2-2"></a>

Five data sources were combined.

**Incident records.** Incident data for 1 January 2022 to 31 December 2024 were obtained from the event chronology of the FDOT District 2 traffic management system [Author note: confirm the system name and data-use permission]. The export holds 9,206,764 records for 227,196 events; each record is one update to an event and gives the event type, time stamp, creating account, roadway description (county, route, direction and landmark or mile marker), coordinates and coded severity, surface, weather and lighting conditions. The four event types attended by Road Rangers (disabled vehicles, crashes, debris and abandoned vehicles) form the analysis sample of 173,198 incidents ([Section 2.3](#sec-2-3)).

**Traffic volumes.** Segment-level annual average daily traffic (AADT) for 2021–2024 was taken from FDOT's historical AADT data [[1]](#ref-fdot-aadt).

**Weather.** Hourly precipitation for 2022–2024 was obtained from NOAA's Integrated Surface Database [[2]](#ref-noaa-isd) for the 11 stations in or near the district with sufficient records ([Section 2.6](#sec-2-6)).

**Road network and candidate sites.** Motorways, trunk and primary roads and their ramps were extracted from OpenStreetMap [[3]](#ref-osm) and converted with OSMnx [[4]](#ref-boeing2017) to a directed graph of 8,944 nodes and 14,483 links with length, travel direction and, where tagged, speed limit. Its interchanges, rest areas and service plazas provided candidate station sites. U.S. Census TIGER/Line county boundaries and primary and secondary roads [[5]](#ref-census-tiger) were used to assign sites to counties and as an alternative network in the sensitivity analysis.

**Calendar and daylight.** Federal holidays were taken from the U.S. federal holiday calendar, and solar elevation was computed from standard solar position equations [[6]](#ref-spencer1971).

### 2.3 Data processing <a id="sec-2-3"></a>

Time stamps were converted to local time and coordinates from micro-degrees to decimal degrees. Five records with an invalid time stamp and 458 with missing or out-of-state coordinates were removed, leaving 9,206,301; none were duplicated, and four fields missing in more than half of the records were dropped. Records were grouped into 227,196 events: event type, creation time, creating account and condition codes were taken from the first record, location from the latest record, and duration as the time between the first and last update. The roadway description was parsed into county, route, direction and mile marker.

The four Road Ranger event types gave 173,198 incidents. Questionable records were flagged, not deleted: implausible durations (under 1 minute or over 24 hours; 5,189 incidents, excluded only from duration analyses), near-duplicates (same route and direction within 0.5 km and 15 minutes; 1.8%) and incidents created by the `avlrrsubsystem` account (49.8%). The last two were tested in robustness checks ([Section 2.10](#sec-2-10)). Daylight, twilight and darkness were assigned from solar elevation, with thresholds of −0.833° and −6°. Recorded condition codes varied little (99.9% minor severity; lighting code undocumented) and contradicted independent data: 94.9% of incidents logged during NOAA-recorded precipitation were coded as clear weather. Precipitation and darkness were therefore taken from NOAA and solar position ([Table S1](#table-s1)).

Incidents were assigned to 1 km × 1 km grid cells in a local equirectangular projection; the 983 cells with incidents form the spatial units. Time was divided into 8,768 three-hour windows, giving a cell-by-window panel with a mean of 0.020 incidents, in which 98.1% of cell-windows are empty.

### 2.4 Research framework <a id="sec-2-4"></a>

The study follows a predict-then-optimise framework in four stages ([Figure 2](#figure-2)). The incident records, road cells, traffic and weather data, and calendar and daylight variables are first combined into a cell graph, in which neighbouring 1 km cells are linked and each cell carries incident counts for consecutive three-hour windows ([Sections 2.3](#sec-2-3) and [2.6](#sec-2-6)).

In the first stage, persistent concentrations of incidents are identified with the Getis-Ord Gi\* statistic [[7]](#ref-getis1992) on incident counts and on traffic-adjusted incident rates, with significance adjusted for multiple testing by the false discovery rate [[8]](#ref-benjamini1995) ([Section 2.7](#sec-2-7)). In the second stage, incidents are forecast one day ahead for every cell and window. Three baselines, a historical average, a Poisson log-linear model and gradient-boosted trees (LightGBM [[9]](#ref-ke2017)), are compared with three deep learning models: a long short-term memory network [[10]](#ref-hochreiter1997), Graph WaveNet [[11]](#ref-wu2019) and a spatio-temporal Transformer [[12]](#ref-vaswani2017) ([Section 2.8](#sec-2-8)). In the third stage, the observed and predicted demand is used to locate Road Ranger stations at candidate interchanges, rest areas and service plazas with the maximal covering location problem [[13]](#ref-church1974), as fixed stations and as day-ahead staging of units ([Section 2.9](#sec-2-9)).

In the fourth stage, all models are fitted on data up to 30 September 2023, tuned on October–December 2023 and evaluated on the unseen incidents of 2024. Evaluation covers forecast error and the share of incidents reached within 10, 15 and 20 minutes, followed by sensitivity analyses, temporal validation and a simulation in which units can be busy ([Sections 2.10](#sec-2-10) and [2.11](#sec-2-11)).

<a id="figure-2"></a>

![Figure 2](../results/figures/Figure2_framework.png)

**Figure 2.** Study framework. AADT: annual average daily traffic; NOAA: National Oceanic and Atmospheric Administration; HA: historical average; FDR: false discovery rate; MCLP: maximal covering location problem.

### 2.5 Exploratory data analysis <a id="sec-2-5"></a>

Exploratory analysis described the composition, timing, location and duration of incidents. Incident types were summarised by year, weekday share, share in the afternoon peak (15:00–17:59) and share created through the vehicle-location subsystem ([Table 1](#table-1)), and all recorded event types were compared with the analysis sample ([Figure S1](#figure-s1)). Temporal patterns were examined as monthly counts by type ([Figure S2](#figure-s2)), mean hourly counts by hour and day of week ([Figure 3](#figure-3)) and the hourly distribution within each type ([Figure S3](#figure-s3)). Spatial patterns were mapped as hexagonal-bin densities on a logarithmic scale ([Figure 1](#figure-1)). Concentration was measured by ranking the 1 km cells by mean annual incidents and computing the share of all incidents held by the busiest cells ([Figure 4](#figure-4)), and counts by route and type were compared for the eight busiest routes ([Figure S4](#figure-s4)). Event duration was summarised by type with medians, interquartile ranges and 5th–95th percentiles, excluding flagged durations ([Figure 5](#figure-5)). Finally, the completeness and variability of the recorded condition codes were tabulated to decide which variables could enter the models ([Table S1](#table-s1)).

### 2.6 Traffic exposure, precipitation and road network <a id="sec-2-6"></a>

**Traffic exposure.** Each incident was matched to the nearest AADT segment of its own year within 150 m (96.9% matched). FDOT roadways with at least 20 matched incidents (594 roadway identifiers) were taken as the patrolled network, and the vehicle-kilometres travelled in each cell and year were computed as the sum, over these segments, of AADT × segment length within the cell × days in the year. Exposure was available for 944 cells holding 99.1% of incidents. Rates per million vehicle-kilometres were smoothed with a global empirical Bayes estimator [[14]](#ref-marshall1991) for hotspot analysis ([Section 2.7](#sec-2-7)); the forecasting models use the previous year's exposure, the latest available at forecast time.

**Precipitation.** Hourly totals were taken from each station's routine hourly report; special reports, which carry partial accumulations, were not added. Totals were summed to three-hour windows and assigned to each cell from its nearest station (median distance 15.3 km). Incident rates in wet and dry windows were compared by incident type and precipitation class (light, < 2.5 mm; moderate, 2.5–10 mm; heavy, ≥ 10 mm per window) with Mantel–Haenszel rate ratios [[15]](#ref-mantel1959) stratified by window of day, month and day type, with Greenland–Robins confidence intervals [[16]](#ref-greenland1985).

**Road network and sites.** Two-way OpenStreetMap links were represented in both directions, and the largest strongly connected component was retained (92.5% of links). Off-peak speeds were the posted limits (56.0% of links) or class defaults (motorway 65, trunk 55, primary 45 and ramps 30–35 mph); peak speeds (weekdays 06:00–08:59 and 15:00–17:59) were set to two-thirds of off-peak. Incidents were snapped to the nearest link within 200 m whose heading matched their recorded direction (95.1% of incidents), otherwise to the nearest link. Candidate sites in District 2 within 0.5 km of each other were merged, giving 307 sites (275 interchanges, 19 service plazas and 13 rest areas); a unit leaves a site from any network node within 300 m.

### 2.7 Hotspot detection <a id="sec-2-7"></a>

Hotspots were identified with the Getis-Ord Gi\* statistic [[7]](#ref-getis1992), [[17]](#ref-ord1995), applied to the mean annual number of incidents *x*ⱼ in each of the *n* = 983 cells, with binary weights *w*ᵢⱼ = 1 for cells within 2 km of cell *i*, including *i* itself:

$$
G_i^* = \frac{\sum_j w_{ij} x_j - \bar{x} \sum_j w_{ij}}{s \sqrt{\left[ n \sum_j w_{ij}^2 - \left( \sum_j w_{ij} \right)^2 \right] / (n - 1)}},
$$

where *x̄* and *s* are the mean and standard deviation of *x*. Two-sided p-values from the standard normal distribution were adjusted for the false discovery rate [[8]](#ref-benjamini1995), and cells were classified at q < 0.01, 0.05 and 0.10; cells with a positive statistic and q < 0.05 are termed hot. Contiguous hot cells were grouped into clusters and named after their busiest cell. Persistence was assessed by repeating the analysis for each year and counting the years in which each cell was hot. Robustness was assessed by repeating it without incidents created through the vehicle-location subsystem, without near-duplicates and for crashes only, with agreement measured as the share of hot cells retained and the Jaccard index. A second analysis applied the same procedure to empirical Bayes-smoothed rates per million vehicle-kilometres for the 944 cells with exposure data ([Section 2.6](#sec-2-6)).

### 2.8 Demand forecasting <a id="sec-2-8"></a>

**Task and data split.** At the start of each day, incidents are forecast for each of the eight three-hour windows in every cell, using only data up to the end of the previous day. Models were trained on 29 January 2022 – 30 September 2023 (610 days; the first 28 days of 2022 supply lagged inputs), tuned and early-stopped on 1 October – 31 December 2023 (92 days) and tested on 2024 (366 days).

**Inputs.** The historical mean for each cell, window and day type (weekday, or weekend and federal holiday) over the training days; counts in the same window one and seven days earlier; cell totals over the previous 1, 7 and 28 days; the neighbouring cells' 7-day total; the district total on the previous day; window, weekday, month and holiday indicators; the share of the window in darkness; cell coordinates; the previous year's traffic exposure; and the previous day's precipitation.

**Baselines.** (i) The historical mean; (ii) a Poisson log-linear model with cell, window × day type and month main effects, fitted by iterative proportional fitting; and (iii) LightGBM [[9]](#ref-ke2017) with a Poisson objective (learning rate 0.05, 63 leaves, at least 500 observations per leaf, early stopping after 100 rounds without improvement). An ablation refitted LightGBM without the exposure and precipitation inputs, and with the observed precipitation in the target window as a perfect-forecast bound.

**Deep learning models.** Each model encodes the last 16 windows (two days) of counts and precipitation in every cell, with time-of-day and weekend indicators, into a cell representation; a shared output layer combines it with the inputs above and predicts the log-rate, offset by the log historical mean, under a Poisson likelihood. The LSTM [[10]](#ref-hochreiter1997) encodes each cell separately, without spatial information; Graph WaveNet [[11]](#ref-wu2019) combines gated dilated temporal convolutions with diffusion convolution over the cell graph and a learned adjacency matrix; and the spatio-temporal Transformer [[12]](#ref-vaswani2017) applies attention over time within each cell and then across cells. Models were trained with Adam [[18]](#ref-kingma2015) on batches of eight days with early stopping (patience 3). Hidden size (32 or 64) and learning rate (10⁻³ or 3 × 10⁻⁴) were tuned on the validation period; differences in validation deviance below 0.1% were treated as ties, and the smaller configuration was retained ([Table S7](#table-s7)). LightGBM and each deep model were trained with five random seeds.

### 2.9 Station location optimisation <a id="sec-2-9"></a>

**Demand and coverage.** Demand points are the directed links with at least one incident in 2022–2023 (1,708 links), weighted by their mean annual number of incidents *a*ᵢʳ in each speed regime *r* (peak, off-peak). A candidate site *j* covers link *i* in regime *r* if the travel time from *j* to the midpoint of *i* is at most *T* minutes; *N*ᵢʳ is the set of such sites.

**Fixed stations.** *p* stations were located with the maximal covering location problem [[13]](#ref-church1974), extended to the two speed regimes:

$$
\max \sum_{r} \sum_{i} a_i^r y_i^r \quad \text{s.t.} \quad \sum_{j \in N_i^r} x_j \ge y_i^r \;\; \forall i, r, \qquad \sum_j x_j = p, \qquad x_j \in \{0, 1\}, \;\; 0 \le y_i^r \le 1,
$$

where *x*ⱼ = 1 if a station is placed at site *j* and *y*ᵢʳ is the covered share of the demand at link *i*. The problem was solved exactly as a mixed-integer program with the HiGHS solver [[19]](#ref-huangfu2018) through SciPy [[20]](#ref-virtanen2020), for *p* = 1–20 and *T* = 10, 15 and 20 minutes.

**Day-ahead staging.** For each day of 2024 and four time bands (night, 18:00–05:59; morning peak, 06:00–08:59; midday, 09:00–14:59; afternoon peak, 15:00–17:59), *p* staging sites were selected by greedy maximal covering of the forecast demand in that band, with each cell's forecast distributed over its links in proportion to their 2022–2023 incidents. An oracle using the band's actual incidents gives an upper bound.

**Comparison layouts.** Two layouts without optimisation were also evaluated: the candidate sites nearest the busiest 2022–2023 cells, and randomly drawn sites (mean of 200 draws).

### 2.10 Evaluation and sensitivity analysis <a id="sec-2-10"></a>

**Forecasts.** On the 2024 test year, models were compared by the mean absolute error, root mean squared error and mean Poisson deviance over cell-windows, and by the daily hit rate, the share of a day's incidents falling in the 5% of cells with the highest predicted daily demand, together with the predictive accuracy index (hit rate ÷ share of cells) [[21]](#ref-chainey2008). Differences in deviance from LightGBM were assessed with a bootstrap over days (2,000 resamples) using seed-averaged predictions; results are reported as mean ± standard deviation over seeds.

**Station layouts.** Each layout was evaluated on the 59,981 incidents of 2024 by the share reached within *T* minutes from the nearest station or staged unit, using each incident's exact location and the speed regime at its time, and by the mean travel time.

**Sensitivity and robustness.** For 10 stations and *T* = 15 minutes, the fixed layout was re-solved with peak speeds of 50% and 83% of off-peak; with off-peak speeds 15% lower and higher; with demand excluding incidents created through the vehicle-location subsystem, excluding near-duplicates, and for crashes only; and with two alternative travel-time models on the road cells, the undirected Census network and a cell graph with distances inflated by a circuity factor of 1.2. For temporal validation, sites were selected on 2022 and evaluated on 2023, and selected on 2023 and evaluated on 2024. Finally, the problem was re-solved on 200 bootstrap samples of 2022–2023 days, on each year alone and under each scenario, recording how often each recommended site, or a site within 5 km of it, was selected, and the coverage lost by the recommended layout relative to the layout optimised for each speed scenario.

### 2.11 Simulation with busy units <a id="sec-2-11"></a>

The coverage model assumes that every unit is free when an incident occurs. A discrete-event simulation of 2024 relaxed this assumption. Incidents were processed in the order they were logged and assigned to the unit that could reach them first: a free unit departs immediately, and a busy unit departs from its station once it has returned from its current job. A unit is busy for the travel time to the incident, the on-scene time and the travel time back to its station on the directed network, at the speed regime of the incident's time. On-scene time was the logged event duration, replaced by the median for the incident type where flagged ([Section 2.3](#sec-2-3)). Every incident was assumed to require a unit, and units were assumed to operate around the clock. Layouts of 10, 15 and 20 stations (*T* = 15 minutes) were simulated with fleets of one to three units per station on average, allocated either equally or in proportion to each station's 2022–2023 demand (largest remainder, with at least one unit per station). Outcomes were the share of incidents reached within 10, 15 and 20 minutes of being logged, the mean and 90th percentile response times, the share of incidents delayed because a closer unit was busy, and unit utilisation. Two variants halved the on-scene times and excluded incidents created through the vehicle-location subsystem, which a patrolling unit had already found.

## 3. Results <a id="sec-3"></a>

### 3.1 Incident characteristics <a id="sec-3-1"></a>

Between 1 January 2022 and 31 December 2024, the traffic management system logged 227,196 events in District 2, of which 173,198 (76.2%) were of the four types attended by Road Rangers ([Table 1](#table-1)). Disabled vehicles were the most frequent type (101,933; 58.9%), followed by crashes (44,158; 25.5%), debris on the roadway (16,979; 9.8%) and abandoned vehicles (10,128; 5.8%). The most common events outside the analysis sample were congestion (22,053), scheduled road work (12,658) and reduced visibility (6,653) ([Figure S1](#figure-s1)).

Annual totals ranged from 56,450 in 2023 to 59,981 in 2024, a difference of 6.3%. The increase in 2024 came mainly from disabled vehicles (9.2% more than in 2023) and abandoned vehicles (22.2% more), whereas annual crash counts differed by less than 5% across the three years ([Figure S2](#figure-s2)). Monthly totals ranged from 3,897 (February 2023) to 5,621 (May 2024), with a mean of 4,811.

The incident types differed in how they were reported and how long they lasted. Half of all incidents (49.8%) were created through the vehicle-location subsystem, ranging from 4.9% of crashes to 67.9% of disabled vehicles and 86.8% of abandoned vehicles. The median event duration was 18.9 minutes, ranging from 4.7 minutes for abandoned vehicles to 56.7 minutes for crashes ([Section 3.4](#sec-3-4)). The shares of incidents occurring on weekdays (75.0–78.0%) were similar across types, whereas the share between 15:00 and 17:59 was about half as large for abandoned vehicles (12.5%) as for the other types (22.1–25.3%).

<a id="table-1"></a>**Table 1.** Characteristics of incidents by type, FDOT District 2, 2022–2024.

| Incident type | n | % | 2022 | 2023 | 2024 | Median duration, min (IQR) | Weekday % | 15:00–17:59 % | AVL-created % |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Disabled vehicle | 101,933 | 58.9 | 33,260 | 32,828 | 35,845 | 13.4 (4.9–31.7) | 75.4 | 23.0 | 67.9 |
| Crash | 44,158 | 25.5 | 14,401 | 15,013 | 14,744 | 56.7 (29.9–88.2) | 77.4 | 25.3 | 4.9 |
| Debris on roadway | 16,979 | 9.8 | 5,822 | 5,529 | 5,628 | 12.8 (3.8–28.6) | 78.0 | 22.1 | 36.3 |
| Abandoned vehicle | 10,128 | 5.8 | 3,284 | 3,080 | 3,764 | 4.7 (3.0–9.9) | 75.0 | 12.5 | 86.8 |
| **All** | **173,198** | **100.0** | **56,767** | **56,450** | **59,981** | **18.9 (5.7–45.6)** | **76.2** | **22.9** | **49.8** |

*Note:* Duration excludes 5,189 flagged events (< 1 min or > 24 h). AVL-created: event created by the `avlrrsubsystem` account. IQR: interquartile range.

### 3.2 Temporal patterns <a id="sec-3-2"></a>

Incidents followed a weekday commuting pattern ([Figure 3](#figure-3)). On average, 168.7 incidents were logged per weekday and 131.5 per weekend day. On weekdays, the hourly rate rose from 1.7 incidents per hour at 03:00–04:59 to a morning peak of 11.3 at 08:00–08:59, stayed between 9.0 and 10.1 from 09:00 to 13:59, and reached its maximum of 13.2–13.7 between 15:00 and 17:59 before falling to 3.0 by 23:00. The highest rate in any hour of the week, 14.8 incidents per hour, occurred on Fridays between 15:00 and 15:59, and the lowest, 1.4, on Tuesdays between 04:00 and 04:59. Weekend days had no morning peak; their rate rose gradually to a broad maximum of 8.0–8.9 incidents per hour between 12:00 and 16:59, and between midnight and 04:59 it was higher than on weekdays (2.2–3.1 against 1.7–2.3).

The timing differed by incident type ([Figure S3](#figure-s3)). Disabled vehicles and crashes peaked at 17:00–17:59 (7.7% and 9.0% of each type), with 23.0% and 25.3% occurring between 15:00 and 17:59. Debris on the roadway peaked earlier, at 14:00–14:59 (8.2%), and had the smallest share between midnight and 05:59 (4.7%, against 8.5–9.1% for the other types). Abandoned vehicles peaked in the morning, at 08:00–08:59 (12.4%), with 27.5% occurring between 06:00 and 08:59.

<a id="figure-3"></a>

![Figure 3](../results/figures/Figure3_hour_by_weekday.png)

**Figure 3.** Mean number of incidents per hour, by hour of day and day of week, 2022–2024.

### 3.3 Spatial distribution and concentration <a id="sec-3-3"></a>

Incidents were concentrated in Duval County, which accounted for 53.2% of the total, followed by Alachua (12.8%), Columbia (10.6%), St. Johns (5.5%) and Hamilton (5.0%) counties ([Figure 1](#figure-1)). Interstates carried 91.3% of incidents: I-75 (26.3%), I-295 (23.2%; 14.4% on the western and 8.8% on the eastern half), I-95 (22.3%) and I-10 (18.5%).

Within the network, incidents were concentrated in a small share of the 983 cells. The busiest 145 cells (14.8%) contained half of all incidents and 333 cells (33.9%) contained 80%, whereas 195 cells (19.8%) recorded on average no more than one incident per year; the median cell recorded 35.3 incidents per year. The 15 busiest cells held 9.9% of incidents, and 14 of them lay in central Jacksonville ([Figure 4](#figure-4)). The busiest cell, on I-295 W between San Jose Boulevard and the Buckman Bridge, recorded 531 incidents per year, followed by I-95 at the ramp to I-10 (480) and two further Buckman Bridge cells (429 and 408); the only busiest-15 cell outside Duval County was on I-75 near mile marker 386 in Alachua County (313 per year). The crash share in these cells ranged from 6.3% at the western end of the Buckman Bridge to 48.3% on I-95 at the Martin Luther King Jr. Parkway.

The mix of incident types also differed between routes ([Figure S4](#figure-s4)). Crashes made up 8.9% of incidents on I-75, 19.7% on I-10, 27.5% on I-295 W, 34.8% on I-95 and 36.3% on I-295 E, and 96.4% on SR-21 (Blanding Boulevard), where disabled vehicles made up 2.7%.

<a id="figure-4"></a>

![Figure 4](../results/figures/Figure4_top_hotspot_cells.png)

**Figure 4.** The 15 one-kilometre grid cells with the highest mean annual number of incidents, with incidents per year and crash share.

### 3.4 Event duration <a id="sec-3-4"></a>

Event duration, measured from the first to the last logged update, differed markedly between incident types ([Figure 5](#figure-5); [Table 1](#table-1)). After excluding 5,189 flagged durations, the median was 18.9 minutes, the 95th percentile 108.3 minutes, and 17.6% of incidents lasted more than one hour. Crashes lasted longest, with a median of 56.7 minutes (interquartile range 29.9–88.2; 95th percentile 158.2); 47.0% of crashes lasted more than one hour and 11.3% more than two hours. Disabled vehicles (median 13.4 minutes; interquartile range 4.9–31.7) and debris on the roadway (12.8; 3.8–28.6) had similar distributions, with 8.5% and 6.2%, respectively, lasting more than one hour. Abandoned vehicles had the shortest events (median 4.7 minutes; interquartile range 3.0–9.9), although their 95th percentile reached 50.3 minutes.

<a id="figure-5"></a>

![Figure 5](../results/figures/Figure5_event_duration.png)

**Figure 5.** Event duration (first to last log update) by incident type; boxes show the interquartile range, whiskers the 5th–95th percentiles; logarithmic scale. Events shorter than 1 minute or longer than 24 hours excluded (n = 5,189).

### 3.5 Precipitation and incident rates <a id="sec-3-5"></a>
*Figures and tables: [Figure S8](#figure-s8).*

### 3.6 Hotspots <a id="sec-3-6"></a>
*Figures and tables: [Figure 6](#figure-6); [Table 2](#table-2); [Figure S5](#figure-s5); [Figure S7](#figure-s7); [Table S2](#table-s2).*

### 3.7 Forecasting performance <a id="sec-3-7"></a>
*Figures and tables: [Table 3](#table-3); [Figure 7](#figure-7); [Table S3](#table-s3); [Table S7](#table-s7).*

### 3.8 Station locations and coverage <a id="sec-3-8"></a>
*Figures and tables: [Figure 8](#figure-8); [Table 4](#table-4); [Figure 9](#figure-9); [Table 5](#table-5).*

### 3.9 Sensitivity analysis and temporal validation <a id="sec-3-9"></a>
*Figures and tables: [Figure S6](#figure-s6); [Table S4](#table-s4); [Figure S9](#figure-s9); [Table S5](#table-s5); [Table S6](#table-s6).*

### 3.10 Fleet size with busy units <a id="sec-3-10"></a>
*Figures and tables: [Table 6](#table-6); [Figure 10](#figure-10).*

## 4. Discussion <a id="sec-4"></a>

## 5. Conclusion <a id="sec-5"></a>

## References

<a id="ref-fdot-aadt"></a>[1] Florida Department of Transportation, "Annual Average Daily Traffic (historical), 2021–2025," Transportation Data and Analytics Office, Tallahassee, FL, USA. [Online]. Available: https://gis-fdot.opendata.arcgis.com

<a id="ref-noaa-isd"></a>[2] National Centers for Environmental Information, "Global Hourly – Integrated Surface Database (ISD)," NOAA, Asheville, NC, USA. [Online]. Available: https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database

<a id="ref-osm"></a>[3] OpenStreetMap contributors, "OpenStreetMap," Florida extract distributed by Geofabrik GmbH, 2026. [Online]. Available: https://download.geofabrik.de/north-america/us/florida.html

<a id="ref-boeing2017"></a>[4] G. Boeing, "OSMnx: New methods for acquiring, constructing, analyzing, and visualizing complex street networks," *Comput. Environ. Urban Syst.*, vol. 65, pp. 126–139, 2017.

<a id="ref-census-tiger"></a>[5] U.S. Census Bureau, "TIGER/Line Shapefiles 2023: Counties; Primary and secondary roads, Florida," Washington, DC, USA, 2023. [Online]. Available: https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html

<a id="ref-spencer1971"></a>[6] J. W. Spencer, "Fourier series representation of the position of the sun," *Search*, vol. 2, no. 5, p. 172, 1971.

<a id="ref-getis1992"></a>[7] A. Getis and J. K. Ord, "The analysis of spatial association by use of distance statistics," *Geogr. Anal.*, vol. 24, no. 3, pp. 189–206, 1992.

<a id="ref-benjamini1995"></a>[8] Y. Benjamini and Y. Hochberg, "Controlling the false discovery rate: A practical and powerful approach to multiple testing," *J. R. Stat. Soc. Ser. B*, vol. 57, no. 1, pp. 289–300, 1995.

<a id="ref-ke2017"></a>[9] G. Ke, Q. Meng, T. Finley, T. Wang, W. Chen, W. Ma, Q. Ye, and T.-Y. Liu, "LightGBM: A highly efficient gradient boosting decision tree," in *Adv. Neural Inf. Process. Syst.*, vol. 30, 2017.

<a id="ref-hochreiter1997"></a>[10] S. Hochreiter and J. Schmidhuber, "Long short-term memory," *Neural Comput.*, vol. 9, no. 8, pp. 1735–1780, 1997.

<a id="ref-wu2019"></a>[11] Z. Wu, S. Pan, G. Long, J. Jiang, and C. Zhang, "Graph WaveNet for deep spatial-temporal graph modeling," in *Proc. 28th Int. Joint Conf. Artif. Intell. (IJCAI)*, 2019, pp. 1907–1913.

<a id="ref-vaswani2017"></a>[12] A. Vaswani, N. Shazeer, N. Parmar, J. Uszkoreit, L. Jones, A. N. Gomez, Ł. Kaiser, and I. Polosukhin, "Attention is all you need," in *Adv. Neural Inf. Process. Syst.*, vol. 30, 2017.

<a id="ref-church1974"></a>[13] R. Church and C. ReVelle, "The maximal covering location problem," *Pap. Reg. Sci. Assoc.*, vol. 32, pp. 101–118, 1974.

<a id="ref-marshall1991"></a>[14] R. J. Marshall, "Mapping disease and mortality rates using empirical Bayes estimators," *J. R. Stat. Soc. Ser. C (Appl. Stat.)*, vol. 40, no. 2, pp. 283–294, 1991.

<a id="ref-mantel1959"></a>[15] N. Mantel and W. Haenszel, "Statistical aspects of the analysis of data from retrospective studies of disease," *J. Natl. Cancer Inst.*, vol. 22, no. 4, pp. 719–748, 1959.

<a id="ref-greenland1985"></a>[16] S. Greenland and J. M. Robins, "Estimation of a common effect parameter from sparse follow-up data," *Biometrics*, vol. 41, no. 1, pp. 55–68, 1985.

<a id="ref-ord1995"></a>[17] J. K. Ord and A. Getis, "Local spatial autocorrelation statistics: Distributional issues and an application," *Geogr. Anal.*, vol. 27, no. 4, pp. 286–306, 1995.

<a id="ref-kingma2015"></a>[18] D. P. Kingma and J. Ba, "Adam: A method for stochastic optimization," in *Proc. Int. Conf. Learn. Represent. (ICLR)*, 2015.

<a id="ref-huangfu2018"></a>[19] Q. Huangfu and J. A. J. Hall, "Parallelizing the dual revised simplex method," *Math. Program. Comput.*, vol. 10, no. 1, pp. 119–142, 2018.

<a id="ref-virtanen2020"></a>[20] P. Virtanen *et al.*, "SciPy 1.0: Fundamental algorithms for scientific computing in Python," *Nat. Methods*, vol. 17, pp. 261–272, 2020.

<a id="ref-chainey2008"></a>[21] S. Chainey, L. Tompson, and S. Uhlig, "The utility of hotspot mapping for predicting spatial patterns of crime," *Secur. J.*, vol. 21, pp. 4–28, 2008.

<a id="ref-hakimi1964"></a>[22] S. L. Hakimi, "Optimum locations of switching centers and the absolute centers and medians of a graph," *Oper. Res.*, vol. 12, no. 3, pp. 450–459, 1964.

<a id="ref-li2018"></a>[23] Y. Li, R. Yu, C. Shahabi, and Y. Liu, "Diffusion convolutional recurrent neural network: Data-driven traffic forecasting," in *Proc. Int. Conf. Learn. Represent. (ICLR)*, 2018.

<a id="ref-lundberg2017"></a>[24] S. M. Lundberg and S.-I. Lee, "A unified approach to interpreting model predictions," in *Adv. Neural Inf. Process. Syst.*, vol. 30, 2017.

<a id="ref-okabe2009"></a>[25] A. Okabe, T. Satoh, and K. Sugihara, "A kernel density estimation method for networks, its computational method and a GIS-based tool," *Int. J. Geogr. Inf. Sci.*, vol. 23, no. 1, pp. 7–32, 2009.

<a id="ref-toregas1971"></a>[26] C. Toregas, R. Swain, C. ReVelle, and L. Bergman, "The location of emergency service facilities," *Oper. Res.*, vol. 19, no. 6, pp. 1363–1373, 1971.

<a id="ref-xie2008"></a>[27] Z. Xie and J. Yan, "Kernel density estimation of traffic accidents in a network space," *Comput. Environ. Urban Syst.*, vol. 32, no. 5, pp. 396–406, 2008.

<a id="ref-yu2018"></a>[28] B. Yu, H. Yin, and Z. Zhu, "Spatio-temporal graph convolutional networks: A deep learning framework for traffic forecasting," in *Proc. 27th Int. Joint Conf. Artif. Intell. (IJCAI)*, 2018, pp. 3634–3640.

<a id="ref-yuan2018"></a>[29] Z. Yuan, X. Zhou, and T. Yang, "Hetero-ConvLSTM: A deep learning approach to traffic accident prediction on heterogeneous spatio-temporal data," in *Proc. 24th ACM SIGKDD Int. Conf. Knowl. Discov. Data Min.*, 2018, pp. 984–992.

---

## Appendix A. Figures

<a id="figure-6"></a>

![Figure 6](../results/figures/Figure6_hotspots.png)

**Figure 6.** Getis-Ord Gi* hotspots of incidents on 1 km road cells, 2022–2024 (binary weights within 2 km; Benjamini–Hochberg q-values). (a) FDOT District 2; (b) Jacksonville, with hotspot cluster IDs H1–H8.

*Cited in [Section 3.6](#sec-3-6).*

<a id="figure-7"></a>

![Figure 7](../results/figures/Figure7_forecast_performance.png)

**Figure 7.** Day-ahead forecast performance on 2024. (a) Mean Poisson deviance of each deep model relative to LightGBM, by three-hour window. (b) Observed vs predicted 2024 incidents per cell, Graph WaveNet (log scales; dashed line: equality).

*Cited in [Section 3.7](#sec-3-7).*

<a id="figure-8"></a>

![Figure 8](../results/figures/Figure8_coverage.png)

**Figure 8.** Share of 2024 incidents within 10, 15 and 20 minutes of the nearest station or staged unit, by number of stations or units: static layouts (2022–2023 demand), day-ahead staging from five forecasts (line: mean; band: range), and the oracle upper bound.

*Cited in [Section 3.8](#sec-3-8).*

<a id="figure-9"></a>

![Figure 9](../results/figures/Figure9_stations.png)

**Figure 9.** Recommended static station locations (10 stations, 15-minute standard), labelled S1–S10, and the 307 candidate sites (interchanges, rest areas and service plazas). Blue cells: at least half of the cell's 2024 incidents within 15 minutes of a station at off-peak speed. (a) FDOT District 2; (b) Jacksonville.

*Cited in [Section 3.8](#sec-3-8).*

<a id="figure-10"></a>

![Figure 10](../results/figures/Figure10_simulation.png)

**Figure 10.** Simulated share of 2024 incidents reached within 15 minutes by fleet size, for layouts of 10, 15 and 20 stations, with equal units per station (solid) or units allocated in proportion to 2022–2023 demand (dashed). Dotted lines: coverage when units are always free.

*Cited in [Section 3.10](#sec-3-10).*


## Appendix B. Tables

<a id="table-2"></a>**Table 2.** Incident hotspot clusters: contiguous Gi* hot cells (q < 0.05), named after their busiest cell, 2022–2024.

| ID | Hotspot location | Routes | Size (1 km cells) | Incidents per year | Crash share (%) | Cells hot in all 3 years | Max Gi* z | Million vehicle-km per year | Incidents per million vehicle-km |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H1 | I-95 at ramp to I-10 (Duval County) | Acosta Bridge, I-10, I-95 | 14 | 3,290 | 40.8 | 13 of 14 | 7.77 | 787.8 | 4.18 |
| H2 | I-295 W at Buckman Bridge (Duval County) | I-295 W | 11 | 2,382 | 17.1 | 11 of 11 | 6.96 | 422.4 | 5.64 |
| H3 | I-295 W at I-95S/I-295 E (Duval County, MM 1) | I-295 W | 3 | 554 | 23.6 | 2 of 3 | 4.25 | 216.9 | 2.56 |
| H4 | I-295 E at Dames Point Bridge (Duval County) | I-295 E | 3 | 409 | 17.2 | 2 of 3 | 3.69 | 69.1 | 5.92 |
| H5 | I-295 W at ramp to Normandy Blvd/SR-228 (Duval County, MM 18) | I-295 W | 1 | 287 | 32.6 | 0 of 1 | 3.37 | 56.5 | 5.08 |
| H6 | I-295 W at I-10 (Duval County, MM 20) | I-295 W | 1 | 256 | 38.3 | 1 of 1 | 3.76 | 98.7 | 2.59 |
| H7 | I-295 E at St Johns Bluff Rd/UNF (Duval County) | I-295 E | 1 | 203 | 55.3 | 1 of 1 | 4.15 | 65.4 | 3.10 |
| H8 | I-295 E at ramp to Butler Blvd EB ramp (Duval County, MM 54) | I-295 E | 1 | 185 | 37.0 | 1 of 1 | 3.26 | 133.5 | 1.38 |

*Note:* Incidents per year and vehicle-km are summed over the cluster's cells. Vehicle-km: FDOT AADT × segment length within the cell × days, on FDOT roadways with at least 20 matched incidents, mean of 2022–2024.


<a id="table-3"></a>**Table 3.** Day-ahead forecast performance on 2024 (366 days × 8 windows × 983 cells); mean ± s.d. over five seeds where applicable.

| Model | Runs | MAE (×10⁻²) | RMSE (×10⁻²) | Poisson deviance (×10⁻²) | Hit rate, top 5% cells (%) | PAI |
| --- | ---: | --- | --- | --- | --- | --- |
| Historical average | 1 | 3.796 | 15.068 | 14.471 | 23.26 | 4.57 |
| Poisson log-linear | 1 | 3.781 | 15.054 | 13.259 | 22.85 | 4.49 |
| LightGBM | 5 | 3.801 ± 0.002 | 15.044 ± 0.001 | 13.266 ± 0.006 | 23.59 ± 0.04 | 4.64 ± 0.01 |
| LSTM (no graph) | 5 | 3.832 ± 0.029 | 15.054 ± 0.005 | 13.329 ± 0.018 | 23.48 ± 0.12 | 4.62 ± 0.02 |
| Graph WaveNet | 5 | 3.838 ± 0.020 | 15.054 ± 0.005 | 13.327 ± 0.022 | 23.49 ± 0.10 | 4.62 ± 0.02 |
| ST-Transformer | 5 | 3.866 ± 0.052 | 15.058 ± 0.005 | 13.343 ± 0.017 | 23.37 ± 0.12 | 4.59 ± 0.02 |

*Note:* PAI: predictive accuracy index.


<a id="table-4"></a>**Table 4.** Station layouts with 10 stations or units, evaluated on the 59,981 incidents of 2024.

| Layout (demand source) | Stations | Covered ≤ 10 min (%) | ≤ 15 min (%) | ≤ 20 min (%) | Mean travel time (min) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current Road Ranger stations | 10 | [pending] | [pending] | [pending] | [pending] |
| Sites nearest the busiest cells (no optimisation) | 10 | 37.9 | 47.1 | 52.2 | 40.5 |
| Random candidate sites (mean of 200 draws) | 10 | 34.8 | 52.7 | 63.8 | 22.5 |
| Static stations, 2022–2023 demand (MCLP) | 10 | 62.9 | 80.7 | 91.4 | 11.7 |
| Day-ahead staging, historical average | 10 | 63.5 | 80.5 | 90.4 | 12.4 |
| Day-ahead staging, LightGBM | 10 | 63.2 | 80.6 | 90.3 | 12.3 |
| Day-ahead staging, LSTM | 10 | 63.5 | 80.5 | 90.4 | 12.4 |
| Day-ahead staging, Graph WaveNet | 10 | 63.5 | 80.5 | 90.4 | 12.3 |
| Day-ahead staging, ST-Transformer | 10 | 63.5 | 80.5 | 90.4 | 12.4 |
| Day-ahead staging, oracle (upper bound) | 10 | 79.9 | 91.3 | 95.5 | 10.1 |

*Note:* Comparison layouts are not optimised: the candidate site nearest each of the busiest 2022–2023 cells (distinct sites), and random candidate sites (mean of 200 draws). Static layouts are solved separately for each response-time standard; their mean travel time refers to the 15-minute layout. Travel times: shortest paths on the directed OpenStreetMap network (motorway, trunk and primary roads with ramps), with incidents matched to their recorded direction of travel.


<a id="table-5"></a>**Table 5.** Recommended station sites (10 stations, 15-minute standard, 2022–2023 demand), selected from 307 candidate interchanges, rest areas and service plazas.

| ID | Station site | Nearest incident landmark | Latitude | Longitude | 2024 incidents nearest to station | Share of 2024 incidents (%) | Of these, reached within 15 min (%) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| S1 | I-295 Exit 54, Duval County | I-295 E at Gate Parkway | 30.2425 | -81.5146 | 10,274 | 17.1 | 89.2 |
| S2 | I-10 Exit 358, Duval County | I-10 at Cassat Ave | 30.3182 | -81.7278 | 9,580 | 16.0 | 92.2 |
| S3 | I-295 Exit 10, Duval County | I-295 W between Buckman Bridge and US-17 | 30.1918 | -81.6975 | 6,849 | 11.4 | 97.7 |
| S4 | I-75 Exit 435, Columbia County | I-75 at ramp to I-10 | 30.2733 | -82.7582 | 6,411 | 10.7 | 77.5 |
| S5 | I-10 Exit 283, Suwannee County | I-10 at US-129 | 30.3332 | -82.9664 | 5,757 | 9.6 | 32.3 |
| S6 | I-95 Exit 366, Duval County | I-95 at ramp from Pecan Park Rd | 30.5222 | -81.6357 | 5,478 | 9.1 | 86.2 |
| S7 | I-75 Exit 384, Alachua County | I-75 at ramp from SR-24/Archer Rd | 29.6220 | -82.3895 | 5,038 | 8.4 | 77.3 |
| S8 | I-75 Exit 404, Alachua County | I-75 at ramp to CR-236 | 29.8729 | -82.5424 | 4,223 | 7.0 | 85.5 |
| S9 | I-95 Exit 318, St. Johns County | I-95 at SR-16 | 29.9221 | -81.4139 | 3,384 | 5.6 | 77.7 |
| S10 | I-10 Exit 333, Baker County | I-10 at CR-125 | 30.2615 | -82.1657 | 2,987 | 5.0 | 68.9 |

*Note:* Coordinates are OpenStreetMap site locations (WGS84). Nearest incident landmark: name of the closest 1 km road cell, from the incident location descriptions.


<a id="table-6"></a>**Table 6.** Discrete-event simulation of 2024 with busy units: response to the 59,981 incidents of 2024 by layout, fleet size and unit allocation.

| Case | Stations | Units | Unit allocation | Reached ≤ 10 min (%) | ≤ 15 min (%) | ≤ 20 min (%) | ≤ 15 min, units always free (%) | Mean response (min) | 90th percentile (min) | Delayed by busy units (%) | Utilisation (%) |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Base | 10 | 10 | Equal | 0.4 | 0.6 | 0.7 | 80.7 | overloaded | overloaded | 99.4 | 108.0 |
| Base | 10 | 20 | Equal | 34.8 | 52.4 | 63.3 | 80.7 | 27.0 | 59.8 | 43.0 | 39.2 |
| Base | 10 | 20 | Proportional | 38.8 | 57.4 | 67.7 | 80.7 | 24.9 | 54.2 | 37.4 | 38.2 |
| Base | 10 | 30 | Equal | 49.0 | 71.6 | 82.3 | 80.7 | 14.3 | 30.6 | 16.8 | 23.8 |
| Base | 10 | 30 | Proportional | 52.2 | 75.1 | 85.0 | 80.7 | 13.6 | 26.3 | 11.3 | 23.5 |
| Base | 15 | 15 | Equal | 16.2 | 25.1 | 31.5 | 88.7 | 91.5 | 232.4 | 78.0 | 62.5 |
| Base | 15 | 30 | Equal | 51.3 | 72.9 | 83.1 | 88.7 | 13.5 | 26.6 | 26.7 | 23.0 |
| Base | 15 | 30 | Proportional | 57.7 | 79.2 | 88.4 | 88.7 | 11.6 | 21.4 | 17.2 | 22.4 |
| Base | 15 | 45 | Equal | 61.9 | 84.5 | 93.0 | 88.7 | 9.9 | 17.5 | 9.0 | 14.5 |
| Base | 15 | 45 | Proportional | 64.7 | 86.7 | 94.3 | 88.7 | 9.5 | 16.4 | 4.2 | 14.4 |
| Base | 20 | 20 | Equal | 33.3 | 47.6 | 56.7 | 94.2 | 34.9 | 88.3 | 61.9 | 40.8 |
| Base | 20 | 40 | Equal | 66.5 | 85.1 | 92.3 | 94.2 | 9.5 | 17.9 | 18.5 | 16.1 |
| Base | 20 | 40 | Proportional | 71.8 | 89.5 | 95.1 | 94.2 | 8.6 | 15.3 | 10.1 | 15.8 |
| Base | 20 | 60 | Equal | 74.4 | 92.0 | 96.9 | 94.2 | 7.9 | 14.2 | 5.9 | 10.4 |
| Base | 20 | 60 | Proportional | 76.4 | 93.2 | 97.1 | 94.2 | 7.8 | 13.5 | 2.1 | 10.4 |
| On-scene time halved | 10 | 20 | Proportional | 47.3 | 68.6 | 79.1 | 80.7 | 15.7 | 34.8 | 22.7 | 26.5 |
| AVL-created incidents excluded | 10 | 20 | Proportional | 48.4 | 69.8 | 79.7 | 84.4 | 17.0 | 34.9 | 22.5 | 23.1 |

*Note:* Each incident is assigned to the unit that can reach it first; a unit is busy for travel, on-scene time (logged event duration; type median where flagged) and return to its station. Utilisation above 100%: demand exceeds capacity and the queue grows through the year. Sensitivity rows: 10 stations, 20 units, proportional allocation.

*Cited in [Section 3.10](#sec-3-10).*


## Appendix C. Supplementary material

<a id="figure-s1"></a>

![Figure S1](../results/figures/FigureS1_event_types.png)

**Figure S1.** Frequency of all recorded event types, 2022–2024; blue bars mark the four incident types analysed.

*Cited in [Section 3.1](#sec-3-1).*

<a id="figure-s2"></a>

![Figure S2](../results/figures/FigureS2_monthly_trend.png)

**Figure S2.** Monthly number of incidents by type, January 2022 – December 2024.

*Cited in [Section 3.1](#sec-3-1).*

<a id="figure-s3"></a>

![Figure S3](../results/figures/FigureS3_hourly_profile_by_type.png)

**Figure S3.** Hourly distribution of incidents within each type (% of the type's total).

*Cited in [Section 3.2](#sec-3-2).*

<a id="figure-s4"></a>

![Figure S4](../results/figures/FigureS4_routes_by_type.png)

**Figure S4.** Incidents by route and type for the eight routes with the most incidents, 2022–2024.


<a id="figure-s5"></a>

![Figure S5](../results/figures/FigureS5_hotspot_persistence.png)

**Figure S5.** Number of years (2022, 2023, 2024) in which each cell was a Gi* hot spot (q < 0.05).

*Cited in [Section 3.6](#sec-3-6).*

<a id="figure-s6"></a>

![Figure S6](../results/figures/FigureS6_sensitivity.png)

**Figure S6.** Sensitivity of the static layout (10 stations, 15-minute standard): coverage within 15 minutes and base-case stations retained under alternative speeds, demand definitions and travel-time models; the two cell-based travel-time models use road cells as candidate sites, so shared stations are not reported for them.

<a id="figure-s7"></a>

![Figure S7](../results/figures/FigureS7_rate_hotspots.png)

**Figure S7.** Getis-Ord Gi* hotspots of incident rates per million vehicle-km (empirical Bayes-smoothed), 2022–2024 (binary weights within 2 km; Benjamini–Hochberg q-values). Open squares: cells without matched AADT segments. (a) FDOT District 2; (b) Jacksonville; cluster IDs R1–R4.

*Cited in [Section 3.6](#sec-3-6).*

<a id="figure-s8"></a>

![Figure S8](../results/figures/FigureS8_precipitation.png)

**Figure S8.** Incident rate ratios for three-hour windows with vs without precipitation at the nearest NOAA station, by incident type and precipitation total in the window. Mantel–Haenszel estimates stratified by window of day, month and day type, with 95% confidence intervals; logarithmic scale.

*Cited in [Section 3.5](#sec-3-5).*

<a id="figure-s9"></a>

![Figure S9](../results/figures/FigureS9_site_robustness.png)

**Figure S9.** Share of re-solved layouts (10 stations, 15-minute standard) that select each candidate site: 200 bootstrap resamples of 2022–2023 days, 2022 and 2023 alone, and seven speed and demand scenarios. Triangles: recommended stations S1–S10. (a) FDOT District 2; (b) Jacksonville.

*Cited in [Section 3.9](#sec-3-9).*


<a id="table-s1"></a>**Table S1.** Completeness and variability of candidate explanatory variables (incidents, n = 173,198).

| Indicator | Share of incidents (%) |
| --- | ---: |
| Severity recorded as "minor" | 99.9 |
| Road surface "Dry" | 98.8 |
| Weather "Clear" | 98.3 |
| Weather "Clear" in three-hour windows with NOAA-recorded precipitation (n = 17,323) | 94.9 |
| Lighting code 16 (code meaning undocumented) | 91.7 |
| Mile marker missing | 53.0 |
| Created by the `avlrrsubsystem` account | 49.8 |
| Duration > 24 h (flagged) | 2.3 |
| Duration < 1 min (flagged) | 0.7 |
| Dark at time of incident (solar elevation below −6°) | 21.7 |
| Near-duplicate (same route and direction, ≤ 0.5 km, ≤ 15 min) | 1.8 |

*Cited in [Section 2.3](#sec-2-3), [Section 2.5](#sec-2-5).*


<a id="table-s2"></a>**Table S2.** Rate hotspot clusters: contiguous Gi* hot cells (q < 0.05) on incidents per million vehicle-km, named after their busiest cell, 2022–2024.

| ID | Hotspot location | Routes | Size (1 km cells) | Incidents per year | Million vehicle-km per year | Incidents per million vehicle-km | Crash share (%) | Max Gi* z | Overlaps a count hotspot (Table 2) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| R1 | I-295 W at Buckman Bridge (Duval County) | I-295 W | 3 | 649 | 103.4 | 6.28 | 10.4 | 3.81 | Yes |
| R2 | I-10 at ramp from CR-229 (Baker County, MM 326) | I-10 | 1 | 59 | 10.0 | 5.94 | 10.1 | 3.62 | No |
| R3 | I-75 (Columbia County, MM 417) | I-75 | 5 | 511 | 89.1 | 5.73 | 7.6 | 10.45 | No |
| R4 | I-295 E at Baymeadows Rd (Duval County, MM 57) | 295 East Express, I-295 E | 6 | 356 | 170.1 | 2.09 | 27.1 | 5.35 | No |

*Note:* Rates are cluster totals (incidents ÷ vehicle-km). Gi* used empirical Bayes-smoothed cell rates for the 944 cells with exposure data.

*Cited in [Section 3.6](#sec-3-6).*


<a id="table-s3"></a>**Table S3.** LightGBM input ablation, day-ahead forecasts for 2024; mean ± s.d. over five seeds.

| LightGBM inputs | Runs | Poisson deviance (×10⁻²) | Hit rate, top 5% cells (%) | PAI | Deviance difference vs day-ahead model (×10⁻², 95% CI) |
| --- | ---: | --- | ---: | ---: | --- |
| Base inputs only (no AADT, no precipitation) | 5 | 13.256 ± 0.011 | 23.59 | 4.64 | -0.011 (-0.012 to -0.009) |
| Base inputs + AADT exposure | 5 | 13.264 ± 0.013 | 23.58 | 4.64 | -0.002 (-0.003 to -0.001) |
| Base inputs + AADT exposure + previous-day precipitation (day-ahead model) | 5 | 13.266 ± 0.006 | 23.59 | 4.64 | — |
| As above + observed precipitation in the target window (perfect-forecast bound) | 5 | 13.253 ± 0.007 | 23.63 | 4.65 | -0.014 (-0.016 to -0.012) |

*Note:* Differences: day-level bootstrap (2,000 resamples) of mean daily deviance, seed-averaged predictions.

*Cited in [Section 3.7](#sec-3-7).*


<a id="table-s4"></a>**Table S4.** Temporal validation of the static layout (10 stations, 15-minute standard): sites selected on one period and evaluated on the following year.

| Sites selected on | Evaluated on | Covered ≤ 15 min (%) | Layout optimised on the evaluation year (%) | Sites shared with that layout | Sites shared with the recommended layout |
| --- | --- | ---: | ---: | ---: | ---: |
| 2022 | 2023 | 81.4 | 81.3 | 5 of 10 | 10 of 10 |
| 2023 | 2024 | 80.5 | 80.6 | 6 of 10 | 5 of 10 |
| 2022–2023 | 2024 | 80.7 | 80.6 | 7 of 10 | 10 of 10 |

*Note:* The layout optimised on the evaluation year uses that year's incidents and is shown for reference.

*Cited in [Section 3.9](#sec-3-9).*


<a id="table-s5"></a>**Table S5.** Robustness of the recommended station sites: share of re-solved layouts that select the site, or any candidate site within 5 km of it.

| ID | Station site | Selected, demand resamples (%) | Site within 5 km selected, demand resamples (%) | Selected, all re-solved layouts (%) | Site within 5 km selected, all layouts (%) |
| --- | --- | ---: | ---: | ---: | ---: |
| S1 | I-295 Exit 54, Duval County | 20.5 | 58.5 | 20.1 | 59.3 |
| S2 | I-10 Exit 358, Duval County | 34.0 | 91.5 | 33.5 | 91.9 |
| S3 | I-295 Exit 10, Duval County | 33.0 | 33.0 | 33.5 | 34.0 |
| S4 | I-75 Exit 435, Columbia County | 100.0 | 100.0 | 100.0 | 100.0 |
| S5 | I-10 Exit 283, Suwannee County | 100.0 | 100.0 | 99.0 | 99.0 |
| S6 | I-95 Exit 366, Duval County | 71.0 | 71.0 | 70.3 | 70.3 |
| S7 | I-75 Exit 384, Alachua County | 100.0 | 100.0 | 97.6 | 99.0 |
| S8 | I-75 Exit 404, Alachua County | 100.0 | 100.0 | 99.5 | 99.5 |
| S9 | I-95 Exit 318, St. Johns County | 82.5 | 82.5 | 80.9 | 81.3 |
| S10 | I-10 Exit 333, Baker County | 67.5 | 68.5 | 66.0 | 67.9 |

*Note:* Demand resamples: 200 bootstrap samples of 2022–2023 days. All re-solved layouts: the 200 resamples, 2022 and 2023 alone, four speed scenarios and three demand definitions (209 layouts).

*Cited in [Section 3.9](#sec-3-9).*


<a id="table-s6"></a>**Table S6.** Coverage of 2024 incidents within 15 minutes under alternative travel speeds: the recommended layout compared with the layout optimised for each speed scenario.

| Travel-speed scenario | Recommended layout, covered ≤ 15 min (%) | Layout optimised for the scenario (%) | Difference (percentage points) | Sites shared |
| --- | ---: | ---: | ---: | ---: |
| Base case | 80.7 | 80.7 | 0.0 | 10 of 10 |
| Peak speed 50% of off-peak | 74.5 | 75.1 | 0.5 | 5 of 10 |
| Peak speed 83% of off-peak | 84.8 | 85.3 | 0.4 | 4 of 10 |
| Off-peak speeds −15% | 72.7 | 73.2 | 0.6 | 3 of 10 |
| Off-peak speeds +15% | 86.5 | 85.9 | -0.6 | 4 of 10 |

*Note:* Layouts are optimised on road-edge midpoints and evaluated at exact incident locations, so a scenario-optimised layout can score slightly below the recommended layout (negative difference).

*Cited in [Section 3.9](#sec-3-9).*


<a id="table-s7"></a>**Table S7.** Hyperparameter tuning of the deep learning models on the validation period (1 October – 31 December 2023), one seed per configuration, at most 30 epochs with early stopping (patience 3).

| Model | Hidden size | Learning rate | Validation deviance (×10⁻²) | Epochs to best | Parameters |
| --- | ---: | ---: | ---: | ---: | ---: |
| LSTM (no graph) | 32 | 0.001 | **13.6037** | 8 | 40,609 |
| LSTM (no graph) | 64 | 0.001 | 13.6060 | 10 | 87,297 |
| LSTM (no graph) | 32 | 0.0003 | 13.6484 | 1 | 40,609 |
| LSTM (no graph) | 64 | 0.0003 | 13.6571 | 4 | 87,297 |
| Graph WaveNet | 32 | 0.001 | 13.6014 | 8 | 61,645 |
| Graph WaveNet | 64 | 0.001 | **13.6009** | 8 | 175,245 |
| Graph WaveNet | 32 | 0.0003 | 13.6256 | 12 | 61,645 |
| Graph WaveNet | 64 | 0.0003 | 13.6333 | 4 | 175,245 |
| ST-Transformer | 32 | 0.001 | **13.6056** | 8 | 53,409 |
| ST-Transformer | 64 | 0.001 | 13.6125 | 8 | 137,473 |
| ST-Transformer | 32 | 0.0003 | 13.6374 | 4 | 53,409 |
| ST-Transformer | 64 | 0.0003 | 13.6357 | 1 | 137,473 |

*Note:* Bold: lowest validation deviance for each model. Differences below 0.1% were treated as ties and the smaller configuration (hidden size 32, learning rate 10⁻³) was retained for all three models.

*Cited in [Section 2.8](#sec-2-8), [Section 3.7](#sec-3-7).*
