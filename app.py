# app.py
import os
import tempfile
import uuid
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from google.cloud import bigquery
import audio_processing as ap

load_dotenv()

# --- CONFIG ---
GCS_BUCKET = os.environ.get("GCS_BUCKET", "your-gcs-bucket-name")
BIGQUERY_PROJECT = ap.BIGQUERY_PROJECT_ID
ALLOWED_EXTENSIONS = {"wav", "flac", "mp3", "m4a", "ogg"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB max

bq_client = bigquery.Client(project=BIGQUERY_PROJECT)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    # --- Validate file ---
    if "audio" not in request.files:
        return jsonify({"status": "error", "message": "No file part 'audio' in request"}), 400

    file = request.files["audio"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "No selected file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"status": "error", "message": "File type not allowed"}), 400

    # --- Save file temporarily ---
    filename = secure_filename(file.filename)
    tmpdir = tempfile.mkdtemp()
    local_path = os.path.join(tmpdir, filename)
    file.save(local_path)

    # --- Destination path in GCS ---
    dest_name = f"upload_audio/{uuid.uuid4().hex}_{filename}"

    try:
        # 🔥 Core pipeline call (NO agent name passed)
        result = ap.process_local_file_and_upload(
            local_path=local_path,
            bucket_name=GCS_BUCKET,
            dest_blob_name=dest_name
        )

        return jsonify({
            "status": "ok",
            "data": result
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:
        # --- Cleanup local temp file ---
        try:
            os.remove(local_path)
        except Exception:
            pass


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        debug=True
    )
