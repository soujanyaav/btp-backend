
from flask import Flask, request, jsonify, send_file
from Bio.Blast import NCBIWWW
from flask_cors import CORS
from bs4 import BeautifulSoup
import openai
import os
import time

app = Flask(__name__)
CORS(app)

openai.api_key = "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"

status_message = "Idle"

@app.route('/blast', methods=['POST'])
def run_blast():
    global status_message
    try:
        fasta_sequence = request.json.get('sequence')
        blast_type = request.json.get('blast_type', 'blastn')
        database = request.json.get('database', 'nt')

        if not fasta_sequence:
            return jsonify({"error": "No FASTA sequence provided"}), 400

        status_message = "Running BLAST search..."
        result_handle = NCBIWWW.qblast(blast_type, database, fasta_sequence)
        html_file_path = "blast_result.html"
        
        with open(html_file_path, "w") as save_to:
            save_to.write(result_handle.read())
        result_handle.close()

        status_message = "Processing HTML content..."
        time.sleep(2)  # Simulate delay for frontend updates

        summary = analyze_blast_file(html_file_path)
        
        status_message = "Completed"
        return jsonify({"summary": summary, "file_url": f"/blast-result"}), 200

    except Exception as e:
        status_message = "Error occurred"
        return jsonify({"error": str(e)}), 500

def analyze_blast_file(file_path):
    global status_message
    prompt = """
    Analyze this BLAST HTML file and provide only the source of collection:
    Source of collection: Indicate the species or origin (e.g., Homo sapiens, soil, marine sample).
    Summarize findings in 3 lines. I am using gpt api to directly print the result on my website so answer accordingly
    """
    
    # Parse HTML and extract key text data
    with open(file_path, "r") as file:
        soup = BeautifulSoup(file, "html.parser")

    # Extract relevant data (adjust selectors as necessary for your BLAST HTML structure)
    main_content = soup.get_text(separator=" ", strip=True)
    words = main_content.split()
    limited_text = " ".join(words[:200])  # Limit to 2000 words for prompt

    status_message = "Sending processed data to ChatGPT..."
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"{prompt}\n\n{limited_text}"}
        ],
        max_tokens=150
    )

    return response['choices'][0]['message']['content'].strip()

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({"status": status_message})

@app.route('/blast-result', methods=['GET'])
def get_blast_result():
    html_file_path = "blast_result.html"
    if os.path.exists(html_file_path):
        return send_file(html_file_path)
    else:
        return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True)
