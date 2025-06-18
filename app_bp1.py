from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
from local_model import ask_local_llm  # ✅ Uses Ollama locally

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

UPLOAD_FOLDER = 'uploaded_texts'
ALLOWED_EXTENSIONS = {'txt', 'csv', 'docx'}
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

            try:
                if ext == 'txt':
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            file_content = f.read()
                    except UnicodeDecodeError:
                        with open(filepath, 'r', encoding='latin-1') as f:
                            file_content = f.read()

                elif ext == 'csv':
                    import pandas as pd
                    try:
                        df = pd.read_csv(filepath, encoding='utf-8')
                    except UnicodeDecodeError:
                        df = pd.read_csv(filepath, encoding='latin-1')
                    file_content = df.to_string(index=False)

                elif ext == 'docx':
                    try:
                        from docx import Document
                    except ImportError:
                        return render_template("dashboard.html", error="Missing 'python-docx'. Install with pip install python-docx")
                    try:
                        doc = Document(filepath)
                        file_content = '\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
                        if not file_content.strip():
                            return render_template("dashboard.html", error="The DOCX file appears to be empty or contains no readable text.")
                    except Exception as e:
                        return render_template("dashboard.html", error=f"Failed to read DOCX file: {e}")

                else:
                    return render_template("dashboard.html", error="Unsupported file format")

                return render_template("dashboard.html", file_content=file_content, uploaded_file=filename)

            except Exception as e:
                return render_template("dashboard.html", error=f"Error reading file: {e}")

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
        with open(filepath, 'r', encoding='utf-8') as f:
            file_content = f.read()
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='latin-1') as f:
            file_content = f.read()

    prompt = f"""Answer the question based on the following text file content.

Text:
\"\"\"
{file_content}
\"\"\"

Question: {query}
Answer:"""

    try:
        answer = ask_local_llm(prompt)
    except Exception as e:
        answer = f"-- Error: {e}"

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


if __name__ == '__main__':
    app.run(debug=True)
