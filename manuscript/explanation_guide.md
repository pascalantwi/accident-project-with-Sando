
## 1. Introduction

Road Rangers help drivers after crashes, breakdowns and debris on the highway. The faster they arrive, the shorter the traffic jam and the lower the chance of a second crash. So I asked two simple questions: **where should the Road Ranger stations be, and how many trucks do they need?**

When I reviewed earlier studies, I found clear gaps:

- They looked at **one highway or a few patrol beats**, never a whole district.
- They used **guessed or average demand**, not real incident records.
- They **ignored one-way travel**. On a divided highway, a truck often has to drive to the next exit to turn around.
- They assumed **a truck is always free**, even though a crash can keep it busy for an hour.
- Deep learning was judged only on prediction accuracy. **Nobody checked whether it actually helps decide where trucks should go.**

---

## 2. Methods

### Study area

![Figure 1](../results/figures/Figure1_spatial_distribution.png)

My study covers **FDOT District 2**, 18 counties in Northeast Florida. In Figure 1, the left map shows the whole district and the right map zooms into Jacksonville. Darker colours mean more incidents. You can see that incidents follow the interstates, I-95, I-10, I-75 and the I-295 beltway, and that **the darkest areas are in central Jacksonville**. In fact, **14 of the 15 busiest 1 km squares are there**.

### Data

I worked with **three years of Road Ranger incident records (2022–2024)**. The raw file had **9.2 million rows**, because every update to an incident was saved as a new row. I combined these into **173,198 incidents** and kept the four types Road Rangers handle: disabled vehicles, crashes, debris and abandoned vehicles.

I then added three outside sources:

- **traffic volumes** from FDOT
- **rainfall** from NOAA weather stations
- **a real road map** from OpenStreetMap that knows one-way roads and exits

I divided the district into **983 squares of 1 km** and each day into **3-hour blocks**.

### My framework

![Figure 2](../results/figures/Figure2_framework.png)

Figure 2 shows my four steps. Data goes in on the left. Then I:

1. **find the hotspots**
2. **forecast incidents**, the deep learning part, shown in blue
3. **choose station locations**
4. **test everything on 2024**, a year the models had never seen

Along the way I calculated the **risk per vehicle** in each square, matched every incident to **rainfall**, and used **307 real exits, rest areas and service plazas** as possible station sites. To make sure the results are reliable, I changed the speed assumptions, tested on other years and re-solved the problem **200 times**. Finally, I simulated all of 2024 with **trucks that can be busy**.

---

## 3. Results

### Most incidents are breakdowns, but crashes take the longest

| Type | Share | Typical duration |
| --- | ---: | ---: |
| Disabled vehicle | 58.9% | 13 min |
| Crash | 25.5% | 57 min |
| Debris | 9.8% | 13 min |
| Abandoned vehicle | 5.8% | 5 min |

Table 1 shows that **most incidents are breakdowns**, but **crashes last the longest, almost an hour**. The numbers are steady at about **57,000–60,000 incidents a year**.

### Weekday afternoons are the busiest time

![Figure 3](../results/figures/Figure3_hour_by_weekday.png)

Figure 3 shows average incidents per hour. On weekdays there is a morning peak around 8 am and a **bigger afternoon peak from 3 to 6 pm**. Weekends are calmer and have no morning peak. **The single busiest hour is Friday 3–4 pm, with about 15 incidents per hour.**

### A few places carry much of the load

![Figure 4](../results/figures/Figure4_top_hotspot_cells.png)

Figure 4 lists the 15 busiest squares. **The busiest is I-295 near the Buckman Bridge, with over 500 incidents a year.** Almost all of them are in Jacksonville. Only one, on I-75 in Alachua County, is outside. Overall, **just 15% of the squares hold half of all incidents.**

### Crashes keep a truck busy

![Figure 5](../results/figures/Figure5_event_duration.png)

Figure 5 compares durations. **Almost half of all crashes last more than one hour**, while abandoned vehicles are usually cleared in about 5 minutes. This matters later, because a truck at a crash cannot respond to anything else.

### Rain increases crashes, and the logs miss it

![Figure S8](../results/figures/FigureS8_precipitation.png)

