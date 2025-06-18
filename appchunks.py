from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
#import sqlite3
import os


from local_model import ask_local_llm  # ✅ Uses Ollama locally

def chunk_text(text, max_chars=3000):
    """Split long text into chunks."""
    chunks = []
    while text:
        chunk = text[:max_chars]
        chunks.append(chunk)
        text = text[max_chars:]
    return chunks


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

UPLOAD_FOLDER = 'uploaded_texts'
ALLOWED_EXTENSIONS = {'txt', 'csv'}
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

            # Read text or csv based on extension
            ext = filename.rsplit('.', 1)[1].lower()
            if ext == 'txt':
                with open(filepath, 'r', encoding='utf-8') as f:
                    file_content = f.read()
            elif ext == 'csv':
                import pandas as pd
                df = pd.read_csv(filepath)
                file_content = df.to_string(index=False)  # Or df.head().to_html() if you want table display

            return render_template("dashboard.html", file_content=file_content, uploaded_file=filename)

        return render_template("dashboard.html", error="Invalid file type")

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

    with open(filepath, 'r', encoding='utf-8') as f:
    file_content = f.read()

chunks = chunk_text(file_content, max_chars=3000)  # You can adjust max_chars
answers = []

for i, chunk in enumerate(chunks):
    prompt = f"""Answer the following question based on this part of the file (chunk {i+1}/{len(chunks)}).

Text:
\"\"\"
{chunk}
\"\"\"

Question: {query}
Answer:"""

    try:
        partial_answer = ask_local_llm(prompt)
        answers.append(f"Chunk {i+1} Answer:\n{partial_answer.strip()}")
    except Exception as e:
        answers.append(f"-- Error processing chunk {i+1}: {e}")
        break  # Optional: stop after first failure

answer = "\n\n".join(answers)


    return render_template("dashboard.html", file_content=file_content, uploaded_file=filename, answer=answer, query=query)


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