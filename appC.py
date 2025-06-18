from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
#import sqlite3
import os

def split_text(text, max_tokens=300):
    import re
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks, current_chunk = [], ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_tokens:
            current_chunk += sentence + " "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks





from local_model1 import ask_local_llm  # ✅ Uses Ollama locally

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

UPLOAD_FOLDER = 'uploaded_texts'
ALLOWED_EXTENSIONS = {'txt', 'csv', 'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload_text', methods=['GET', 'POST'])
def upload_text():
    if 'username' not in session:
        return redirect(url_for("login"))

    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template("dashboard.html", error="No file part in the request")

        file = request.files['file']
        if file.filename == '':
            return render_template("dashboard.html", error="No file selected")

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            ext = filename.rsplit('.', 1)[1].lower()
            file_content = ""

            if ext == 'txt':
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    file_content = f.read()

            elif ext == 'csv':
                import pandas as pd
                df = pd.read_csv(filepath)
                file_content = df.to_string(index=False)

            elif ext == 'pdf':
                try:
                    import fitz  # PyMuPDF
                except ImportError:
                    return render_template("dashboard.html", error="Missing PyMuPDF. Install with: pip install pymupdf")

                try:
                    doc = fitz.open(filepath)
                    for page in doc:
                        file_content += page.get_text()
                except Exception as e:
                    return render_template("dashboard.html", error=f"Failed to read PDF: {e}")

            else:
                return render_template("dashboard.html", error="Unsupported file type")

            return render_template("dashboard.html", file_content=file_content, uploaded_file=filename)

    return render_template("dashboard.html")






# 🔐 Login
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == "misa" and password == "coffee123":
            session["username"] = username
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

# 📊 Dashboard
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")

# 🧠 Ask AI
@app.route('/ask_file', methods=['POST'])
def ask_file():
    if 'username' not in session:
        return redirect(url_for("login"))

    query = request.form.get("query")
    filename = request.form.get("filename")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(filepath):
        return render_template("dashboard.html", error="Uploaded file not found")

    try:
        # Try reading with utf-8, fallback to ignoring errors
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            file_content = f.read()
    except Exception as e:
        return render_template("dashboard.html", error=f"Failed to read file: {e}")

    # Split file into chunks
    chunks = split_text(file_content, max_tokens=300)
    chunks = chunks[:3]  # Limit to first 3 chunks to avoid long wait

    answers = []
    for i, chunk in enumerate(chunks):
        prompt = f"""Answer the question based on the following chunk of a document:

Chunk {i+1}:
\"\"\"{chunk}\"\"\"

Question: {query}
Answer:"""
        try:
            response = ask_local_llm(prompt)
        except Exception as e:
            response = f"-- Error on chunk {i+1}: {e}"
        answers.append(response.strip())

    combined_answer = "\n\n".join(answers)

    return render_template("dashboard.html",
                           file_content=file_content,
                           uploaded_file=filename,
                           answer=combined_answer,
                           query=query)



# 🔓 Logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

# 🔑 Forgot Password
@app.route("/forgot_password")
def forgot_password():
    return render_template("forgot_password.html")


app.run(debug=True)