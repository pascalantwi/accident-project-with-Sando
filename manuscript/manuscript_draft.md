# Locating freeway service patrol stations with deep spatio-temporal incident forecasting: a predict-then-optimise study of FDOT District 2, Northeast Florida

Pascal Antwi¹, [Co-author] Sando²
¹ [Affiliation] · ² [Affiliation] · Corresponding author: [name, email]

## 1. Introduction <a id="sec-1"></a>

## 2. Methodology <a id="sec-2"></a>

### 2.1 Study area <a id="sec-2-1"></a>
*Figures and tables: [Figure 1](#figure-1).*

### 2.2 Data <a id="sec-2-2"></a>

### 2.3 Data processing <a id="sec-2-3"></a>

### 2.4 Research framework <a id="sec-2-4"></a>
*Figures and tables: [Figure 2](#figure-2).*

### 2.5 Exploratory data analysis <a id="sec-2-5"></a>

### 2.6 Hotspot detection <a id="sec-2-6"></a>

### 2.7 Demand forecasting <a id="sec-2-7"></a>

### 2.8 Station location optimisation <a id="sec-2-8"></a>

### 2.9 Evaluation and sensitivity analysis <a id="sec-2-9"></a>

## 3. Results <a id="sec-3"></a>

### 3.1 Incident characteristics <a id="sec-3-1"></a>
*Figures and tables: [Table 1](#table-1); [Figure S1](#figure-s1); [Figure S2](#figure-s2).*

### 3.2 Temporal patterns <a id="sec-3-2"></a>
*Figures and tables: [Figure 3](#figure-3); [Figure S3](#figure-s3).*

### 3.3 Spatial distribution and concentration <a id="sec-3-3"></a>
*Figures and tables: [Figure 1](#figure-1); [Figure 4](#figure-4); [Figure S4](#figure-s4).*

### 3.4 Event duration <a id="sec-3-4"></a>
*Figures and tables: [Figure 5](#figure-5).*

### 3.5 Data quality <a id="sec-3-5"></a>
*Figures and tables: [Table S1](#table-s1).*

### 3.6 Hotspots <a id="sec-3-6"></a>
*Figures and tables: [Figure 6](#figure-6); [Table 2](#table-2); [Figure S5](#figure-s5).*

### 3.7 Forecasting performance <a id="sec-3-7"></a>
*Figures and tables: [Table 3](#table-3); [Figure 7](#figure-7).*

### 3.8 Station locations and coverage <a id="sec-3-8"></a>
*Figures and tables: [Figure 8](#figure-8); [Table 4](#table-4); [Figure 9](#figure-9); [Table 5](#table-5).*

### 3.9 Sensitivity analysis <a id="sec-3-9"></a>
*Figures and tables: [Figure S6](#figure-s6).*

## 4. Discussion <a id="sec-4"></a>

## 5. Conclusion <a id="sec-5"></a>

## References

- Benjamini, Y., Hochberg, Y., 1995. Controlling the false discovery rate: a practical and powerful approach to multiple testing. *Journal of the Royal Statistical Society: Series B* 57(1), 289–300.
- Boeing, G., 2017. OSMnx: new methods for acquiring, constructing, analyzing, and visualizing complex street networks. *Computers, Environment and Urban Systems* 65, 126–139.
- Chainey, S., Tompson, L., Uhlig, S., 2008. The utility of hotspot mapping for predicting spatial patterns of crime. *Security Journal* 21, 4–28.
- Church, R., ReVelle, C., 1974. The maximal covering location problem. *Papers of the Regional Science Association* 32, 101–118.
- Getis, A., Ord, J.K., 1992. The analysis of spatial association by use of distance statistics. *Geographical Analysis* 24(3), 189–206.
- Hakimi, S.L., 1964. Optimum locations of switching centers and the absolute centers and medians of a graph. *Operations Research* 12(3), 450–459.
- Ke, G., Meng, Q., Finley, T., et al., 2017. LightGBM: a highly efficient gradient boosting decision tree. *Advances in Neural Information Processing Systems* 30.
- Li, Y., Yu, R., Shahabi, C., Liu, Y., 2018. Diffusion convolutional recurrent neural network: data-driven traffic forecasting. *International Conference on Learning Representations (ICLR)*.
- Lundberg, S.M., Lee, S.-I., 2017. A unified approach to interpreting model predictions. *Advances in Neural Information Processing Systems* 30.
- Okabe, A., Satoh, T., Sugihara, K., 2009. A kernel density estimation method for networks, its computational method and a GIS-based tool. *International Journal of Geographical Information Science* 23(1), 7–32.
- Toregas, C., Swain, R., ReVelle, C., Bergman, L., 1971. The location of emergency service facilities. *Operations Research* 19(6), 1363–1373.
- Wu, Z., Pan, S., Long, G., Jiang, J., Zhang, C., 2019. Graph WaveNet for deep spatial-temporal graph modeling. *Proceedings of IJCAI*, 1907–1913.
- Xie, Z., Yan, J., 2008. Kernel density estimation of traffic accidents in a network space. *Computers, Environment and Urban Systems* 32(5), 396–406.
- Yu, B., Yin, H., Zhu, Z., 2018. Spatio-temporal graph convolutional networks: a deep learning framework for traffic forecasting. *Proceedings of IJCAI*, 3634–3640.
- Yuan, Z., Zhou, X., Yang, T., 2018. Hetero-ConvLSTM: a deep learning approach to traffic accident prediction on heterogeneous spatio-temporal data. *Proceedings of ACM SIGKDD*, 984–992.

---

## Appendix A. Figures

<a id="figure-1"></a>

![Figure 1](../results/figures/Figure1_spatial_distribution.png)

**Figure 1.** Spatial distribution of incidents in FDOT District 2, 2022–2024. (a) District overview; the dashed box marks panel (b). (b) Central Jacksonville; red circles mark 14 of the 15 busiest 1 km grid cells. Hexagon shading shows incident counts on a logarithmic scale.

*Cited in [Section 2.1](#sec-2-1), [Section 3.3](#sec-3-3).*

<a id="figure-2"></a>

![Figure 2](../results/figures/Figure2_framework.png)

**Figure 2.** Study framework. HA: historical average; FDR: false discovery rate; MCLP: maximal covering location problem.

*Cited in [Section 2.4](#sec-2-4).*

<a id="figure-3"></a>

![Figure 3](../results/figures/Figure3_hour_by_weekday.png)

**Figure 3.** Mean number of incidents per hour, by hour of day and day of week, 2022–2024.

*Cited in [Section 3.2](#sec-3-2).*

<a id="figure-4"></a>

![Figure 4](../results/figures/Figure4_top_hotspot_cells.png)

**Figure 4.** The 15 one-kilometre grid cells with the highest mean annual number of incidents, with incidents per year and crash share.

*Cited in [Section 3.3](#sec-3-3).*

<a id="figure-5"></a>

![Figure 5](../results/figures/Figure5_event_duration.png)

**Figure 5.** Event duration (first to last log update) by incident type; boxes show the interquartile range, whiskers the 5th–95th percentiles; logarithmic scale. Events shorter than 1 minute or longer than 24 hours excluded (n = 5,189).

*Cited in [Section 3.4](#sec-3-4).*

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

**Figure 9.** Recommended static station locations (10 stations, 15-minute standard), labelled S1–S10. Blue cells are within 15 minutes of a station at off-peak speed. (a) FDOT District 2; (b) Jacksonville.

*Cited in [Section 3.8](#sec-3-8).*

## Appendix B. Tables

<a id="table-1"></a>**Table 1.** Characteristics of incidents by type, FDOT District 2, 2022–2024.

| Incident type | n | % | 2022 | 2023 | 2024 | Median duration, min (IQR) | Weekday % | 15:00–17:59 % | AVL-created % |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Disabled vehicle | 101,933 | 58.9 | 33,260 | 32,828 | 35,845 | 13.4 (4.9–31.7) | 75.4 | 23.0 | 67.9 |
| Crash | 44,158 | 25.5 | 14,401 | 15,013 | 14,744 | 56.7 (29.9–88.2) | 77.4 | 25.3 | 4.9 |
| Debris on roadway | 16,979 | 9.8 | 5,822 | 5,529 | 5,628 | 12.8 (3.8–28.6) | 78.0 | 22.1 | 36.3 |
| Abandoned vehicle | 10,128 | 5.8 | 3,284 | 3,080 | 3,764 | 4.7 (3.0–9.9) | 75.0 | 12.5 | 86.8 |
| **All** | **173,198** | **100.0** | **56,767** | **56,450** | **59,981** | **18.9 (5.7–45.6)** | **76.2** | **22.9** | **49.8** |

*Note:* Duration excludes 5,189 flagged events (< 1 min or > 24 h). AVL-created: event created by the `avlrrsubsystem` account. IQR: interquartile range.

*Cited in [Section 3.1](#sec-3-1).*

<a id="table-2"></a>**Table 2.** Incident hotspot clusters: contiguous Gi* hot cells (q < 0.05), named after their busiest cell, 2022–2024.

| ID | Hotspot location | Routes | Size (1 km cells) | Incidents per year | Crash share (%) | Cells hot in all 3 years | Max Gi* z |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| H1 | I-95 at ramp to I-10 (Duval County) | Acosta Bridge, I-10, I-95 | 14 | 3,290 | 40.8 | 13 of 14 | 7.77 |
| H2 | I-295 W at Buckman Bridge (Duval County) | I-295 W | 11 | 2,382 | 17.1 | 11 of 11 | 6.96 |
| H3 | I-295 W at I-95S/I-295 E (Duval County, MM 1) | I-295 W | 3 | 554 | 23.6 | 2 of 3 | 4.25 |
| H4 | I-295 E at Dames Point Bridge (Duval County) | I-295 E | 3 | 409 | 17.2 | 2 of 3 | 3.69 |
| H5 | I-295 W at ramp to Normandy Blvd/SR-228 (Duval County, MM 18) | I-295 W | 1 | 287 | 32.6 | 0 of 1 | 3.37 |
| H6 | I-295 W at I-10 (Duval County, MM 20) | I-295 W | 1 | 256 | 38.3 | 1 of 1 | 3.76 |
| H7 | I-295 E at St Johns Bluff Rd/UNF (Duval County) | I-295 E | 1 | 203 | 55.3 | 1 of 1 | 4.15 |
| H8 | I-295 E at ramp to Butler Blvd EB ramp (Duval County, MM 54) | I-295 E | 1 | 185 | 37.0 | 1 of 1 | 3.26 |

*Note:* Incidents per year are summed over the cluster's cells.

*Cited in [Section 3.6](#sec-3-6).*

<a id="table-3"></a>**Table 3.** Day-ahead forecast performance on 2024 (366 days × 8 windows × 983 cells); mean ± s.d. over five seeds where applicable.

| Model | Runs | MAE (×10⁻²) | RMSE (×10⁻²) | Poisson deviance (×10⁻²) | Hit rate, top 5% cells (%) | PAI |
| --- | ---: | --- | --- | --- | --- | --- |
| Historical average | 1 | 3.796 | 15.068 | 14.471 | 23.26 | 4.57 |
| Poisson log-linear | 1 | 3.781 | 15.054 | 13.259 | 22.85 | 4.49 |
| LightGBM | 5 | 3.803 ± 0.002 | 15.043 ± 0.001 | 13.256 ± 0.011 | 23.59 ± 0.05 | 4.64 ± 0.01 |
| LSTM (no graph) | 5 | 3.825 ± 0.030 | 15.053 ± 0.005 | 13.324 ± 0.021 | 23.47 ± 0.07 | 4.61 ± 0.01 |
| Graph WaveNet | 5 | 3.814 ± 0.024 | 15.050 ± 0.002 | 13.316 ± 0.010 | 23.50 ± 0.02 | 4.62 ± 0.00 |
| ST-Transformer | 5 | 3.894 ± 0.038 | 15.060 ± 0.005 | 13.348 ± 0.019 | 23.34 ± 0.07 | 4.59 ± 0.01 |

*Note:* PAI: predictive accuracy index.

*Cited in [Section 3.7](#sec-3-7).*

<a id="table-4"></a>**Table 4.** Station layouts with 10 stations or units, evaluated on the 59,981 incidents of 2024.

| Layout (demand source) | Stations | Covered ≤ 10 min (%) | ≤ 15 min (%) | ≤ 20 min (%) | Mean travel time (min) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current Road Ranger stations | 10 | [pending] | [pending] | [pending] | [pending] |
| Static stations, 2022–2023 demand (MCLP) | 10 | 75.5 | 90.8 | 97.3 | 8.6 |
| Day-ahead staging, historical average | 10 | 77.3 | 91.6 | 97.0 | 9.5 |
| Day-ahead staging, LightGBM | 10 | 77.3 | 91.7 | 97.0 | 9.4 |
| Day-ahead staging, LSTM | 10 | 77.3 | 91.6 | 97.0 | 9.4 |
| Day-ahead staging, Graph WaveNet | 10 | 77.2 | 91.5 | 97.0 | 9.4 |
| Day-ahead staging, ST-Transformer | 10 | 77.2 | 91.6 | 97.0 | 9.4 |
| Day-ahead staging, oracle (upper bound) | 10 | 93.9 | 99.1 | 99.9 | 9.1 |

*Note:* Static layouts are solved separately for each response-time standard; their mean travel time refers to the 15-minute layout.

*Cited in [Section 3.8](#sec-3-8).*

<a id="table-5"></a>**Table 5.** Recommended station locations (10 stations, 15-minute standard, 2022–2023 demand).

| ID | Station location | Latitude | Longitude | 2024 incidents nearest to station | Share of 2024 incidents (%) | Of these, reached within 15 min (%) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| S1 | SR-202 / Butler Blvd at ramp from Southside Blvd SB (Duval County) | 30.2498 | -81.5561 | 14,394 | 24.0 | 97.7 |
| S2 | SR-21 / Blanding Blvd at Wilson Blvd (Duval County) | 30.2707 | -81.7360 | 11,285 | 18.8 | 96.6 |
| S3 | I-95 at ramp to I-295 W (Duval County) | 30.4639 | -81.6482 | 6,506 | 10.8 | 89.0 |
| S4 | I-10 near MM 299 (Columbia County) | 30.2545 | -82.7169 | 6,380 | 10.6 | 87.5 |
| S5 | I-75 at SR-121 (Alachua County, MM 381) | 29.5983 | -82.3710 | 5,115 | 8.5 | 95.1 |
| S6 | I-75 near MM 407 (Alachua County) | 29.9156 | -82.5541 | 4,551 | 7.6 | 90.4 |
| S7 | I-95 at SR-16 (St. Johns County, MM 317) | 29.9133 | -81.4108 | 3,155 | 5.3 | 76.0 |
| S8 | I-10 at ramp from SR-228 (Baker County) | 30.2626 | -82.1076 | 2,926 | 4.9 | 74.5 |
| S9 | I-75 near MM 457 (Hamilton County) | 30.4915 | -83.0236 | 2,877 | 4.8 | 93.5 |
| S10 | I-10 at US-90 (Suwannee County, MM 274) | 30.3376 | -83.1080 | 2,792 | 4.7 | 66.7 |

*Note:* Coordinates are cell centroids (WGS84).

*Cited in [Section 3.8](#sec-3-8).*

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

*Cited in [Section 3.3](#sec-3-3).*

<a id="figure-s5"></a>

![Figure S5](../results/figures/FigureS5_hotspot_persistence.png)

**Figure S5.** Number of years (2022, 2023, 2024) in which each cell was a Gi* hot spot (q < 0.05).

*Cited in [Section 3.6](#sec-3-6).*

<a id="figure-s6"></a>

![Figure S6](../results/figures/FigureS6_sensitivity.png)

**Figure S6.** Sensitivity of the static layout (10 stations, 15-minute standard): coverage within 15 minutes and base-case stations retained under alternative speeds, circuity and demand definitions.

*Cited in [Section 3.9](#sec-3-9).*

<a id="table-s1"></a>**Table S1.** Completeness and variability of candidate explanatory variables (incidents, n = 173,198).

| Indicator | Share of incidents (%) |
| --- | ---: |
| Severity recorded as "minor" | 99.9 |
| Road surface "Dry" | 98.8 |
| Weather "Clear" | 98.3 |
| Lighting code 16 (code meaning undocumented) | 91.7 |
| Mile marker missing | 53.0 |
| Created by the `avlrrsubsystem` account | 49.8 |
| Duration > 24 h (flagged) | 2.3 |
| Duration < 1 min (flagged) | 0.7 |
| Dark at time of incident (solar elevation below −6°) | 21.7 |
| Near-duplicate (same route and direction, ≤ 0.5 km, ≤ 15 min) | 1.8 |

*Cited in [Section 3.5](#sec-3-5).*

---

## List of figures

- [Figure 1](#figure-1). Spatial distribution of incidents in FDOT District 2, 2022–2024.
- [Figure 2](#figure-2). Study framework.
- [Figure 3](#figure-3). Mean number of incidents per hour, by hour of day and day of week, 2022–2024.
- [Figure 4](#figure-4). The 15 one-kilometre grid cells with the highest mean annual number of incidents, with incidents per year and crash share.
- [Figure 5](#figure-5). Event duration (first to last log update) by incident type; boxes show the interquartile range, whiskers the 5th–95th percentiles; logarithmic scale.
- [Figure 6](#figure-6). Getis-Ord Gi* hotspots of incidents on 1 km road cells, 2022–2024 (binary weights within 2 km; Benjamini–Hochberg q-values).
- [Figure 7](#figure-7). Day-ahead forecast performance on 2024.
- [Figure 8](#figure-8). Share of 2024 incidents within 10, 15 and 20 minutes of the nearest station or staged unit, by number of stations or units: static layouts (2022–2023 demand), day-ahead staging from five forecasts (line: mean; band: range), and the oracle upper bound.
- [Figure 9](#figure-9). Recommended static station locations (10 stations, 15-minute standard), labelled S1–S10.
- [Figure S1](#figure-s1). Frequency of all recorded event types, 2022–2024; blue bars mark the four incident types analysed.
- [Figure S2](#figure-s2). Monthly number of incidents by type, January 2022 – December 2024.
- [Figure S3](#figure-s3). Hourly distribution of incidents within each type (% of the type's total).
- [Figure S4](#figure-s4). Incidents by route and type for the eight routes with the most incidents, 2022–2024.
- [Figure S5](#figure-s5). Number of years (2022, 2023, 2024) in which each cell was a Gi* hot spot (q < 0.05).
- [Figure S6](#figure-s6). Sensitivity of the static layout (10 stations, 15-minute standard): coverage within 15 minutes and base-case stations retained under alternative speeds, circuity and demand definitions.

## List of tables

- [Table 1](#table-1). Characteristics of incidents by type, FDOT District 2, 2022–2024.
- [Table 2](#table-2). Incident hotspot clusters: contiguous Gi* hot cells (q < 0.05), named after their busiest cell, 2022–2024.
- [Table 3](#table-3). Day-ahead forecast performance on 2024 (366 days × 8 windows × 983 cells); mean ± s.d. over five seeds where applicable.
- [Table 4](#table-4). Station layouts with 10 stations or units, evaluated on the 59,981 incidents of 2024.
- [Table 5](#table-5). Recommended station locations (10 stations, 15-minute standard, 2022–2023 demand).
- [Table S1](#table-s1). Completeness and variability of candidate explanatory variables (incidents, n = 173,198).
