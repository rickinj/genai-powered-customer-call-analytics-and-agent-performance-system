# audio_processing.py
import os
import re
import random
import json
import mimetypes
import time
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
from google.cloud import bigquery, storage
from vertexai import init
from vertexai.generative_models import GenerativeModel, Part
from pydantic import BaseModel, Field
from pydub import AudioSegment
from datetime import datetime

load_dotenv()

# --- CONFIGURATION ---
BIGQUERY_PROJECT_ID = os.environ.get("BIGQUERY_PROJECT_ID", "your-project-id")
BIGQUERY_DATASET = os.environ.get("BIGQUERY_DATASET", "your-dataset-name")
BIGQUERY_TABLE_CUSTOMERS = os.environ.get("BIGQUERY_TABLE_CUSTOMERS", "your-customer-table-name")
BIGQUERY_TABLE_EMPLOYEES = os.environ.get("BIGQUERY_TABLE_EMPLOYEES", "your-employee-table-name")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "your-llm-model-name")
GCS_BUCKET = os.environ.get("GCS_BUCKET", "your-gcs-bucket-name")

# --- CLIENT INITIALIZATION ---
try:
    bigquery_client = bigquery.Client(project=BIGQUERY_PROJECT_ID)
    storage_client = storage.Client()
    init(project=BIGQUERY_PROJECT_ID, location="us-central1")
    gemini_model = GenerativeModel(GEMINI_MODEL)
    print("✅ Clients initialized successfully.")
except Exception as e:
    print(f"❌ Error initializing clients: {e}")
    raise SystemExit(1)

# ---------------------------------------------------------------------------------------------------------------------------------------- # 

# --- STRUCTURE FOR OUTPUT ---
class CallAnalysis(BaseModel):
    phone_number: str = Field(description="10-digit number, or 'Incomplete phone number' / 'Missing phone number'")
    problem_solved: str = Field(description="Solved or Pending")
    problem_type: str = Field(description="Payment, Network, Recharge")
    sentiment: str = Field(description="Summary of customer’s emotional tone")
    full_transcript: str = Field(description="Full corrected transcript text")
    agent_name: str = Field(description="Full name of Agent or the employee talking to the customer")
    agent_tone: str = Field(description="Tone of the Agent in a summarized form")
    empathy_score: int = Field(description="Overall empathy of the Agent")
    clarity_score: int = Field(description="How clear the Agent/Employee was during the call in solving the complaint")
    interruption_behavior: str = Field(description="How well the Agent listened to the complaint without unwanted interruptions")
    improvement_suggestions: str = Field(description="Suggestions on the field or areas of improvement for the Agent")
    overall_agent_feedback: str = Field(description="Overall feedback of the Agent considering the above points")

# ---------------------------------------------------------------------------------------------------------------------------------------- # 

# --- HELPERS ---

def generate_customer_id() -> int:
    return random.randint(10000, 99999)

def get_call_duration_seconds(local_path: str) -> int:
    """
    Returns call duration in seconds.
    """
    audio = AudioSegment.from_file(local_path)
    return int(len(audio) / 1000)

def clean_phone_number(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        return digits
    elif 7 <= len(digits) < 10:
        return "Incomplete phone number"
    return "Missing phone number"

def normalize_improvement_suggestions(value) -> str:
    """
    Ensures improvement_suggestions is always a STRING.
    - If list → join into bullet-style string
    - If string → return as-is
    - Else → empty string
    """
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value)
    if isinstance(value, str):
        return value
    return ""

def extract_agent_from_filename(filename: str):
    """
    Expected format: agentName-employeeId.ext
    Example: RohitSharma-EMP1023.wav
    """
    name = Path(filename).stem
    if "-" in name:
        agent_name, employee_id = name.split("-", 1)
        return agent_name.strip(), employee_id.strip()
    return "Unknown", "UNKNOWN_EMP"


def upload_file_to_gcs(local_path: str, bucket_name: str, dest_blob_name: str):
    mime_type, _ = mimetypes.guess_type(local_path)
    if mime_type is None:
        mime_type = "application/octet-stream"
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(dest_blob_name)
    print(f"⬆️ Uploading {local_path} → gs://{bucket_name}/{dest_blob_name}")
    blob.upload_from_filename(local_path)
    return f"gs://{bucket_name}/{dest_blob_name}", mime_type

