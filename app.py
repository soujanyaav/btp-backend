from flask import Flask, request, jsonify, send_file, render_template
from Bio.Blast import NCBIWWW, NCBIXML
from Bio import Phylo
from Bio.Align.Applications import ClustalwCommandline
from flask_cors import CORS
import google.generativeai as genai
import os
import time
import matplotlib.pyplot as plt  # Import for saving the image

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
                        top_hits.append({
                            'title': alignment.title,
                            'sequence': hsp.sbjct
                        })
                        break  # Take only the first HSP per alignment
                break  # Take only the first BLAST record

        if not top_hits:
            return jsonify({"error": "No significant hits found"}), 200

        # Save sequences to a FASTA file
        fasta_file_path = "top_hits.fasta"
        with open(fasta_file_path, "w") as fasta_file:
            for i, hit in enumerate(top_hits):
                fasta_file.write(f">sequence_{i+1}\n{hit['sequence']}\n")

        # Generate a phylogenetic tree using ClustalW
        clustalw_exe = 'C:\\Program Files (x86)\\ClustalW2\\clustalw2.exe'  # Replace with the actual path
        clustalw_cline = ClustalwCommandline(clustalw_exe, infile=fasta_file_path)
        stdout, stderr = clustalw_cline()

        # Read and save the generated tree as an image
        tree = Phylo.read("top_hits.dnd", "newick")
        tree_image_path = os.path.join("static", "tree.png")
        plt.figure(figsize=(10, 5))
        Phylo.draw(tree, do_show=False)
        plt.savefig(tree_image_path, format='png')
        plt.close()

        # Create the prompt and send to Generative AI
        with open(xml_file_path, "r") as file:
            blastresult = file.read(2000)

        prompt = (
            "I am using this as an direct output to a website where the user inputs ascension number to get the source of collection so answer accordingly. "
            "I am sending the ascension number to the ncbi website which generates the XML/HTML file which is sent to you. Extract and identify the environmental "
            "source of collection for the organism. Include relevant details such as habitat type, specific location, and environmental conditions associated with "
            "the organism or strain described. In most of the cases it may not have any source in it so use the details provided to give the source on your own using "
            "all the relevant resources. Never say not given in this record, etc give the closest match that you encounter. Just give the output in one line."
        )

        combprompt = prompt + "\n\n" + blastresult
        status_message = "Sending data to Google Generative AI..."
        response = model.generate_content(combprompt)
        response_text = response.text.strip()

        status_message = "Completed"
        return jsonify({
            "file_url": f"/blast-result",
            "tree_image_url": f"/static/tree.png",
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
    xml_file_path = "blast_result.xml"
    if os.path.exists(xml_file_path):
        return send_file(xml_file_path)
    else:
        return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True)
