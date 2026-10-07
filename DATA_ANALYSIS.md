# Data analysis: Test sales dataset

Source: `Test_sales_dataset_ecommerce_sales_dataset_.csv`. 10,000 orders, 26 columns, 2021-01-05 to 2024-12-24.


## 1. Data quality

- Missing values: 0. Duplicate rows: 0. Order IDs unique: True.

- Revenue = Unit_Price x Quantity x (1 - Discount) holds in every row: True.

- Profit = Revenue - Cost holds in every row: True. Shipping cost is therefore not deducted from profit.

- Customer_ID: 5,348 unique IDs, but one ID can appear with several segments, genders and regions (max 4 regions), so customer-level conclusions are unreliable.


## 2. Headline numbers

- Gross revenue (all orders): 5,284,387.70. Net revenue (Delivered + Processing): 3,845,611.08.

- Net profit: 1,059,850.32. Net weighted margin (profit / revenue): 27.6%. Across all orders the weighted margin is 27.2%, while the simple average of row margins is 23.6%, which understates it, so dashboards use the weighted figure.

- Order status: Delivered 6,273 (62.7%), Returned 1,857 (18.6%), Processing 962 (9.6%), Cancelled 908 (9.1%).

- Cancelled + Returned orders carry 1,438,777 of revenue (27% of gross), so net revenue is the right default KPI.


## 3. Discounts destroy margin

| Discount | orders | avg_margin_pct | loss_share_pct |
|---|---|---|---|
| 0% | 2,700.0 | 40.1 | 0.0 |
| 5% | 931.0 | 37.1 | 0.0 |
| 10% | 912.0 | 33.4 | 0.0 |
| 15% | 915.0 | 28.8 | 0.0 |
| 20% | 870.0 | 25.5 | 0.0 |
| 25% | 966.0 | 19.9 | 0.0 |
| 30% | 922.0 | 14.5 | 14.9 |
| 40% | 916.0 | 0.3 | 50.1 |
| 50% | 868.0 | -21.1 | 85.5 |

1,338 orders (13.4%) lose money. Losses begin at discounts of 30% and above.


## 4. Category and region (net)

| Category | revenue | profit | profit_share_pct |
|---|---|---|---|
| Electronics | 2,473,554.9 | 686,526.4 | 64.8 |
| Home & Kitchen | 647,606.1 | 170,740.7 | 16.1 |
| Clothing | 289,369.4 | 82,015.1 | 7.7 |
| Books & Media | 275,941.9 | 76,420.3 | 7.2 |
| Beauty & Health | 159,138.6 | 44,147.8 | 4.2 |

| Region | revenue | profit | orders |
|---|---|---|---|
| North America | 981,621 | 268,759 | 1,891 |
| Middle East | 972,807 | 283,698 | 1,780 |
| Asia | 951,599 | 258,040 | 1,793 |
| Europe | 939,584 | 249,353 | 1,771 |

Electronics generates roughly two thirds of net profit. Regions are evenly balanced.


## 5. Returns and cancellations by category

| Category | returned_pct | cancelled_pct |
|---|---|---|
| Beauty & Health | 16.7 | 9.0 |
| Books & Media | 19.3 | 9.0 |
| Clothing | 20.6 | 8.6 |
| Electronics | 17.2 | 9.6 |
| Home & Kitchen | 18.9 | 9.2 |


## 6. Shipping

| Shipping_Method | avg_cost | avg_days |
|---|---|---|
| Economy | 6.1 | 11.5 |
| Express | 35.1 | 11.3 |
| Overnight | 75.1 | 11.5 |
| Standard | 12.4 | 11.4 |

Cost differs strongly by method, but delivery time is almost identical. Faster methods are not faster in this data.


## 7. Time pattern (caution)

| Year | orders |
|---|---|
| 2021 | 896 |
| 2022 | 2,687 |
| 2023 | 4,375 |
| 2024 | 2,042 |

Orders peak in 2023-10 (427) and fall to 12 in 2024-12. This looks like an artefact of how the sample was generated and should not be presented as a real business decline.