# ---------------------------------------------------------------------------------------------------------------------------------------- # 

# --- MAIN PROCESSING FUNCTION ---

def transcribe_and_analyze_audio(gcs_uri: str, agent_name: str, mime_type: str = None) -> Dict[str, Any]:
    """
    Single Gemini prompt that does BOTH:
    - Transcription
    - Analysis (phone number, problem solved, type, sentiment)
    """
    mime_type = mime_type or mimetypes.guess_type(gcs_uri)[0] or "audio/wav"

    print(f"🎧 Starting combined transcription + analysis for {gcs_uri} ({mime_type})")

    audio_part = Part.from_uri(gcs_uri, mime_type=mime_type)

    unified_prompt = """
            You are an expert Airtel call quality analyst.

            Carefully listen to the entire audio recording and produce a structured JSON response.

            Your tasks:

            1) Transcribe the full call clearly.
            - Correct grammar where needed.
            - Label speakers strictly as "Customer" and "Support".

            2) Extract customer-related information:
            - "phone_number": Any phone number mentioned (any length). If none, return "Missing phone number".
            - "problem_solved": Either "Solved" or "Pending".
            - "problem_type": Choose strictly from ["Payment", "Network", "Recharge"].
            - "sentiment": Describe the customer's emotional state in **20 words or fewer**.

            3) Identify the support agent:
            - If the support agent **explicitly states their name** during the call, extract it as "agent_name".
            - If the name is **not clearly stated**, return "Unknown".
            - Do NOT guess or infer the name.

            4) Evaluate the support agent's performance:
            - "agent_tone": Describe the agent's tone (e.g., calm, rushed, defensive, empathetic).
            - "empathy_score": Rate from 1 to 5.
            - "clarity_score": Rate from 1 to 5 based on explanation quality.
            - "interruption_behavior": One of ["low", "medium", "high"].
            - "improvement_suggestions": Provide **3 short bullet points**.
            - "overall_agent_feedback": A concise, manager-ready evaluation paragraph.

            IMPORTANT INSTRUCTIONS:
            - Return **VALID JSON ONLY**.
            - Do NOT include explanations, markdown, or extra text.
            - If any field cannot be determined, use an empty string or "Unknown" where applicable.

            Return JSON in the following exact structure:

            {
            "phone_number": "",
            "problem_solved": "",
            "problem_type": "",
            "sentiment": "",
            "full_transcript": "",
            "agent_name": "Unknown",
            "agent_tone": "",
            "empathy_score": 0,
            "clarity_score": 0,
            "interruption_behavior": "",
            "improvement_suggestions": "",
            "overall_agent_feedback": ""
            }
"""

    try:
        response = gemini_model.generate_content([audio_part, unified_prompt])
        raw = response.text.strip()

        match = re.search(r"```json(.*?)```", raw, re.DOTALL)
        if match:
            raw = match.group(1).strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            print(f"⚠️ Failed to parse JSON from Gemini output. Raw content:\n{raw}")
            return {"error": "Invalid JSON", "raw_output": raw}

        # Validate and clean phone number
        parsed["phone_number"] = clean_phone_number(parsed.get("phone_number", ""))
        return parsed

    except Exception as e:
        print(f"❌ Error during Gemini processing: {e}")
        return {"error": str(e)}

def resolve_agent_identity(parsed_data: dict, filename: str):
    spoken_name = parsed_data.get("agent_name", "").strip()

    file_agent_name, employee_id = extract_agent_from_filename(filename)

    if spoken_name and spoken_name.lower() != "unknown":
        final_agent_name = spoken_name
    else:
        final_agent_name = file_agent_name

    return final_agent_name, employee_id

def insert_customer_data(data: dict, customer_id: int, gcs_uri: str):
    table_id = f"{BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE_CUSTOMERS}"

    row = [{
        "customer_id": customer_id,
        "phone_number": data.get("phone_number"),
        "problem_solved": data.get("problem_solved"),
        "problem_type": data.get("problem_type"),
        "sentiment": data.get("sentiment"),
        "full_transcript": data.get("full_transcript"),
        "call_gcs_uri": gcs_uri,
        "created_at": datetime.now().isoformat()
    }]

    bigquery_client.load_table_from_json(row, table_id).result()


