import streamlit as st
import pandas as pd
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Competition Analytics", layout="wide")

# --- 1. LOAD DATA ---
@st.cache_data
def load_data():
    df = pd.read_csv(r"..\data\competition_data.csv")
    
    # Create Date Column
    df['date_full'] = pd.to_datetime(df[['year', 'month', 'day']])
    
    # --- DEFINE GROUPS (IT vs Non-IT) ---
    it_cols = [
        'cat_web_development', 'cat_ui/ux_competition', 'cat_competitive_programming', 
        'cat_cybersecurity/network', 'cat_game_development', 'cat_ai', 'cat_hackathon', 
        'cat_mobile_development', 'cat_robotic/iot', 'cat_data_science', 'cat_data_analyst', 
        'cat_smart_city', 'cat_python', 'cat_product_competition'
    ]
    
    def define_group(row):
        if row[it_cols].sum() > 0:
            return "IT Competition"
        elif row['cat_non-it_competition'] == 1:
            return "Non-IT Competition"
        else:
            return "Other"

    df['competition_group'] = df.apply(define_group, axis=1)
    
    return df

try:
    df = load_data()
except FileNotFoundError:
    st.error("File 'competition_data.csv' not found. Please put it in the same folder.")
    st.stop()

# --- SIDEBAR: GLOBAL FILTER ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "IT vs Non-IT Analysis", "About Project"])

st.sidebar.divider()
st.sidebar.header("Filters")

# --- DATE FILTER WITH RESET ---
min_date = df['date_full'].min().date()
max_date = df['date_full'].max().date()

# 1. Initialize Session State for the date picker if it doesn't exist
if 'date_range' not in st.session_state:
    st.session_state['date_range'] = (min_date, max_date)

# 2. Reset Button
if st.sidebar.button("Reset Date Filter"):
    st.session_state['date_range'] = (min_date, max_date)

# 3. The Date Input Widget (Linked to Session State)
date_range = st.sidebar.date_input(
    "Select Date Range",
    value=st.session_state['date_range'],
    min_value=min_date,
    max_value=max_date,
    key='date_range' # This links the widget to st.session_state['date_range']
)

# Handle case where user selects only one date (start date) but hasn't picked end date yet
if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

# Apply Filter
mask = (df['date_full'].dt.date >= start_date) & (df['date_full'].dt.date <= end_date)
filtered_df = df[mask]

# Show active filter range text
st.sidebar.caption(f"Showing data from: {start_date} to {end_date}")


# ==========================================
# PAGE 1: GENERAL DASHBOARD
# ==========================================
if page == "Dashboard":
    st.title("Competition Market Overview")
    
    # Metric Row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Competitions", len(filtered_df))
    col2.metric("Free Competitions", len(filtered_df[filtered_df['fee_type'] == 'Free']))
    col3.metric("Paid Competitions", len(filtered_df[filtered_df['fee_type'] == 'Paid']))
    
    # Avg Fee (Excluding -1 and 0)
    avg_fee = 0
    paid_comps = filtered_df[filtered_df['min_registration_fee'] > 0]
    if not paid_comps.empty:
        avg_fee = paid_comps['min_registration_fee'].mean()
    col4.metric("Avg. Fee (Paid Only)", f"Rp {avg_fee:,.0f}")
    
    st.divider()
    
    # ROW 1: Timeline
    st.subheader("Activity Timeline")
    # We create a copy to avoid SettingWithCopyWarning
    timeline_df = filtered_df.copy()
    timeline_df['month_year'] = timeline_df['date_full'].dt.to_period('M').astype(str)
    trend = timeline_df.groupby('month_year').size().reset_index(name='count')
    fig_trend = px.line(trend, x='month_year', y='count', markers=True, 
                        title="Competitions Published per Month")
    st.plotly_chart(fig_trend, use_container_width=True)
    
    # ROW 2: Target Audience & Post Category
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Target Audience Distribution")
        # Summing the boolean audience columns
        aud_cols = [c for c in df.columns if c.startswith('aud_') and c != 'aud_invalid']
        aud_counts = filtered_df[aud_cols].sum().reset_index()
        aud_counts.columns = ['Audience', 'Count']
        aud_counts['Audience'] = aud_counts['Audience'].str.replace('aud_', '').str.title()
        
        fig_aud = px.pie(aud_counts, names='Audience', values='Count', hole=0.4)
        st.plotly_chart(fig_aud, use_container_width=True)
        
    with c2:
        st.subheader("Post Category Distribution")
        post_counts = filtered_df['post_category'].value_counts().reset_index()
        post_counts.columns = ['Category', 'Count']
        
        fig_post = px.bar(post_counts, x='Category', y='Count', color='Category',
                          text_auto=True)
        st.plotly_chart(fig_post, use_container_width=True)

    # ROW 3: Paid/Unpaid & Top Categories
    c3, c4 = st.columns(2)
    
    with c3:
        st.subheader("Paid vs Unpaid Distribution")
        fee_counts = filtered_df['fee_type'].value_counts().reset_index()
        fee_counts.columns = ['Type', 'Count']
        fig_fee_dist = px.pie(fee_counts, names='Type', values='Count', 
                              color_discrete_map={'Free': '#2ecc71', 'Paid': '#e74c3c', 'Not listed': '#95a5a6'})
        st.plotly_chart(fig_fee_dist, use_container_width=True)

    with c4:
        st.subheader("Top 10 Specific Categories")
        cat_cols = [c for c in df.columns if c.startswith('cat_') and c != 'cat_invalid']
        cat_counts = filtered_df[cat_cols].sum().sort_values(ascending=False).head(10).reset_index()
        cat_counts.columns = ['Category', 'Count']
        cat_counts['Category'] = cat_counts['Category'].str.replace('cat_', '').str.replace('_', ' ').str.title()
        
        fig_cat = px.bar(cat_counts, x='Count', y='Category', orientation='h', 
                         color='Count', color_continuous_scale='Viridis')
        fig_cat.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_cat, use_container_width=True)

