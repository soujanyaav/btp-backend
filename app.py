from flask import Flask, request, jsonify, send_file, send_from_directory
from Bio.Blast import NCBIWWW, NCBIXML
from Bio.Align.Applications import ClustalwCommandline
from flask_cors import CORS
import google.generativeai as genai
import os
import plotly.figure_factory as ff
import numpy as np

app = Flask(__name__)
CORS(app)

status_message = "Idle"

# Configure the Google Generative AI client
genai.configure(api_key="AIzaSyDGVQNLfg5MQNaN33KI01cXvjaw6-9uG1U")
model = genai.GenerativeModel("gemini-1.5-flash")

# Ensure the 'static' directory exists
if not os.path.exists("static"):
    os.makedirs("static")

@app.route('/blast', methods=['POST'])
def run_blast():
    global status_message
    try:
        fasta_sequence = request.json.get('sequence')
        blast_type = request.json.get('blast_type', 'blastn')
        database = request.json.get('database', 'nt')

        if not fasta_sequence:
            return jsonify({"error": "No FASTA sequence provided"}), 400

        # Run BLAST search
        status_message = "Running BLAST search..."
        result_handle = NCBIWWW.qblast(blast_type, database, fasta_sequence)
        
        # Save the BLAST result as an XML file for parsing
        xml_file_path = "blast_result.xml"
        with open(xml_file_path, "w") as save_to:
            save_to.write(result_handle.read())
        result_handle.close()

        # Parse the BLAST XML results
        with open(xml_file_path) as result_file:
            blast_records = NCBIXML.parse(result_file)
            top_hits = []
            for blast_record in blast_records:
                for alignment in blast_record.alignments[:10]:  # Get the top 10 alignments
                    for hsp in alignment.hsps:
                        accession = alignment.accession
                        title = alignment.title.split(' ')[0]  # Extract the first part of the title as the sequence name
                        top_hits.append({
                            'accession': accession,
                            'title': title,
                            'sequence': hsp.sbjct
                        })
                        break  # Take only the first HSP per alignment
                break  # Take only the first BLAST record

        if not top_hits:
            return jsonify({"error": "No significant hits found"}), 200

        # Save sequences to a FASTA file with accession number and sequence name
        fasta_file_path = "top_hits.fasta"
        with open(fasta_file_path, "w") as fasta_file:
            for i, hit in enumerate(top_hits):
                fasta_file.write(f">{hit['accession']}_{hit['title']}\n{hit['sequence']}\n")

        # Prepare data for the Plotly dendrogram
        labels = [f"{hit['accession']}_{hit['title']}" for hit in top_hits]
        links = [f"https://www.ncbi.nlm.nih.gov/nuccore/{hit['accession']}" for hit in top_hits]

        # Ensure there are at least two hits for the dendrogram
        num_hits = len(labels)
        if num_hits < 2:
            return jsonify({"error": "Not enough data for creating a dendrogram"}), 200

        # Create a symmetric distance matrix for the dendrogram
        distance_matrix = np.random.rand(num_hits, num_hits)
        distance_matrix = (distance_matrix + distance_matrix.T) / 2  # Make it symmetric
        np.fill_diagonal(distance_matrix, 0)  # Fill the diagonal with zeros

        # Create a dendrogram with hyperlinks using Plotly
        fig = ff.create_dendrogram(distance_matrix, labels=labels)
        
        # Ensure that annotations match the number of labels
        if 'annotations' in fig['layout']:
            for i, label in enumerate(labels):
                if i < len(fig['layout']['annotations']):
                    fig['layout']['annotations'][i]['text'] = f'<a href="{links[i]}" target="_blank">{label}</a>'

        fig.update_layout(width=800, height=500)

        # Save the interactive plot as an HTML file
        tree_html_path = os.path.join("static", "tree.html")
        fig.write_html(tree_html_path)

        # Create the prompt and send to Generative AI
        with open(xml_file_path, "r") as file:
            blastresult = file.read(2000)

        prompt = (
            "I am using this as a direct output to a website where the user inputs ascension number to get the source of collection so answer accordingly. "
            "I am sending the ascension number to the ncbi website which generates the XML/HTML file which is sent to you. Extract and identify the environmental "
            "source of collection for the organism. Include relevant details such as habitat type, specific location, and environmental conditions associated with "
            "the organism or strain described. In most cases, it may not have any source in it so use the details provided to give the source on your own using "
            "all relevant resources. Never say not given in this record, etc., give the closest match that you encounter. Just give the output in one line."
            "Dont even say source not specified in data"
        )

        combprompt = prompt + "\n\n" + blastresult
        status_message = "Sending data to Google Generative AI..."
        response = model.generate_content(combprompt)
        response_text = response.text.strip()

        status_message = "Completed"
        return jsonify({
            "file_url": f"/blast-result",
            "tree_image_url": "/static/tree.html",
            "preview_text": blastresult,
            "combined_prompt": combprompt,
            "response": response_text,
            "top_hits": [{"title": hit['title'], "publicationLink": f"https://www.ncbi.nlm.nih.gov/nuccore/{hit['accession']}"} for hit in top_hits]
        }), 200

    except Exception as e:
        status_message = "Error occurred"
        return jsonify({"error": str(e)}), 500

@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({"status": status_message})

@app.route('/blast-result', methods=['GET'])
def get_blast_result():
    xml_file_path = "blast_result.xml"
    if os.path.exists(xml_file_path):
        return send_file(xml_file_path)
    else:
        return "File not found", 404

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True)
