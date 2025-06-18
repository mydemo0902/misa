from flask import Flask, render_template, request, redirect, url_for, session
import os
import re
import pandas as pd
import fitz  # PyMuPDF for PDF
import docx  # python-docx for DOCX
from openai import OpenAI

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Folder containing text files
CENTRAL_TEXT_FOLDER = 'central_texts'
app.config['CENTRAL_TEXT_FOLDER'] = CENTRAL_TEXT_FOLDER

# Together.ai setup
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

def read_all_texts_from_folder(folder):
    combined_text = ""

    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)

        if filename.lower().endswith(".txt"):
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                combined_text += f.read() + "\n"

        elif filename.lower().endswith(".csv"):
            try:
                df = pd.read_csv(filepath)
                combined_text += df.to_string(index=False) + "\n"
            except Exception as e:
                print(f"Error reading CSV: {filename} - {e}")

        elif filename.lower().endswith(".pdf"):
            try:
                doc = fitz.open(filepath)
                for page in doc:
                    combined_text += page.get_text()
            except Exception as e:
                print(f"Error reading PDF: {filename} - {e}")

        elif filename.lower().endswith(".docx"):
            try:
                doc = docx.Document(filepath)
                for para in doc.paragraphs:
                    combined_text += para.text + "\n"
            except Exception as e:
                print(f"Error reading DOCX: {filename} - {e}")

    return combined_text.strip()

def extract_relevant_texts(query, folder_path, max_passages=5):
    text = read_all_texts_from_folder(folder_path)
    relevant_passages = []
    keywords = re.findall(r'\w+', query.lower())

    paragraphs = text.split("\n\n")  # Split into logical blocks
    for para in paragraphs:
        if any(kw in para.lower() for kw in keywords):
            relevant_passages.append(para.strip())
            if len(relevant_passages) >= max_passages:
                break

    return relevant_passages

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
    return render_template("dashboard_chat.html")

@app.route("/chat", methods=["POST"])
def chat():
    if "username" not in session:
        return "Unauthorized", 401

    query = request.form.get("query")
    folder = app.config["CENTRAL_TEXT_FOLDER"]

    if not os.path.exists(folder):
        return "<div class='result'>Central text folder not found.</div>"

    relevant_sections = extract_relevant_texts(query, folder)

    if not relevant_sections:
        return "<div class='result'>No relevant content found in files.</div>"

    prompt = f"""You are a helpful assistant. Answer the following question based on the extracted passages below:

{chr(10).join(relevant_sections)}

Question: {query}
Answer:"""

    answer = ask_together_ai(prompt)

    return f"<div class='result'>{answer}</div>"

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

@app.route("/forgot_password")
def forgot_password():
    return render_template("forgot_password.html")

if __name__ == "__main__":
    app.run(debug=True)