# ==========================================
# PAGE 2: IT vs NON-IT COMPARISON
# ==========================================
elif page == "IT vs Non-IT Analysis":
    st.title("IT vs. Non-IT Competitions")
    st.markdown("Comparing technical competitions against general/non-technical ones.")
    
    # Filter Data (Ignore 'Other') from the GLOBAL filtered_df
    comp_df = filtered_df[filtered_df['competition_group'].isin(["IT Competition", "Non-IT Competition"])]
    
    # 1. MARKET SHARE
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Market Share")
        group_counts = comp_df['competition_group'].value_counts().reset_index()
        group_counts.columns = ['Group', 'Count']
        fig_pie = px.pie(group_counts, names='Group', values='Count', hole=0.5, 
                         color='Group',
                         color_discrete_map={"IT Competition": "#3366CC", "Non-IT Competition": "#DC3912"})
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with c2:
        # 2. FEE COMPARISON (Box Plot)
        st.subheader("Fee Comparison (Paid Only)")
        paid_comp = comp_df[(comp_df['min_registration_fee'] > 0) & (comp_df['min_registration_fee'] < 500000)]
        fig_fee = px.box(paid_comp, x='competition_group', y='min_registration_fee', color='competition_group',
                         labels={'min_registration_fee': 'Fee (IDR)'},
                         color_discrete_map={"IT Competition": "#3366CC", "Non-IT Competition": "#DC3912"})
        st.plotly_chart(fig_fee, use_container_width=True)

    st.divider()
    
    # 3. AUDIENCE COMPARISON
    st.subheader("Target Audience Comparison")
    
    aud_cols = [c for c in df.columns if c.startswith('aud_') and c != 'aud_invalid']
    aud_grouped = comp_df.groupby('competition_group')[aud_cols].sum().reset_index()
    aud_melted = aud_grouped.melt(id_vars='competition_group', var_name='Audience', value_name='Count')
    aud_melted['Audience'] = aud_melted['Audience'].str.replace('aud_', '').str.title()
    
    fig_aud = px.bar(aud_melted, x='Audience', y='Count', color='competition_group', barmode='group',
                     color_discrete_map={"IT Competition": "#3366CC", "Non-IT Competition": "#DC3912"})
    st.plotly_chart(fig_aud, use_container_width=True)

# ==========================================
# PAGE 3: ABOUT PROJECT
# ==========================================
elif page == "About Project":
    st.title("About This Project")
    
    st.markdown("""
    ### Project Goal
    To build a comprehensive database and analytics dashboard of infromation for IT competitions in Indonesia, 
    derived from the Instagram account @csrelatedcompetition.
    
    ### The Pipeline
    This dashboard is the result of an end-to-end Data Engineering & Analysis workflow:
    
    **1. Data Collection (Scraping)**
    * **Source:** Instagram posts from user @csrelatedcompetition.
    * **Raw Data:** Caption text were scraped to gather information about various events.
    
    **2. Intelligent Extraction (LLM)**
    * **The Challenge:** Captions are unstructured text. Manually reading 1,000+ posts is impossible.
    * **The Solution:** Utilized LLM as a reasoning engine.
    * **Process:** The LLM read each caption and extracted structured fields:
        * Category (e.g., Web Dev, UI/UX)
        * Target Audience (e.g., Mahasiswa, SMA)
        * Registration Fees
        * Team Size
    
    **3. Data Cleaning & Refinement**
    * Implemented a "Self-Healing" script to handle API rate limits and parsing errors.
    * Standardized category names (aggregating "Website Design" into "Web Development").
    * Parsed financial data (converting "50k" to 50000).
    
    **4. Visualization**
    * The final data is visualized here using Streamlit and Plotly to provide actionable insights into the competition market.
    """)