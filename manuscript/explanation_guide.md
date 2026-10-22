# Explanation guide: section by section, with figures and tables

A plain-language guide for presenting the study. For each section: what we did, then each figure or table with **What it shows**, **What to say** and the **Key number** to remember.

---

## 1. Introduction: the problem and the gap

**What to say:** "Road Rangers help after crashes, breakdowns and debris on the highway. The faster they arrive, the shorter the traffic jam and the lower the chance of a second crash. So we ask two questions: where should the stations be, and how many trucks are needed?"

**The gap, in simple words:**
- Earlier studies covered one highway or a few patrol beats, not a whole district.
- They used guessed or average demand, not real incident records.
- They ignored one-way travel: on a divided highway you often drive to the next exit to turn around.
- They assumed a truck is always free.
- Deep learning was tested only for prediction accuracy, never for whether it helps decide where trucks go.

---

## 2. Methods: what we did

### 2.1 Study area: Figure 1

![Figure 1](../results/figures/Figure1_spatial_distribution.png)

- **What it shows:** where all incidents happened in FDOT District 2 (left) and a close-up of Jacksonville (right). Darker colour means more incidents. Red circles are the busiest 1 km squares.
- **What to say:** "Incidents follow the interstates: I-95, I-10, I-75 and the I-295 beltway. The darkest areas are in central Jacksonville."
- **Key number:** 14 of the 15 busiest squares are in central Jacksonville.

### 2.2–2.3 Data and cleaning

- **What to say:** "We used three years of Road Ranger incident records, 2022–2024. The raw file had a row for every update to an incident, so we combined them into one record per incident. We kept the four types Road Rangers handle: disabled vehicles, crashes, debris and abandoned vehicles. We added traffic volumes from FDOT, rainfall from NOAA and a real road map from OpenStreetMap."
- **Key numbers:** 9.2 million log rows became 173,198 incidents; 983 squares of 1 km; 3-hour time blocks.

### 2.4 Research framework: Figure 2

![Figure 2](../results/figures/Figure2_framework.png)

- **What it shows:** the four steps of the study.
- **What to say:** "Data goes in on the left. Then we (1) find hotspots, (2) forecast incidents, the deep learning part in blue, (3) choose station locations, and (4) evaluate everything on 2024 data the models never saw."

### 2.5–2.11 Methods in one line each

| Step | In simple words |
| --- | --- |
| 2.5 Exploring the data | Counted incidents by type, time, place and duration |
| 2.6 Extra data | Vehicles passing each square (for risk per vehicle), rainfall per 3 hours, road map with one-way roads; 307 real exits, rest areas and service plazas as possible station sites |
| 2.7 Hotspots | A statistical test (Getis-Ord Gi*) finds squares with unusually many incidents, corrected so we don't get false alarms |
| 2.8 Forecasting | Predicted tomorrow's incidents with three simple models and three deep learning models |
| 2.9 Station locations | An optimisation model picks the sites that reach the most incidents within 10, 15 or 20 minutes |
| 2.10 Checks | Changed speeds and data definitions, tested on other years, re-solved 200 times |
| 2.11 Busy-truck simulation | Replayed all of 2024 with trucks that are busy while driving, working the scene and returning |

---

## 3. Results: what we found

### 3.1 Incident characteristics: Table 1

| Type | Share | Typical duration |
| --- | ---: | ---: |
| Disabled vehicle | 58.9% | 13 min |
| Crash | 25.5% | 57 min |
| Debris | 9.8% | 13 min |
| Abandoned vehicle | 5.8% | 5 min |

- **What it shows:** how many incidents of each type, by year, and how long they last.
- **What to say:** "Most incidents are breakdowns, but crashes last the longest, about an hour. Numbers are similar each year."
- **Key number:** 173,198 incidents; about 57,000–60,000 per year.

### 3.2 Time patterns: Figure 3

![Figure 3](../results/figures/Figure3_hour_by_weekday.png)

- **What it shows:** average incidents per hour for each hour and day. Darker means more.
- **What to say:** "Weekdays have a morning peak around 8 am and a bigger afternoon peak from 3 to 6 pm. Weekends are calmer, with no morning peak."
- **Key number:** busiest hour is Friday 3–4 pm, about 15 incidents per hour.

### 3.3 Busiest locations: Figure 4

![Figure 4](../results/figures/Figure4_top_hotspot_cells.png)

- **What it shows:** the 15 busiest 1 km squares, with incidents per year and the share that are crashes.
- **What to say:** "The busiest spot is I-295 near the Buckman Bridge, with over 500 incidents a year. Most top spots are in Jacksonville. Only one is outside, on I-75 in Alachua County."
- **Key number:** 15% of squares hold half of all incidents.

### 3.4 Event duration: Figure 5

![Figure 5](../results/figures/Figure5_event_duration.png)

- **What it shows:** how long incidents last, by type. The box is the middle half of incidents.
- **What to say:** "Crashes last much longer than other incidents. Almost half of crashes last more than one hour, which keeps a truck busy."
- **Key number:** crash median 57 minutes; abandoned vehicles 5 minutes.

### 3.5 Rain and incidents: Figure S8

![Figure S8](../results/figures/FigureS8_precipitation.png)

- **What it shows:** how much more often incidents happen when it rains. A value of 1 means no change; above 1 means more.
- **What to say:** "Crashes go up when it rains, and the heavier the rain, the bigger the increase. Breakdowns actually go down slightly. Also, the incident logs said 'clear weather' 95% of the time even when it was raining, so that field can't be trusted."
- **Key number:** heavy rain makes crashes about 1.7 times as likely (+70%).