Figure S8 shows how much more often incidents happen in rain; a value above 1 means more. **Crashes rise with rain, and the heavier the rain, the bigger the increase, up to about 70% in heavy rain.** Breakdowns actually go down slightly. I also found that **the incident logs said "clear weather" 95% of the time even when it was raining**, so that field cannot be trusted.

### The hotspots are stable

![Figure 6](../results/figures/Figure6_hotspots.png)

In Figure 6 the red squares are statistically significant hotspots. I found **8 hotspot clusters, all in Jacksonville**. The two biggest (Table 2) are **H1, I-95 at the ramp to I-10**, and **H2, I-295 at the Buckman Bridge**. Most importantly, **31 of the 35 hot squares were hot in all three years**. The hotspots don't move, so planning from past records makes sense.

When I adjusted for traffic volume (Figure S7, Table S2), **different places appeared, including rural I-10 in Baker County and I-75 in Columbia County**. So **count hotspots show where trucks are needed, and risk hotspots show where road safety improvements are needed.**

### Deep learning did not win

| Model | Forecast error (lower is better) |
| --- | ---: |
| Poisson log-linear (simple) | 13.259 |
| LightGBM (machine learning) | 13.266 |
| Graph WaveNet (deep learning) | 13.327 |
| LSTM (deep learning) | 13.329 |
| ST-Transformer (deep learning) | 13.343 |
| Historical average | 14.471 |

![Figure 7](../results/figures/Figure7_forecast_performance.png)

Table 3 and Figure 7 compare the forecasting models. **The three deep learning models were about 0.5% worse than the simpler models**, in every time of day. Tuning them (Table S7) didn't change this. Incidents are rare and follow regular patterns, so **simple models already capture what can be predicted**. Figure 7b shows the predictions still match reality well, closely following the diagonal.

### Smart placement beats intuition

![Figure 8](../results/figures/Figure8_coverage.png)

Figure 8 shows that adding stations helps, but each extra station adds less. **Moving trucks every day based on forecasts gave almost the same result as fixed stations.**

| Layout (10 stations) | Incidents reached within 15 minutes |
| --- | ---: |
| **My optimised stations** | **80.7%** |
| Random sites | 52.7% |
| Stations at the busiest spots | 47.1% |
| Moving trucks daily, any forecast | 80.5–80.6% |
| Moving trucks daily, perfect knowledge | 91.3% |

Table 4 is one of my main findings. **Putting stations at the busiest spots is the worst option.** They all end up in Jacksonville and the rural highways are left uncovered.

![Figure 9](../results/figures/Figure9_stations.png)

Figure 9 shows my **10 recommended stations** (red triangles), and Table 5 lists them by exit, for example **I-295 Exit 54, I-10 Exit 358 and I-75 Exit 435**. Together they **reach about 81% of incidents within 15 minutes**.

### The results are reliable

![Figure S9](../results/figures/FigureS9_site_robustness.png)

I re-solved the problem **209 times** with different data and assumptions. In Figure S9, bigger circles mean a site was chosen more often. **The rural stations on I-75 and I-10 were chosen almost every time, so they are firm recommendations.** In Jacksonville the exact exit changes, but **the area stays the same**. Stations chosen with 2022 data still worked just as well in 2023 (Table S4). Across all speed assumptions, coverage stayed between **73% and 86%** (Figure S6).

### One truck per station is not enough

![Figure 10](../results/figures/Figure10_simulation.png)

Figure 10 and Table 6 show what happens when trucks can be busy. **With only one truck per station, the system is overloaded and almost no incident is reached in time.** With **two to three trucks per station**, coverage gets close to the ideal; for example, **20 stations with 60 trucks reach 93%**. Giving busier stations more trucks improves coverage at no extra cost.

---

## 4. What it means

- **Use incident counts to place trucks, and risk per vehicle to plan safety improvements.**
- **Simple forecasting models are enough for planning.** Deep learning is better kept for real-time operations with live traffic data.
- **Station locations and the number of trucks must be planned together.**

My study also has limitations:

- **couldn't compare with the current Road Ranger stations**, because FDOT hasn't shared those locations.
- About **half the incidents were logged by Road Rangers while patrolling**, so patrolled areas may look busier.
- **Travel speeds come from speed limits**, not measured speeds.
- I studied **only one district**.

## 5. Conclusion

**Put Road Ranger stations in the right places across the whole district, not only at the busiest spots, and give each station two to three trucks. FDOT can plan this with the data it already has.**
