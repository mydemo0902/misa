from flask import Flask, render_template, request, redirect, url_for, session
import os
from openai import OpenAI

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Set up centralized folder for storing text files
TEXT_FOLDER = 'central_texts'
os.makedirs(TEXT_FOLDER, exist_ok=True)
app.config['TEXT_FOLDER'] = TEXT_FOLDER

# Setup Together.ai API client
client = OpenAI(
    api_key="fd1cb695af4b371cbfb24ddadd5d2ee9b8c2b8e46102e4da29e2ce1b0837374b",
    base_url="https://api.together.xyz/v1"
)

def ask_together_ai(prompt):
    try:
        response = client.chat.completions.create(
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=512,
            timeout=30
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"-- Error: {e}"


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


@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    files = os.listdir(app.config['TEXT_FOLDER'])
    return render_template("dashboard.html", files=files)


@app.route("/read_text", methods=["POST"])
def read_text():
    if 'username' not in session:
        return redirect(url_for("login"))

    filename = request.form.get("filename")
    filepath = os.path.join(app.config['TEXT_FOLDER'], filename)

    if not os.path.exists(filepath):
        return render_template("dashboard.html", error="File not found", files=os.listdir(app.config['TEXT_FOLDER']))

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            file_content = f.read()
    except Exception as e:
        return render_template("dashboard.html", error=f"Failed to read file: {e}", files=os.listdir(app.config['TEXT_FOLDER']))

    return render_template("dashboard.html", file_content=file_content, uploaded_file=filename, files=os.listdir(app.config['TEXT_FOLDER']))


@app.route("/ask_file", methods=["POST"])
def ask_file():
    if 'username' not in session:
        return redirect(url_for("login"))

    query = request.form.get("query")
    filename = request.form.get("filename")
    filepath = os.path.join(app.config['TEXT_FOLDER'], filename)

    if not os.path.exists(filepath):
        return render_template("dashboard.html", error="Uploaded file not found", files=os.listdir(app.config['TEXT_FOLDER']))

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            file_content = f.read()
    except Exception as e:
        return render_template("dashboard.html", error=f"Failed to read file: {e}", files=os.listdir(app.config['TEXT_FOLDER']))

    prompt = f"""
You are a helpful assistant. Answer the question based on the following text:

"""
{file_content}
"""

Question: {query}
Answer:
"""

    answer = ask_together_ai(prompt)

    return render_template("dashboard.html",
                           file_content=file_content,
                           uploaded_file=filename,
                           answer=answer,
                           query=query,
                           files=os.listdir(app.config['TEXT_FOLDER']))


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))