### 3.6 Hotspots: Figure 6 and Table 2

![Figure 6](../results/figures/Figure6_hotspots.png)

- **What it shows:** squares with significantly more incidents than their surroundings (red). Clusters labelled H1–H8.
- **What to say:** "We found 8 hotspot clusters, all in Jacksonville. The two biggest are H1, I-95 at the ramp to I-10, and H2, I-295 at the Buckman Bridge. 31 of the 35 hot squares were hot in all three years, so the hotspots are stable."
- **Table 2:** lists each cluster with its location, incidents per year, crash share and risk per million vehicle-km.
- **Supplementary:** Figure S7 and Table S2 show hotspots by risk per vehicle. "When we account for traffic volume, different places appear, including rural I-10 in Baker County and I-75 in Columbia County. Count hotspots tell us where trucks are needed; risk hotspots tell us where road safety improvements are needed."
- **Key numbers:** 35 hot squares (3.6%) hold 13.1% of incidents; 88.6% stayed hot every year.

### 3.7 Forecasting: Table 3 and Figure 7

| Model | Error (deviance, lower is better) |
| --- | ---: |
| Poisson log-linear (simple) | 13.259 |
| LightGBM (machine learning) | 13.266 |
| Graph WaveNet (deep learning) | 13.327 |
| LSTM (deep learning) | 13.329 |
| ST-Transformer (deep learning) | 13.343 |
| Historical average | 14.471 |

![Figure 7](../results/figures/Figure7_forecast_performance.png)

- **What it shows:** Table 3 compares forecast error. In Figure 7, (a) shows deep models are slightly worse than LightGBM in every time block, and (b) shows predicted versus actual incidents per square, which lie close to the diagonal.
- **What to say:** "Deep learning did not beat the simpler models. Incidents are rare and follow regular patterns, so the simple models already capture what can be predicted. We also tuned the deep models (Table S7) and it didn't change the result."
- **Key number:** deep models were about 0.5% worse than LightGBM.

### 3.8 Station locations: Figures 8 and 9, Tables 4 and 5

![Figure 8](../results/figures/Figure8_coverage.png)

- **Figure 8, what it shows:** the share of incidents reached in time as we add stations, for 10, 15 and 20 minutes.
- **What to say:** "More stations reach more incidents, but each extra station adds less. Moving trucks daily using forecasts (blue) gives almost the same result as fixed stations (orange)."

**Table 4 (10 stations, reached within 15 minutes):**

| Layout | Reached |
| --- | ---: |
| Optimised fixed stations | 80.7% |
| Random sites | 52.7% |
| Stations at the busiest spots | 47.1% |
| Daily moving, any forecast | 80.5–80.6% |
| Daily moving with perfect knowledge | 91.3% |

- **What to say:** "Putting stations at the busiest spots is the worst option, because they all end up in Jacksonville and rural highways are left uncovered."

![Figure 9](../results/figures/Figure9_stations.png)

- **Figure 9, what it shows:** the 10 recommended stations (red triangles); blue squares can be reached within 15 minutes.
- **Table 5:** lists the 10 stations by exit number, e.g. S1 I-295 Exit 54, S2 I-10 Exit 358, S4 I-75 Exit 435.
- **Key number:** 10 stations reach about 81% of incidents within 15 minutes.

### 3.9 Robustness checks: Figure S6, Figure S9, Tables S4–S6

![Figure S9](../results/figures/FigureS9_site_robustness.png)

- **What it shows:** how often each site is chosen when we re-solve the problem 209 times with different data and assumptions. Bigger circle means chosen more often.
- **What to say:** "The rural stations on I-75 and I-10 were chosen almost every time, so they are firm. In Jacksonville the exact exit changes, but the area stays the same. Stations chosen with 2022 data still worked well in 2023 (Table S4)."
- **Key numbers:** coverage stayed between 73% and 86% across speed assumptions (Figure S6); the recommended layout loses at most 0.55 points compared with the best layout for each scenario (Table S6).

### 3.10 Busy trucks: Table 6 and Figure 10

![Figure 10](../results/figures/Figure10_simulation.png)

- **What it shows:** the share of incidents reached within 15 minutes when trucks can be busy, by number of trucks. Dotted lines are the result if trucks were always free.
- **What to say:** "With only one truck per station the system is overloaded. With two to three trucks per station, we get close to the ideal. Giving busier stations more trucks helps for free."
- **Key numbers (Table 6):** 10 stations with 10 trucks: 0.6%; with 30 trucks: 75%; 20 stations with 60 trucks: 93%.

---

## 4. Discussion: what it means

- **Place trucks by counts, fix roads by risk:** count hotspots show where trucks are needed; risk-per-vehicle hotspots show where safety improvements are needed.
- **Deep learning:** not needed for planning stations; better for real-time use with live traffic data.
- **Plan together:** decide station locations and number of trucks at the same time.
- **Limitations:**
  - no comparison with current Road Ranger stations yet (FDOT data needed)
  - half the incidents were logged by patrolling Road Rangers, so patrolled areas may look busier
  - speeds come from speed limits, not measured speeds
  - only one district studied

## 5. Conclusion: the one message

"Put Road Ranger stations in the right places across the whole district, not only at the busiest spots, and give each station two to three trucks. FDOT can plan this with the data it already has."
