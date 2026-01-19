> [!NOTE]
> This project is an extension of the project [GenAI Audio Analysis (Google Cloud + Gemini + NLP + SQL)](https://github.com/rickinj/genai-audio-analysis). Do view the original project for SQL -> NLP rule based analysis.

# 🎧 GenAI-Powered Customer Call Analytics & Agent Performance System

This project is an **end-to-end GenAI-powered call analytics system** that ingests customer support call recordings, analyzes them using **Google Gemini**, and provides **actionable insights** on both **customer issues** and **support agent performance**. 
The system is designed to mimic a **real-world enterprise workflow**, with structured data storage in **BigQuery** and **live analytics dashboards in Power BI**.

---

## 🏗️ High-Level Architecture
    Audio File (UI Upload)
            ↓
    Flask Backend (Python)
            ↓
    Google Cloud Storage (Audio Storage)
            ↓
    Gemini (Transcription + Analysis)
            ↓
    BigQuery (Structured Storage)
            ↓
    Power BI (Live Dashboards & Analytics)

---

## ✨ Key Features

### 🎧 Audio Processing
- Upload customer support call recordings via a web UI
- Automatic upload to Google Cloud Storage
- Call duration computed deterministically from audio metadata

### 🧠 GenAI-Powered Analysis (Gemini)
- Full call transcription with speaker labeling
- Customer sentiment analysis
- Issue classification (Payment / Network / Recharge)
- Call resolution detection (Solved / Pending)
- Agent performance evaluation:
  - Agent tone assessment
  - Empathy score (1–5)
  - Clarity score (1–5)
  - Interruption behavior
  - Improvement suggestions
  - Overall qualitative feedback

### 🧍 Intelligent Agent Identification
- Extracts agent name if explicitly spoken during the call
- Falls back to filename-based identification (`AgentName-EmployeeID.ext`)
- Prevents guessing or hallucination of agent identities

### 🗄️ Enterprise-Grade Data Modeling
- Separate Customer and Employee tables
- Clean relational design using `customer_id` as a foreign key
- Timestamped records for analytics and auditing

### 📊 Live Analytics with Power BI
- BigQuery connected directly to Power BI
- Automatic refresh (no CSV downloads required)
- Interactive dashboards with slicers and KPIs

---

## 🧠 How Gemini Is Used

Gemini is used for **qualitative intelligence**, not for computing deterministic values.

### Gemini Responsibilities
- Call transcription with grammar correction
- Customer sentiment interpretation
- Agent tone and behavioral analysis
- Improvement suggestions and qualitative feedback generation

### Deterministic Processing
- Deterministic values such as **call duration** are **not inferred by AI**
- These values are calculated directly from audio metadata to ensure accuracy and reliability

---

## 📊 Power BI Dashboard

The Power BI dashboard is built on **live BigQuery connections** and provides real-time visibility into customer issues and agent performance.

### 🔹 KPI Overview
- Total Calls
- % Calls Resolved
- Average Empathy Score
- Average Clarity Score
- Average Call Duration

### 🔹 Call Insights
- Problem status distribution (Solved vs Pending)
- Problem type breakdown (Payment / Network / Recharge)

### 🔹 Agent Performance Analysis
- Agent-wise empathy and clarity scores
- Call duration vs clarity trends
- Qualitative agent feedback table generated using GenAI
- Interactive slicers (Agent, Year)

![Power BI Dashboard](assets/powerbi_dashboard.jpg)
---

## 🗄️ Data Model

### 📄 Customer Call Analysis Table  
**`tbl_customer_call_analysis`**

| Column Name     | Type      | Description                        |
|-----------------|-----------|------------------------------------|
| customer_id     | INTEGER   | Unique identifier for each call    |
| phone_number    | STRING    | Extracted or inferred phone number |
| problem_solved  | STRING    | Solved / Pending                   |
| problem_type    | STRING    | Payment / Network / Recharge       |
| sentiment       | STRING    | Customer emotional tone            |
| full_transcript | STRING    | Complete corrected transcript      |
| call_gcs_uri    | STRING    | GCS path of audio file             |
| created_at      | TIMESTAMP | Record creation time               |

### 👨‍💼 Employee Performance Table  
**`tbl_employee_performance`**

| Column Name             | Type      | Description                   |
|-------------------------|-----------|-------------------------------|
| employee_id             | STRING    | Unique employee identifier    |
| agent_name              | STRING    | Resolved agent name           |
| customer_id             | INTEGER   | Foreign key to customer table |
| agent_tone              | STRING    | Agent tone assessment         |
| empathy_score           | INTEGER   | Empathy score (1–5)           |
| clarity_score           | INTEGER   | Clarity score (1–5)           |
| interruption_behavior   | STRING    | low / medium / high           |
| improvement_suggestions | STRING    | Normalized suggestions        |
| overall_agent_feedback  | STRING    | Manager-ready evaluation      |
| call_duration_seconds   | INTEGER   | Call length in seconds        |
| created_at              | TIMESTAMP | Record creation time          |

---

## 🛠️ Tech Stack

### Frontend
- HTML, CSS, Vanilla JavaScript  

### Backend
- Python  
- Flask (API layer)

### Cloud & GenAI
- Google Cloud Storage (audio storage)  
- Google Vertex AI – Gemini 2.5 Flash  
- Google BigQuery (data persistence)

### Analytics Tool
- PowerBI

---

## 📂 Project Structure

    ├── app.py # Flask backend
    ├── table_creator.py # Table Creation
    ├── your_credentials.json # Google Cloud Credentials JSON File that can be generated in Service Accounts -> Manage Keys -> Download either as JSON or P12
    ├── audio_processing.py # Audio → Gemini → Customer + Employee/Agent Feedback pipeline
    ├── templates/
    │ └── index.html # Frontend UI
    ├── assets/
    │ └── powerbi_dashboard.png # Dashboard UI
    ├── .env # Environment variables (not committed)
    ├── powerbi_dashboard.pbix # PBIX file of the dummy dashboard
    └── README.md

---

## ⚙️ Environment Variables

Create a `.env` file with the following variables  
(values are not shared for security reasons):

```env
BIGQUERY_PROJECT_ID=your-project-id
BIGQUERY_DATASET=your-dataset
BIGQUERY_TABLE_CUSTOMERS=your-customer-table
BIGQUERY_TABLE_EMPLOYEES=your-employee-table
GCS_BUCKET=your-bucket-name
GEMINI_MODEL=gemini-2.5-flash
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
```

⚠️ The `.env` file is intentionally excluded from version control.

---

> [!NOTE]
> ⚠️ FFmpeg must be installed on the system for audio duration calculation (used by pydub).

---

## ▶️ Running the Project Locally

```bash
pip install -r requirements.txt
python app.py
```

Then open:
```bash
http://localhost:8080
```

---

## 🔐 Security & Permissions

- Uses Google service account authentication  
- Vertex AI accesses audio via managed service agents  
- GCS access controlled using IAM roles  
- No secrets committed to GitHub  

---

## ⚠️ Current Limitations
- Supports pre-recorded calls only (no real-time streaming)
- No speaker diarization; a single support agent is assumed per call
- Agent identification depends on spoken name or filename-based fallback
- Sentiment analysis is summarized, not token-level or time-segmented

## 🔮 Future Enhancements
- Real-time call streaming and on-the-fly analysis
- Speaker diarization for multi-agent or transferred calls
- Agent identity confidence scoring
- Supervisor alerting for low-quality or high-risk calls
- Automated coaching and training recommendations

---

## 🧑‍💻 Author Notes

This project was built to demonstrate:

- Practical GenAI system design  
- Real-world cloud integration  
- Robust handling of LLM outputs  
- Clean separation of frontend, backend, and AI logic  

---

## ⭐ Like this project?

Feel free to ⭐ the repository or fork it to extend further.