def insert_employee_data(data: dict, customer_id: int, agent_name: str, employee_id: str,call_duration_seconds: int):
    table_id = f"{BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE_EMPLOYEES}"

    row = [{
        "employee_id": employee_id,
        "agent_name": agent_name,
        "customer_id": customer_id,
        "agent_tone": data.get("agent_tone"),
        "empathy_score": int(data.get("empathy_score", 0)),
        "clarity_score": int(data.get("clarity_score", 0)),
        "interruption_behavior": data.get("interruption_behavior"),
        "improvement_suggestions": normalize_improvement_suggestions(data.get("improvement_suggestions")),
        "overall_agent_feedback": data.get("overall_agent_feedback"),
        "call_duration_seconds": call_duration_seconds,
        "created_at": datetime.now().isoformat()
    }]

    bigquery_client.load_table_from_json(row, table_id).result()

'''
def insert_to_bigquery(data: dict, customer_id: int):
    """Inserts combined results into BigQuery."""
    table_id = f"{BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
    schema = [
        bigquery.SchemaField("customer_id", "INTEGER"),
        bigquery.SchemaField("phone_number", "STRING"),
        bigquery.SchemaField("full_transcript", "STRING"),
        bigquery.SchemaField("problem_solved", "STRING"),
        bigquery.SchemaField("problem_type", "STRING"),
        bigquery.SchemaField("sentiment", "STRING"),
    ]

    row = [{
        "customer_id": customer_id,
        "phone_number": data.get("phone_number", ""),
        "full_transcript": data.get("full_transcript", ""),
        "problem_solved": data.get("problem_solved", ""),
        "problem_type": data.get("problem_type", ""),
        "sentiment": data.get("sentiment", ""),
    }]

    print(f"📦 Uploading results for Customer ID {customer_id} to BigQuery...")
    job_config = bigquery.LoadJobConfig(schema=schema)
    job = bigquery_client.load_table_from_json(row, table_id, job_config=job_config)
    job.result()
    print("✅ Data inserted successfully.")

'''

# --- MAIN EXECUTION ---
def process_local_file_and_upload(
    local_path: str,
    bucket_name: str = GCS_BUCKET,
    dest_blob_name: str = None
):
    """
    Uploads a local audio file to GCS and runs the complete call analysis pipeline.

    Pipeline:
    1) Upload audio to GCS
    2) Gemini transcription + analysis
    3) Resolve agent identity (Gemini → filename fallback)
    4) Insert customer data into customer_call_analysis
    5) Insert employee data into employee_performance

    Returns structured analysis data and gs:// URI.
    """

    # --- Prepare destination name in GCS ---
    if dest_blob_name is None:
        dest_blob_name = (
            f"upload_audio/{Path(local_path).stem}_"
            f"{random.randint(1000,9999)}{Path(local_path).suffix}"
        )

    # --- Upload to GCS ---
    gs_uri, mime_type = upload_file_to_gcs(local_path, bucket_name, dest_blob_name)

    # --- Run Gemini analysis (NO agent name passed) ---
    result = transcribe_and_analyze_audio(gcs_uri=gs_uri, agent_name="", mime_type=mime_type)

    # --- Generate customer ID ---
    customer_id = generate_customer_id()

    # --- Get audio length ---
    call_duration_seconds = get_call_duration_seconds(local_path)

    # --- Resolve agent identity ---
    filename = Path(local_path).name
    final_agent_name, employee_id = resolve_agent_identity(result,filename)

    # --- Insert into BigQuery (separate tables) ---
    insert_customer_data(
        data=result,
        customer_id=customer_id,
        gcs_uri=gs_uri
    )

    insert_employee_data(
        data=result,
        customer_id=customer_id,
        agent_name=final_agent_name,
        employee_id=employee_id,
        call_duration_seconds=call_duration_seconds
    )

    # --- Return combined response ---
    return {
        "gs_uri": gs_uri,
        "customer_id": customer_id,
        "agent_name": final_agent_name,
        "employee_id": employee_id,
        "result": result
    }


if __name__ == "__main__":
    local_file = "sample_audio.wav"
    if os.path.exists(local_file):
        print("🚀 Starting local audio processing pipeline...")
        process_local_file_and_upload(local_file)
    else:
        print("⚠️ sample_audio.wav not found. Please place an audio file in this directory.")
