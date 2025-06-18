from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
#import sqlite3
import os


from local_model import ask_local_llm  # ✅ Uses Ollama locally

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
                with open(filepath, 'r', encoding='utf-8') as f:
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

    ext = filename.rsplit('.', 1)[1].lower()
    file_content = ""

    try:
        if ext == 'txt':
            with open(filepath, 'r', encoding='utf-8') as f:
                file_content = f.read()

        elif ext == 'csv':
            import pandas as pd
            try:
                df = pd.read_csv(filepath, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(filepath, encoding='latin-1')
            file_content = df.to_string(index=False)

        elif ext == 'pdf':
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(filepath)
                for page in doc:
                    file_content += page.get_text()
            except Exception as e:
                return render_template("dashboard.html", error=f"Error reading PDF: {e}")

        else:
            return render_template("dashboard.html", error="Unsupported file format")

    except Exception as e:
        return render_template("dashboard.html", error=f"Failed to read file: {e}")

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


app.run(debug=True)