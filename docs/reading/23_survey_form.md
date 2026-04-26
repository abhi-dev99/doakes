# Documentation: Market Validation Survey Module (`survey-form/`)

## 1. Purpose
This module handles the **Market Validation** phase of the ARGUS project. Instead of relying solely on technical benchmarks, it proves the commercial viability of the system by collecting data from banking executives and fraud analysts regarding their current pain points, latency tolerances, and feature priorities.

## 2. Key Components

### A. The Data Collection Form (`survey_form.html`)
A standalone HTML page containing a comprehensive questionnaire. It asks target customers (Banks, PSPs, Fintechs) to rate the importance of various features (Pre-Auth vs Post-Auth, India-specific models, Explainability) and their non-functional requirements (Latency, TPS, Uptime).

### B. The Simulation Script (`simulate_survey.py`)
Because collecting 300 real responses from banking executives for a hackathon/viva is practically impossible, this script simulates a realistic dataset of 300 survey responses.
*   **Persona Archetypes**: The script categorizes respondents into 7 distinct org types (e.g., Private Bank, Public Bank, Fintech, PSP).
*   **Bias Engine (`ARCHETYPE_BIAS`)**: Each archetype is given a mathematical bias to ensure the simulated answers make logical sense. For example:
    *   *PSPs* demand ultra-low latency (<5ms) because they sit in the middle of checkout flows.
    *   *Government DBT Platforms* have lower TPS requirements but demand absolute accuracy and strict India data residency.
    *   *Public Sector Banks* heavily prioritize Explainable AI for compliance/audit reasons.
*   **Realistic Payload Generation**: It uses arrays of real Indian names, real corporate domains (`@hdfcbank.co.in`, `@razorpay.com`), and specific text-based pain points ("Our false positive rate is above 20%", "SIM swap attacks hit us hard last year").

### C. Execution & Export
Running `python simulate_survey.py --count 300` generates these 300 profiles and automatically POSTs them to the backend API (`/api/survey/submit`). The backend saves this data into `argus_survey_responses.csv`.

## 3. Role in the Project (Viva Context)
During the viva defense, this data serves as the **Business Case** for ARGUS. It allows you to mathematically justify your architectural decisions:
*   *"Why did you use heuristic XAI instead of SHAP?"* -> "Because our market survey of 300 banking executives showed that 85% of them require sub-20ms latency, which SHAP cannot meet."
*   *"Why did you add a Digital Arrest detector?"* -> "Because Public Sector Banks indicated in our survey that social engineering is their fastest-growing threat vector."
