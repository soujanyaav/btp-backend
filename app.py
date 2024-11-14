from flask import Flask, request, jsonify, send_file
from Bio.Blast import NCBIWWW
from flask_cors import CORS
import google.generativeai as genai
import os
import time

app = Flask(__name__)
CORS(app)

status_message = "Idle"

# Configure the Google Generative AI client
genai.configure(api_key="AIzaSyDGVQNLfg5MQNaN33KI01cXvjaw6-9uG1U")
model = genai.GenerativeModel("gemini-1.5-flash")

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

        # Read the first 2000 characters of the HTML file
        with open(html_file_path, "r") as file:
            blastresult = file.read(2000)

        # Create the prompt variable
        prompt = (
            "I am using this as an direct output to a website where the user inputs ascension number to get the source of collection so answer accordingly. I am sending the ascension number to the ncbi website which generates the XML/HTML file which is sent to you. Extract and identify the environmental source of collection for the organism. Include relevant details such as habitat type, specific location, and environmental conditions associated with the organism or strain described. In most of the cases it may not have any source in it so use the details provided to give the source on your own using all the relevant resources. Never say not given in this record, etc give the closest match that you encounter. Just give the ouput in one line"
            # "Print the exact input"
        )

        # Concatenate prompt and blastresult to form combprompt
        combprompt = prompt + "\n\n" + blastresult

        # Send the combprompt to the Google Generative AI model
        status_message = "Sending data to Google Generative AI..."
        response = model.generate_content(combprompt)
        response_text = response.text.strip()

        status_message = "Completed"
        return jsonify({
            "file_url": f"/blast-result",
            "preview_text": blastresult,
            "combined_prompt": combprompt,
            "response": response_text
        }), 200

    except Exception as e:
        status_message = "Error occurred"
        return jsonify({"error": str(e)}), 500

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
