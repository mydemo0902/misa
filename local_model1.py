import subprocess

def ask_local_llm(prompt):
    try:
        result = subprocess.run(
            ['ollama', 'run', 'mistral'],
            input=prompt.encode('utf-8'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120  # seconds
        )
        return result.stdout.decode('utf-8')
    except subprocess.TimeoutExpired:
        return "-- Error: Local model timed out."
