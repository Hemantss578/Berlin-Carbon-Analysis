# Berlin Smart Canopy: Urban Carbon Sequestration & ML Optimization
## 📖 Project Overview

Berlin aims to achieve aggressive climate-neutral goals. Optimizing this transition requires precise, data-driven management of the city's urban canopy. This project integrates demographic, geospatial, and botanical metrics to build a two-layer analytical intelligence framework:
1. **Diagnostic:** Mapping local CO2 emission intensity against existing tree canopy sequestration capacities.
2. **Predictive & Prescriptive:** Using unsupervised clustering to prioritize high-risk urban heat zones, paired with a supervised forecasting engine that simulates the multi-decade impact of localized planting strategies.

---

## 🏗️ Repository Architecture

The project enforces a strict separation of concerns, dividing raw data synthesis, machine learning pipeline execution, and the interactive application layer.

berlin_smart_canopy/
├── app.py                  # 2-Page interactive Streamlit web application
├── data_generator.py       # Deterministic synthetic data compiler (EPSG:4326)
├── ml_engine.py            # Feature engineering, model training, & artifact serialization
├── README.md               # Repository documentation
├── requirements.txt        # Managed project dependencies
└── data/
    ├── raw/                # Generated synthetic CSV and GeoJSON maps
    ├── processed/          # Engineered training features and enriched dataframes
    └── models/             # Serialized KMeans, RandomForest models, and metadata

✨ Core Application Features
📊 Page 1: Urban Canopy Dashboard
Emissions Choropleth: Visualizes annual CO2 footprints across Berlin postal codes (PLZ) using interactive boundary shading layer vectors.

Canopy Density Overlay: Features high-resolution mapping of specific mature trees and their current environmental offsets.

Geospatial Cross-Filtering: Dynamically calculated hover metrics highlighting local population density and concrete-sealed surface ratios.

🧪 Page 2: Planting Simulator & Forecasting
Target Intervention Selector: Allows urban planners to isolate an individual postal code identified as high-priority.

Virtual Arborist Controls: Interactive sliders to configure targeted planting initiatives across distinct species (e.g., Oak, Maple, Lime, Plane trees) along with starting sapling ages.

Machine Learning Projections: Leverages a trained regressor to render an instant, non-linear line chart projecting net-footprint adjustments up to the year 2050.

🧠 Machine Learning Framework
The application relies on two decoupled machine learning workflows implemented within ml_engine.py:

1. Unsupervised Prioritization (K-Means Clustering)
Objective: Automatically segment Berlin's postal codes into actionable priority levels.

Features Used: Total CO2 Emissions, Sealed Surface Ratios, and Existing Canopy Sequestration Cap.

Output: Labels areas into distinct zones (e.g., Critical Intervention Required, Stable Canopy Ecosystem).

2. Supervised Forecasting (Random Forest Regressor)
Objective: Predict total metric tons of CO2 absorption for a specific neighborhood in the year 2050.

Feature Engineering: Accounts for non-linear, exponential botanical growth coefficients. The model scales predictive values based on the maturity curve of the selected species (e.g., fast early growth in Maples vs. high long-term biomass storage in mature Oaks).

🚀 Installation & Quick Start
Ensure you have Python 3.12+ configured locally. Run the following command sequences from the project's root folder:

1. Environment Setup
Install the necessary geospatial, mathematical, and visualization dependencies:

Bash
pip install -r requirements.txt
2. Data Initialization
Generate the synthetic geospatial profiles and base data models locally:

Bash
python berlin_smart_canopy/data_generator.py
3. Model Training
Execute the feature engineering pipeline and train the serialization models:

Bash
python berlin_smart_canopy/ml_engine.py
4. Run the Platform
Launch the reactive Streamlit application layer:

Bash
streamlit run berlin_smart_canopy/app.py
The application will automatically initialize in your local browser window at http://localhost:8501.

🛠️ Built With
Core Engine: Python, NumPy, Pandas

Machine Learning: Scikit-Learn, Joblib

Geospatial Pipeline: GeoPandas, PyArrow, Folium, Streamlit-Folium

Visualization Interface: Streamlit, Altair
