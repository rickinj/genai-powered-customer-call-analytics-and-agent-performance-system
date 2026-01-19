# clean_up.py
import os
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
GCP_PROJECT_ID = os.getenv("BIGQUERY_PROJECT_ID")
BQ_DATASET_ID = os.getenv("BIGQUERY_DATASET")

# --- TABLE NAMES ---
CUSTOMER_TABLE_ID = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.tbl_customer_call_analysis"
EMPLOYEE_TABLE_ID = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.tbl_employee_performance"

# -------------------------------------------------
# CUSTOMER CALL ANALYSIS TABLE SCHEMA
# -------------------------------------------------
CUSTOMER_SCHEMA = [
    bigquery.SchemaField("customer_id", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("phone_number", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("problem_solved", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("problem_type", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("sentiment", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("full_transcript", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("call_gcs_uri", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("created_at", "TIMESTAMP", mode="NULLABLE"),
]

# -------------------------------------------------
# EMPLOYEE PERFORMANCE TABLE SCHEMA
# -------------------------------------------------
EMPLOYEE_SCHEMA = [
    bigquery.SchemaField("employee_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("agent_name", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("customer_id", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("agent_tone", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("empathy_score", "INTEGER", mode="NULLABLE"),
    bigquery.SchemaField("clarity_score", "INTEGER", mode="NULLABLE"),
    bigquery.SchemaField("interruption_behavior", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("improvement_suggestions", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("overall_agent_feedback", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("call_duration_seconds", "INTEGER", mode="NULLABLE"),
    bigquery.SchemaField("created_at", "TIMESTAMP", mode="NULLABLE"),
]

# -------------------------------------------------
# HELPER: RESET TABLE
# -------------------------------------------------
def reset_table(client: bigquery.Client, table_id: str, schema: list):
    print(f"\n🔄 Resetting table: {table_id}")

    try:
        client.delete_table(table_id, not_found_ok=True)
        print("✅ Existing table deleted (if any).")
    except Exception as e:
        print(f"⚠️ Error deleting table: {e}")

    try:
        table = bigquery.Table(table_id, schema=schema)
        client.create_table(table)
        print("✅ Table created successfully.")
    except Exception as e:
        print(f"❌ Error creating table: {e}")

# -------------------------------------------------
# MAIN
# -------------------------------------------------
def main():
    if not GCP_PROJECT_ID or not BQ_DATASET_ID:
        raise ValueError("BIGQUERY_PROJECT_ID and BIGQUERY_DATASET must be set in .env")

    client = bigquery.Client(project=GCP_PROJECT_ID)

    reset_table(client, CUSTOMER_TABLE_ID, CUSTOMER_SCHEMA)
    reset_table(client, EMPLOYEE_TABLE_ID, EMPLOYEE_SCHEMA)

    print("\n🎉 BigQuery tables reset successfully.")

if __name__ == "__main__":
    main()
