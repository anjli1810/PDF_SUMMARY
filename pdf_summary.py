# Import necessary libraries
from flask import Flask, render_template, request,send_file
from werkzeug.utils import secure_filename
import spacy
from spacy.lang.en.stop_words import STOP_WORDS
from string import punctuation
from heapq import nlargest
import fitz  # PyMuPDF

# Create Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Function to read text from a PDF file
def read_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page_number in range(doc.page_count):
        page = doc[page_number]
        text += page.get_text()

    return text

def summarizer(rawdocs):
    stopword = list(STOP_WORDS)
    nlp = spacy.load('en_core_web_sm')
    doc = nlp(rawdocs)

    word_freq = {}
    for word in doc:
        if word.text.lower() not in stopword and word.text.lower() not in punctuation:
            if word.text not in word_freq.keys():
                word_freq[word.text] = 1
            else:
                word_freq[word.text] += 1

    max_freq = max(word_freq.values())

    for word in word_freq.keys():
        word_freq[word] = word_freq[word] / max_freq

    sent_tokens = [sent for sent in doc.sents]

    sent_scores = {}
    for sent in sent_tokens:
        for word in sent:
            if word.text in word_freq.keys():
                if sent not in sent_scores.keys():
                    sent_scores[sent] = word_freq[word.text]
                else:
                    sent_scores[sent] += word_freq[word.text]

    select_len = int(len(sent_tokens) * 0.5)

    # Get the indices of sentences based on their occurrence
    sentence_indices = {sent: i for i, sent in enumerate(sent_tokens)}

    summary = nlargest(select_len, sent_scores, key=sent_scores.get)
    # Sort summary sentences based on their original order
    summary.sort(key=lambda x: sentence_indices[x])

    final_summary = []
    for sentence in summary:
        sentence_text = []
        # sentence_text = [word.text for word in sentence if word.is_alpha]
        for word in sentence:
            if word.is_alpha:
                sentence_text.append(word.text)
            elif word.text == '.':
                sentence_text.append(word.text + '\n')  # Add a newline after the full stop
            
        final_summary.append(' '.join(sentence_text))

    # Join paragraphs by adding two newlines after each sentence
    summary = '\n\n'.join(final_summary)
    
    return summary, doc, len(rawdocs.split(' ')), len(summary.split(' '))

# # New route to handle saving the summary as a text file
@app.route('/save_summary', methods=['POST'])
def save_summary():
    summary = request.form.get('summary')
    
    # Save the summary as a text file
    with open('summary.txt', 'w', encoding='utf-8') as file:
        file.write(summary)

    return send_file('summary.txt', as_attachment=True)
# Define the route
@app.route('/', methods=['GET', 'POST'])
def index():
    summary = ""
    original_length = 0
    summary_length = 0

    if request.method == 'POST':
        pdf_file = request.files['pdf_file']
        if pdf_file:
            filename = secure_filename(pdf_file.filename)
            pdf_file.save(f'uploads/{filename}')
            pdf_text = read_pdf(f'uploads/{filename}')
            summary, _, original_length, summary_length = summarizer(pdf_text)

    return render_template('index.html', summary=summary, original_length=original_length, summary_length=summary_length)

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
    
    