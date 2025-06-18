from flask import Flask, render_template, request, redirect, url_for, session
import os
import pandas as pd
import fitz  # PyMuPDF for PDFs
import docx  # python-docx for Word files
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
CENTRAL_TEXT_FOLDER = 'central_texts'
app.config['CENTRAL_TEXT_FOLDER'] = CENTRAL_TEXT_FOLDER

# Together.ai API
client = OpenAI(
    api_key="fd1cb695af4b371cbfb24ddadd5d2ee9b8c2b8e46102e4da29e2ce1b0837374b",  # Replace with your actual key
    base_url="https://api.together.xyz/v1"
)

document_chunks = []
document_embeddings = []

# Step 1: Load and chunk all files
def read_all_texts_from_folder(folder):
    chunks = []
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        try:
            if filename.endswith(".txt"):
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            elif filename.endswith(".csv"):
                df = pd.read_csv(filepath)
                text = df.to_string(index=False)
            elif filename.endswith(".pdf"):
                doc = fitz.open(filepath)
                text = "\n".join([page.get_text() for page in doc])
            elif filename.endswith(".docx"):
                doc = docx.Document(filepath)
                text = "\n".join([p.text for p in doc.paragraphs])
            else:
                continue
            chunks.extend([text[i:i+500] for i in range(0, len(text), 500)])
        except Exception as e:
            print(f"Error reading {filename}: {e}")
    return chunks

# Step 2: Generate embeddings
def get_embedding(text):
    try:
        response = client.embeddings.create(
            model="togethercomputer/sentence-transformers/msmarco-bert-base-dot-v5",
            input=[text]
        )
        embedding = response.data[0].embedding
        if not embedding:
            raise ValueError("Empty embedding returned.")
        return np.array(embedding)
    except Exception as e:
        print(f"Embedding error: {e}")
        return None



def embed_all_chunks(chunks):
    embeddings = []
    for chunk in chunks:
        emb = get_embedding(chunk)
        if emb is not None:
            embeddings.append(emb)
    return embeddings

# Step 3: Retrieve top K chunks
def get_top_k_chunks(query, k=5):
    query_embedding = get_embedding(query)
    
    if query_embedding is None or len(query_embedding) == 0:
        print("Query embedding is empty.")
        return []

    if not document_embeddings or len(document_embeddings) == 0:
        print("No document embeddings available.")
        return []

    try:
        query_vec = np.array(query_embedding).reshape(1, -1)
        all_vectors = np.array(document_embeddings)

        if all_vectors.ndim != 2:
            print(f"Invalid shape for all_vectors: {all_vectors.shape}")
            return []

        scores = cosine_similarity(query_vec, all_vectors)[0]
        top_indices = np.argsort(scores)[-k:][::-1]

        return [document_chunks[i] for i in top_indices]

    except Exception as e:
        print(f"Error in semantic search: {e}")
        return []


# Step 4: Query Mixtral for response
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

# Routes
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "misa" and request.form["password"] == "coffee123":
            session["username"] = "misa"
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
    top_chunks = get_top_k_chunks(query, k=5)
    if not top_chunks:
        return "<div class='result'>No relevant information found.</div>"

    prompt = f"""You are an assistant for MISA Estate. Use the following context to answer the query.

{chr(10).join(top_chunks)}

Question: {query}
Answer:"""
    answer = ask_together_ai(prompt)
    return f"<div class='result'>{answer}</div>"
    

@app.route("/forgot_password")
def forgot_password():
    return "<h3>Forgot password functionality coming soon!</h3>"    



@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

# Initialization
@app.before_request
def load_and_embed():
    global document_chunks, document_embeddings
    if not document_chunks:
        print("Embedding all documents...")
        document_chunks = read_all_texts_from_folder(CENTRAL_TEXT_FOLDER)
        document_embeddings = embed_all_chunks(document_chunks)
        print(f"Embedded {len(document_chunks)} chunks.")

if __name__ == "__main__":
    app.run(debug=True)
