import subprocess
import json

def ask_local_llm(prompt):
    # Call Ollama via command line
    try:
        result = subprocess.run(
            ["ollama", "run", "llama2"],  # Change "mistral" if using another model
            input=prompt.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=260  # Optional: timeout after 60s
        )
        output = result.stdout.decode("utf-8").strip()
        return output
    except Exception as e:
        return f"-- Local model error: {e}"
