import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os

# --- PART 1: DATA GENERATION (The "Digital Twin") ---
# We check if data exists. If not, we create it instantly.
def generate_data():
    if not os.path.exists('realistic_loan_book.csv'):
        # 1. RISK DATA (Real CEEW Data & Lat/Lon for Map)
        risk_data = {
            'District': ['Mumbai Suburban', 'Bengaluru Urban', 'Chennai', 'Jaipur', 'Patna', 'Gurugram', 'Hyderabad', 'Kolkata'],
            'Flood_Risk': [0.90, 0.75, 0.95, 0.20, 0.90, 0.30, 0.60, 0.85],
            'Heat_Risk':  [0.50, 0.45, 0.70, 0.98, 0.80, 0.88, 0.85, 0.60],
            'Lat': [19.07, 12.97, 13.08, 26.91, 25.59, 28.45, 17.38, 22.57],
            'Lon': [72.87, 77.59, 80.27, 75.78, 85.13, 77.02, 78.48, 88.36]
        }
        df_risk = pd.DataFrame(risk_data)
        
        # 2. LOAN DATA (Synthetic)
        loans = []
        for _ in range(200): # 200 Fake loans
            district = np.random.choice(risk_data['District'])
            # Metro logic: Higher loans in Mumbai/Bangalore
            if district in ['Mumbai Suburban', 'Gurugram']:
                prop_val = np.random.randint(80, 250) * 100000
            else:
                prop_val = np.random.randint(30, 90) * 100000
            
            loan_amt = int(prop_val * np.random.uniform(0.6, 0.85))
            
            loans.append({
                'Loan_ID': np.random.randint(10000, 99999),
                'Customer_Name': f"Cust_{np.random.randint(1,999)}",
                'District': district,
                'Property_Value': prop_val,
                'Loan_Amount': loan_amt,
                'Base_PD': np.random.uniform(0.01, 0.05) # Base Probability of Default
            })
        df_loans = pd.DataFrame(loans)
        
        # Merge and Save
        df_final = pd.merge(df_loans, df_risk, on='District')
        df_final.to_csv('realistic_loan_book.csv', index=False)
        return df_final
    else:
        return pd.read_csv('realistic_loan_book.csv')

# --- PART 2: THE DASHBOARD SETUP ---
st.set_page_config(page_title="ESG Risk Engine", layout="wide")

# Load Data
df = generate_data()

# --- PART 3: THE SIDEBAR (User Inputs) ---
st.sidebar.header("⚙️ Stress Test Parameters")
scenario = st.sidebar.radio(
    "Select Climate Scenario:",
    ("Scenario A: Mild (1.5°C)", "Scenario B: Moderate (2.0°C)", "Scenario C: Severe (3.0°C)")
)

# Set Severity based on selection
if "Scenario A" in scenario:
    severity = 0.15
elif "Scenario B" in scenario:
    severity = 0.30
else:
    severity = 0.50 # Extreme

# --- PART 4: THE MATH ENGINE (Logic) ---
# 1. Flood destroys asset value -> Increases LTV
df['Stressed_Value'] = df['Property_Value'] * (1 - (df['Flood_Risk'] * severity))
df['Stressed_LTV'] = df['Loan_Amount'] / df['Stressed_Value']

# 2. Heat destroys income -> Increases Default Probability
df['Stressed_PD'] = df['Base_PD'] * (1 + (df['Heat_Risk'] * severity * 10))

# 3. Flag Risky Loans
conditions = [
    (df['Stressed_LTV'] > 0.90) | (df['Stressed_PD'] > 0.15), # Critical Condition
    (df['Stressed_LTV'] <= 0.90) & (df['Stressed_PD'] <= 0.15) # Safe Condition
]

# *** FIX IS HERE: We added default='SAFE' ***
df['Risk_Status'] = np.select(conditions, ['CRITICAL', 'SAFE'], default='SAFE')

# --- PART 5: VISUALIZATION ---
st.title(f"🏦 Climate Risk Stress Test: {scenario}")
st.markdown("Real-time impact analysis of **Floods (Collateral Damage)** and **Heatwaves (Income Loss)**.")

# Top Metrics
col1, col2, col3 = st.columns(3)
risky_loans = df[df['Risk_Status'] == 'CRITICAL']
capital_at_risk = risky_loans['Loan_Amount'].sum() / 10000000 # In Crores

col1.metric("Total Portfolio Size", f"₹ {df['Loan_Amount'].sum()/10000000:.2f} Cr")
col2.metric("⚠️ Capital at Risk (VaR)", f"₹ {capital_at_risk:.2f} Cr", delta="-High Risk")
col3.metric("Critical Loans Count", f"{len(risky_loans)}")

# Map
st.subheader(f"📍 Geographic Risk Heatmap ({scenario})")
fig = px.scatter_mapbox(
    df, lat="Lat", lon="Lon", 
    color="Risk_Status", 
    size="Loan_Amount",
    color_discrete_map={"SAFE": "green", "CRITICAL": "red"},
    zoom=4, mapbox_style="open-street-map",
    hover_data=["District", "Stressed_LTV", "Stressed_PD"]
)
st.plotly_chart(fig, use_container_width=True)

# Data Table
st.subheader("📋 Critical Loan Report")
st.dataframe(risky_loans[['Loan_ID', 'District', 'Loan_Amount', 'Stressed_LTV', 'Risk_Status']])