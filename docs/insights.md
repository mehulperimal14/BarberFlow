# Business Insights Report: BarberFlow

Findings from the **simulated** BarberFlow dataset: 50 shops, 5,000 customers, 64,991 visits, 2026-06-01 to 2026-08-30.
Every number below can be reproduced with `sql/analysis_queries.sql` or the `/api/analytics/*` endpoints.
Because the data comes from `scripts/generate_data.py`, these insights describe the simulated market. They demonstrate the analysis method, not real-world behaviour.

---

## Insight 1: Demand is concentrated in evenings and weekends
* **Evidence**
  * 16:00–18:59 accounts for **58.7%** of all arrivals (about 19.5% in each of those hours, query #4).
  * Saturday has **14,513** visits against **5,493** on Monday (2.6×). Friday to Sunday is **57.6%** of the volume (query #5).
  * The average wait rises from **5.4 min on Mondays to 33.0 min on Saturdays**, and from about 0.5 min at 08:00 to about 55 min after 19:00.
* **Recommendation:** schedule barbers by hour and weekday. Use off-peak offers on Monday and Tuesday mornings to shift flexible demand.

## Insight 2: The average wait hides a very skewed distribution
* **Evidence**
  * The mean wait is **19.0 min**, but the **median is 0 min**. **76.4%** of visits have no wait, while **14.9%** wait more than 30 minutes (p90 = 62 min).
  * The 16 *Bottleneck* shops (2–3 seats) average **52.7 min**. Every other shop type averages ≤ 3.1 min.
* **Recommendation:** report the median and p90 wait, not just the mean. Target capacity fixes at the bottleneck shops, adding a barber at peak hours before adding chairs, rather than making market-wide changes.

## Insight 3: Long waits come with lower ratings
* **Evidence:** each review is matched to the reviewer's visit (query #16, one visit per review). The average rating is **4.44★ after no wait** and **3.47★ after waits over 25 minutes**, a 22% drop. The wait-experience sub-rating falls from 4.75 to 2.0.
* **Caveat:** the simulator uses the wait as an input to the rating, so this confirms the pipeline recovers a built-in effect. It does not prove causation in real data.

## Insight 4: Demand outgrows capacity unevenly across neighborhoods
* **Evidence:** visits per seat (pre-aggregated, no join fan-out) against a market average of 257.9:

  | Area | Shops | Seats | Visits/seat | Avg wait | Status |
  |---|---:|---:|---:|---:|---|
  | Eastside | 12 | 45 | 357.7 | 26.3 min | High opportunity |
  | Suburbs | 7 | 29 | 319.7 | 33.3 min | High opportunity |
  | Downtown | 9 | 49 | 234.6 | 16.8 min | Balanced |
  | Westside | 10 | 55 | 226.3 | 16.4 min | Balanced |
  | Northside | 12 | 74 | 211.9 | 6.9 min | Over-saturated |
* **Recommendation:** Eastside and Suburbs are the strongest expansion candidates: high demand per seat and the longest waits.

## Insight 5: Revenue is driven by price, not by volume
* **Evidence:** each service is chosen about equally often (≈ 9.5–9.9k visits each; Premium Haircut 7,005 because Budget shops don't offer it). *Haircut + Beard* (24.5%) and *Premium Haircut* (24.4%) still generate half of the revenue, because of their price (query #9).
* **Recommendation:** bundle add-ons with high-ticket services to lift the average ticket (currently $28.14).
