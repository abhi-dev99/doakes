# Documentation: Project Root & Architecture

## 1. Purpose
This document provides a high-level overview of the ARGUS repository structure. It explains the files and folders that live at the root of the project, how they interact, and how the overall application is containerized and configured.

## 2. Directory Structure

### `/backend`
The core Python application. Contains the FastAPI server, the ML ensemble, data generation scripts, and SQLite database.
*   `/ml`: Contains the actual predictive models, feature extractors, and specialized heuristic engines.
*   `/simulator`: Contains the synthetic transaction generator.
*   `main.py`: The FastAPI server entry point.

### `/frontend`
The React 18 / Vite frontend application serving the Command Center dashboard.
*   `/src`: Contains the React components, Tailwind CSS styling, and WebSocket networking logic.
*   `Appv2.jsx`: The primary dashboard view.

### `/survey-form`
The market validation module containing the simulated feedback loop from 300 banking executives.

### `/docs/reading`
This directory! Contains the file-by-file technical documentation for the entire project.

### `/assignments`
Contains project management artifacts, planning documents, and academic requirements. (Note: The `/assignments/prep` folder is `.gitignore`d as it contains scratch work).

### `/deprecated`
Contains legacy V1 and V2 models, old training scripts, and outdated API endpoints. These files are kept for historical reference and code review but are intentionally disconnected from the live V4 application. This folder is ignored by Git.

## 3. Root Configuration Files

*   **`README.md`**: The primary entry point for developers. Contains setup instructions, the technology stack, and architectural diagrams.
*   **`.gitignore`**: Ensures that virtual environments (`venv`, `node_modules`), heavy SQLite databases (`argus_data.db`), and deprecated folders are not committed to the repository.

## 4. Overall Execution Flow
1.  **Start Backend**: Running `uvicorn main:app` starts the Python server. It loads the `FraudDetectionEngine`, pre-loads the XGBoost/LightGBM weights into memory, and opens the WebSocket port.
2.  **Start Frontend**: Running `npm run dev` starts the React dashboard. It connects to the backend WebSocket.
3.  **Simulation Loop**: `main.py` triggers `transaction_gen.py` to create a payload. The payload flows through `pre_auth_engine.py` -> `feature_extractor.py` -> `fraud_model.py` -> `explainable_ai.py` -> `alert_notifications.py` -> WebSocket broadcast to Frontend. 

This entire flow occurs in under 20 milliseconds per transaction.
