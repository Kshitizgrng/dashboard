# Global Sales Intelligence Dashboard

## Executive Summary
A full-stack data application built with **Python** and **Streamlit** to visualize global sales performance. This dashboard transforms raw CSV data into actionable insights, allowing stakeholders to track KPIs like **Total Sales**, **Profit Margins**, and **Quantity Sold** in real-time.

### 🟢 **[Click Here to Launch Live Dashboard](https://dashboard-2kvkir4bhuwfw6dudfpg3c.streamlit.app/)**

## 🛠️ Tech Stack
* **Core Logic:** Python 3.10+
* **Frontend Framework:** Streamlit
* **Data Manipulation:** Pandas
* **Visualization:** Plotly Express
* **Data Source:** CSV (Global Sales 2025 Dataset)

## Key Features

### 1. Dynamic Filtering System
* **Sidebar Controls:** Users can slice data by **Region**, **Country**, and **City** simultaneously.
* **Date Logic:** Integrated `DateInput` widgets to analyze specific fiscal periods (Q1, Q2, etc.).

### 2. Advanced Visualizations
* **KPI Scorecards:** Instant view of Top-Level Metrics (Sales, Profit, Margin).
* **Geospatial Analysis:** Interactive **Treemap** showing the hierarchy of Sales by Region $\rightarrow$ State $\rightarrow$ City.
* **Trend Analysis:** Time-series line charts tracking monthly performance.
* **Correlation:** Scatter plots identifying the relationship between Sales Volume and Profitability.

### 3. Data Accessibility
* **Raw Data View:** Built-in "Expander" allowing users to inspect the underlying dataset.
* **Export Capability:** One-click "Download CSV" feature for offline analysis.

## Setup Instructions
1. Clone the repo:
   ```bash
   git clone [https://github.com/yourusername/Sales-Intelligence-Dashboard.git](https://github.com/yourusername/Sales-Intelligence-Dashboard.git)
