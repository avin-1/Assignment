from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import pandas as pd
import os
import uuid
import json
from dotenv import load_dotenv
import resend

load_dotenv()
app = Flask(__name__, static_folder="frontend/dist", static_url_path="/")
CORS(app)

DB = "candidates.db"
# Use SPACE_HOST provided by Hugging Face Spaces if present
hf_host = os.environ.get("SPACE_HOST")
default_frontend_url = f"https://{hf_host}" if hf_host else "http://localhost:5173"
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", default_frontend_url)

# ─────────────────────────────────────
# DB helpers
# ─────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            phone TEXT
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            candidate_name TEXT,
            candidate_email TEXT,
            questions TEXT,
            history TEXT DEFAULT '[]',
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            candidate_name TEXT,
            candidate_email TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    conn.close()

init_db()

# ─────────────────────────────────────
# Email helper  (uses Resend HTTPS API — works on HuggingFace)
# ─────────────────────────────────────
def send_email(to_email: str, candidate_name: str, chat_url: str) -> bool:
    api_key = os.environ.get("RESEND_API_KEY")
    sender = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")

    if not api_key:
        print("[email] Missing RESEND_API_KEY — email not sent")
        return False

    resend.api_key = api_key

    html_body = f"""
    <html><body>
      <div style="font-family:Arial,sans-serif;padding:20px;color:#1a1a2e;max-width:600px;margin:auto;">
        <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:30px;border-radius:12px 12px 0 0;text-align:center;">
          <h1 style="color:white;margin:0;">OmniMise Screening</h1>
          <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;">AI-Powered Candidate Interview</p>
        </div>
        <div style="background:#f8f9ff;padding:30px;border-radius:0 0 12px 12px;border:1px solid #e0e0f0;">
          <p style="font-size:16px;">Hi <strong>{candidate_name}</strong>,</p>
          <p style="color:#555;">You have been invited to complete a short AI-powered screening interview for a position at our company.</p>
          <p style="color:#555;">The interview is conversational and typically takes <strong>5–10 minutes</strong>.</p>
          <div style="text-align:center;margin:30px 0;">
            <a href="{chat_url}" style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:14px 32px;text-decoration:none;border-radius:8px;font-size:16px;font-weight:bold;">
              Begin Interview
            </a>
          </div>
          <p style="color:#888;font-size:13px;">Or paste this link in your browser:<br/>
            <a href="{chat_url}" style="color:#667eea;">{chat_url}</a>
          </p>
          <p style="color:#888;font-size:12px;margin-top:20px;">Best of luck!<br/>— The OmniMise Team</p>
        </div>
      </div>
    </body></html>
    """

    try:
        params: resend.Emails.SendParams = {
            "from": f"OmniMise <{sender}>",
            "to": [to_email],
            "subject": "You're Invited: AI Screening Interview",
            "html": html_body,
        }
        r = resend.Emails.send(params)
        print(f"[email] Sent to {to_email} — id: {r.get('id')}")
        return True
    except Exception as e:
        print(f"[email] FAILED to send to {to_email}: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


# ─────────────────────────────────────
# 1. Upload Candidates
# ─────────────────────────────────────
@app.route('/api/upload-candidates', methods=['POST'])
def upload_candidates():
    if 'file' not in request.files:
        return jsonify({"error": "No file in request"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    try:
        df = pd.read_excel(file)
    except Exception as e:
        return jsonify({"error": f"Could not read Excel: {str(e)}"}), 400

    conn = get_db()
    c = conn.cursor()
    inserted = 0
    try:
        for _, row in df.iterrows():
            name  = str(row.get('name',  '')) if pd.notna(row.get('name',  '')) else ''
            email = str(row.get('email', '')) if pd.notna(row.get('email', '')) else ''
            phone = str(row.get('phoneno', '')) if pd.notna(row.get('phoneno', '')) else ''
            if not email:
                continue
            try:
                c.execute("INSERT INTO candidates (name,email,phone) VALUES (?,?,?)", (name, email, phone))
                inserted += 1
            except sqlite3.IntegrityError:
                pass  # duplicate email — skip
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return jsonify({"message": f"Uploaded successfully. {inserted} new candidates added."}), 200


# ─────────────────────────────────────
# 2. Start Session (HR triggers this)
#    Extract rules → generate questions → create sessions → send emails
# ─────────────────────────────────────
from Agent.ruleAgent import process_prompt_with_agent
from Agent.chatAgent import generate_questions_from_rules

@app.route('/api/start-session', methods=['POST'])
def start_session():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "Please provide a 'text' field with HR rules"}), 400

    text_input = data['text']
    print(f"[start-session] Received HR input: {text_input}")

    try:
        # 1. Extract structured rules
        rules = process_prompt_with_agent(text_input)
        print(f"[start-session] Extracted {len(rules)} rules.")

        # 2. Generate questions from rules
        questions = generate_questions_from_rules(rules)
        questions_json = json.dumps(questions)
        print(f"[start-session] Generated {len(questions)} questions.")

    except Exception as e:
        import traceback
        return jsonify({"error": f"AI processing failed: {str(e)}", "trace": traceback.format_exc()}), 500

    # 3. Fetch all candidates and create sessions + send emails
    conn = get_db()
    c = conn.cursor()
    sent_count = 0
    sessions_created = 0

    try:
        c.execute("SELECT name, email FROM candidates WHERE email IS NOT NULL AND email != ''")
        candidates = c.fetchall()

        if not candidates:
            return jsonify({"error": "No candidates found. Please upload a spreadsheet first."}), 400

        for cand in candidates:
            session_id = str(uuid.uuid4())
            name = cand['name'] or "Candidate"
            email = cand['email']

            # Insert session
            c.execute(
                "INSERT INTO sessions (session_id, candidate_name, candidate_email, questions) VALUES (?,?,?,?)",
                (session_id, name, email, questions_json)
            )
            sessions_created += 1

            # Send email
            chat_url = f"{FRONTEND_BASE_URL}/chat/{session_id}"
            if send_email(email, name, chat_url):
                sent_count += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return jsonify({
        "message": f"Sessions created and emails sent.",
        "rules": rules,
        "questions": questions,
        "sessions_created": sessions_created,
        "emails_sent": sent_count
    }), 200


# ─────────────────────────────────────
# 3. Get Session Info (candidate loads chat page)
# ─────────────────────────────────────
@app.route('/api/chat/<session_id>', methods=['GET'])
def get_session(session_id):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        session = c.fetchone()
        if not session:
            return jsonify({"error": "Session not found"}), 404

        return jsonify({
            "session_id": session_id,
            "candidate_name": session['candidate_name'],
            "status": session['status'],
            "history": json.loads(session['history'] or '[]')
        }), 200
    finally:
        conn.close()


# ─────────────────────────────────────
# 4. Chat turn (candidate sends a message)
# ─────────────────────────────────────
from Agent.chatAgent import chat_turn, start_interview

@app.route('/api/chat/<session_id>/message', methods=['POST'])
def send_message(session_id):
    data = request.get_json()
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        session = c.fetchone()
        if not session:
            return jsonify({"error": "Session not found"}), 404
        if session['status'] == 'completed':
            return jsonify({"reply": "This interview has already been completed. Thank you!", "is_complete": True}), 200

        questions = json.loads(session['questions'])
        history = json.loads(session['history'] or '[]')
        candidate_name = session['candidate_name'] or "Candidate"

        # Get AI response
        result = chat_turn(candidate_name, questions, history, user_message)

        # Update history
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": result["reply"]})

        # Save history
        c.execute("UPDATE sessions SET history = ? WHERE session_id = ?",
                  (json.dumps(history), session_id))

        # If interview is complete → save summary
        if result["is_complete"] and result["summary"]:
            summary = result["summary"]
            summary["candidate_email"] = session["candidate_email"]
            c.execute(
                "INSERT INTO responses (session_id, candidate_name, candidate_email, summary) VALUES (?,?,?,?)",
                (session_id, candidate_name, session["candidate_email"], json.dumps(summary))
            )
            c.execute("UPDATE sessions SET status = 'completed' WHERE session_id = ?", (session_id,))

        conn.commit()
        return jsonify({
            "reply": result["reply"],
            "is_complete": result["is_complete"]
        }), 200

    except Exception as e:
        import traceback
        conn.rollback()
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
    finally:
        conn.close()


# ─────────────────────────────────────
# 5. Start interview (first AI message when candidate loads)
# ─────────────────────────────────────
@app.route('/api/chat/<session_id>/start', methods=['POST'])
def start_chat(session_id):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        session = c.fetchone()
        if not session:
            return jsonify({"error": "Session not found"}), 404

        history = json.loads(session['history'] or '[]')

        # If there's already history, return the existing first message
        if history:
            first_ai = next((h["content"] for h in history if h["role"] == "assistant"), None)
            return jsonify({"reply": first_ai or "Hello! Ready to begin?"}), 200

        questions = json.loads(session['questions'])
        candidate_name = session['candidate_name'] or "Candidate"

        greeting = start_interview(candidate_name, questions)

        history.append({"role": "assistant", "content": greeting})
        c.execute("UPDATE sessions SET history = ?, status = 'in_progress' WHERE session_id = ?",
                  (json.dumps(history), session_id))
        conn.commit()

        return jsonify({"reply": greeting}), 200
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
    finally:
        conn.close()


# ─────────────────────────────────────
# 6. Fetch all interview responses (HR dashboard)
# ─────────────────────────────────────
@app.route('/api/responses', methods=['GET'])
def get_responses():
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='responses'")
        if not c.fetchone():
            return jsonify([]), 200

        c.execute("SELECT * FROM responses ORDER BY created_at DESC")
        rows = c.fetchall()
        result = []
        for r in rows:
            summary = json.loads(r['summary'] or '{}')
            result.append({
                "session_id": r['session_id'],
                "candidate_name": r['candidate_name'],
                "candidate_email": r['candidate_email'],
                "created_at": r['created_at'],
                "summary": summary
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route('/api/status')
def status():
    return jsonify({"status": "OmniMise API running"}), 200

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.errorhandler(404)
def not_found(e):
    # If the request is for an /api route, return a real 404 JSON
    if request.path.startswith('/api/'):
        return jsonify({"error": "Resource not found"}), 404
    # Otherwise, serve index.html for React Router to handle
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    app.run(host="0.0.0.0", port=port, debug=False)