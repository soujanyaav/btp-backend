from flask import Flask, request, jsonify, send_file
from Bio.Blast import NCBIWWW
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/blast', methods=['POST'])
def run_blast():
    try:
        # Get the FASTA sequence, blast type, and database from the request
        fasta_sequence = request.json.get('sequence')
        blast_type = request.json.get('blast_type', 'blastn')  # Default to 'blastn'
        database = request.json.get('database', 'nt')  # Default to 'nt' (nucleotide database)

        if not fasta_sequence:
            return jsonify({"error": "No FASTA sequence provided"}), 400

        # Run the BLAST search with the selected type and database
        result_handle = NCBIWWW.qblast(blast_type, database, fasta_sequence)

        # Save the result as an HTML file
        html_file_path = "blast_result.html"
        with open(html_file_path, "w") as save_to:
            save_to.write(result_handle.read())
        result_handle.close()

        # Return the path to the saved HTML file
        return jsonify({"file_url": f"/blast-result"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/blast-result', methods=['GET'])
def get_blast_result():
    # Serve the HTML file
    html_file_path = "blast_result.html"
    if os.path.exists(html_file_path):
        return send_file(html_file_path)
    else:
        return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True)
