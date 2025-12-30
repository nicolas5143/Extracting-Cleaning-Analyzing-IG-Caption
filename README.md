# CS Competition Analytics Dashboard

An end-to-end data engineering and analytics project that aggregates, extracts, and visualizes student competition data from Instagram.

**Data Source:** [@csrelatedcompetitions](https://www.instagram.com/csrelatedcompetitions/)  

---

## Project Overview

finding relevant student competitions (Hackathons, Business Cases, Olympiads) is often difficult because information is scattered across social media images. 

This project solves that problem by building an automated pipeline that:
1.  **Scrapes** raw posts (captions) from Instagram.
2.  **Extracts** structured data (Fees, Category, Audience) from unstructured text using Large Language Models.
3.  **Cleans & Enriches** the data (Currency parsing, Category standardization).
4.  **Visualizes** market trends via an interactive **Streamlit** dashboard.

---

## Dashboard Features

The dashboard allows users to explore the competition market with the following features:

* **Timeline Analysis:** See when competitions are most frequently published.
* **IT vs. Non-IT Analysis:** A dedicated section comparing technical (Coding, AI) vs. general (Business, Essay) competitions.
* **Price Analysis:** Distribution of Free vs. Paid events and average registration fees.
* **Smart Filters:** Filter data by date range with a one-click reset option.

---

## Tech Stack

* **Python:** Core programming language.
* **LLM / AI:** `Groq API` for high-speed data extraction.
* **Data Processing:** `Pandas` for cleaning and manipulation.
* **Visualization:** `Streamlit` (UI) and `Plotly` (Charts).
* **Environment:** `Dotenv` for API security.

---

## How to Run Locally

Since this dashboard relies on the processed dataset (`competition_data.csv`), you can run it entirely on your local machine.

### Prerequisites
* Python 3.8 or higher installed.

### Installation Steps

1.  **Clone the repository**
    ```bash
    git clone https://github.com/nicolas5143/Extracting-Cleaning-Analyzing-IG-Caption.git
    cd your-repo-name
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Dashboard**
    ```bash
    streamlit run dashboard_complete.py
    ```

4.  **View the App**
    The app will open automatically in your browser at `http://localhost:8501`.

---
