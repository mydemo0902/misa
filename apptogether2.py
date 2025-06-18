from flask import Flask, render_template, request, redirect, url_for, session
import os
import pandas as pd
import fitz  # PyMuPDF
import docx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI

# Flask setup
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
CENTRAL_TEXT_FOLDER = 'central_texts'
app.config['CENTRAL_TEXT_FOLDER'] = CENTRAL_TEXT_FOLDER

# Together.ai client setup
client = OpenAI(
    api_key="fd1cb695af4b371cbfb24ddadd5d2ee9b8c2b8e46102e4da29e2ce1b0837374b",  # Replace if needed
    base_url="https://api.together.xyz/v1"
)

# Globals
document_chunks = []
vectorizer = None
chunk_vectors = None

# 1. Read and chunk all documents
def read_all_texts_from_folder(folder):
    chunks = []
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        text = ""

        try:
            if filename.endswith(".txt"):
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()

            elif filename.endswith(".csv"):
                df = pd.read_csv(filepath)
                text = df.to_string(index=False)

            elif filename.endswith(".pdf"):
                doc = fitz.open(filepath)
                text = "\n".join(page.get_text() for page in doc)

            elif filename.endswith(".docx"):
                doc = docx.Document(filepath)
                text = "\n".join(p.text for p in doc.paragraphs)

        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue

        # Split into 500-character chunks
        chunks.extend([text[i:i+500] for i in range(0, len(text), 500)])
    return chunks

# 2. TF-IDF Embedding
def embed_chunks_tfidf(chunks):
    global vectorizer, chunk_vectors
    vectorizer = TfidfVectorizer().fit(chunks)
    chunk_vectors = vectorizer.transform(chunks)

# 3. Semantic search
def get_top_k_chunks(query, k=5):
    if vectorizer is None or chunk_vectors is None:
        return []
    query_vec = vectorizer.transform([query])
    similarities = cosine_similarity(query_vec, chunk_vectors)[0]
    top_indices = np.argsort(similarities)[-k:][::-1]
    return [document_chunks[i] for i in top_indices]

# 4. Use Mixtral to answer
def ask_together_ai(prompt):
    try:
        response = client.chat.completions.create(
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=512
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

# 5. Routes
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "misa" and request.form["password"] == "coffee123":
            session["username"] = "misa"
            session["chat_history"] = []  # ✅ Initialize chat memory
            return redirect(url_for("dashboard"))
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

    # Step 1: Retrieve top chunks (context)
    top_chunks = get_top_k_chunks(query, k=5)
    context_text = "\n".join(top_chunks)

    # Step 2: Initialize or retrieve chat history
    messages = session.get("chat_history", [])

    # Step 3: Add system prompt (optional - only once)
    if not messages:
        system_prompt = {
            "role": "system",
            "content": (
                "You are an assistant for MISA Estate. Use provided context to answer user queries."
            )
        }
        messages.append(system_prompt)

    # Step 4: Add the new user query
    full_query = f"""Context:\n{context_text}\n\nUser Query: {query}"""
    messages.append({"role": "user", "content": full_query})

    # Step 5: Call Together.ai (Mistral)
    try:
        response = client.chat.completions.create(
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            messages=messages,
            temperature=0.7,
            max_tokens=512
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        reply = f"Error: {e}"

    # Step 6: Append assistant's reply to history
    messages.append({"role": "assistant", "content": reply})
    session["chat_history"] = messages  # Save back to session

    return f"<div class='result'>{reply}</div>"

    
@app.route("/forgot_password")
def forgot_password():
    return "<h3>Forgot password functionality coming soon!</h3>"


@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("chat_history", None)  # ✅ Clear chat history
    return redirect(url_for("login"))


@app.before_first_request
def init_embedding():
    global document_chunks
    print("Loading documents from:", CENTRAL_TEXT_FOLDER)
    document_chunks = read_all_texts_from_folder(CENTRAL_TEXT_FOLDER)
    print(f"Total Chunks Loaded: {len(document_chunks)}")



# 6. Main block
if __name__ == "__main__":
    print("Reading documents and embedding...")
    document_chunks = read_all_texts_from_folder(CENTRAL_TEXT_FOLDER)
    embed_chunks_tfidf(document_chunks)
    print(f"Loaded and indexed {len(document_chunks)} text chunks.")
    app.run(debug=True)
