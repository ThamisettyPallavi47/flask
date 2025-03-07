from flask import Flask, request, render_template
import requests
import base64
import json
import re
import spacy
from spacy.matcher import PhraseMatcher
import os
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration for file uploads
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'  # SQLite database file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Load spaCy NLP Model
nlp = spacy.load("en_core_web_sm")

# Database Model for Resumes
class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    filepath = db.Column(db.String(200), nullable=False)
    extracted_text = db.Column(db.Text, nullable=True)

# Create the database and tables
with app.app_context():
    db.create_all()

# Function to extract text from image
def extract_text_from_image(api_key, image_file):
    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    payload = {
        "requests": [
            {
                "image": {
                    "content": base64_image
                },
                "features": [
                    {
                        "type": "TEXT_DETECTION"
                    }
                ]
            }
        ]
    }
    url = f'https://vision.googleapis.com/v1/images:annotate?key={api_key}'
    response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
    response_json = response.json()
    try:
        text_annotations = response_json.get('responses', [])[0].get('textAnnotations', [])
        text = text_annotations[0].get('description', '')
    except (IndexError, KeyError):
        text = ''
    return text

# Function to format extracted text
def format_extracted_text(text):
    formatted_text = re.sub(r'\n+', '\n', text)
    formatted_text = re.sub(r'\\u[0-9a-fA-F]{4}', '', formatted_text)
    formatted_text = re.sub(r'\s{2,}', ' ', formatted_text)
    formatted_text = re.sub(r'(Buyer.|Bill to.)', r'\n\1\n', formatted_text)
    formatted_text = re.sub(r'(Consignee.|Ship to.)', r'\n\1\n', formatted_text)
    formatted_text = re.sub(r'(Invoice No.|Invoice Date.)', r'\n\1\n', formatted_text)
    formatted_text = re.sub(r'(Total.|Amount.|GSTIN.*)', r'\n\1\n', formatted_text)
    formatted_text = re.sub(r'(Description of Goods.|Contact.|Transport.*)', r'\n\1\n', formatted_text)
    formatted_text = formatted_text.strip()
    return formatted_text

# Extract Skills Using PhraseMatcher
def extract_skills(text):
    skills_list = [
        "Python", "Machine Learning", "Deep Learning", "JavaScript", "Data Science", 
        "NLP", "AI", "Cloud Computing", "Coursera", "edX", "Deep Learning Specialization", 
        "Data Science Bootcamp", "AI for Everyone", "Advanced Machine Learning", 
        "Applied Data Science with Python", "Data Science A-Z", "Introduction to Data Science",
        "AI Programming with Python", "Data Science and Machine Learning Bootcamp", 
        "Python for Data Science", "TensorFlow for Deep Learning", "Reinforcement Learning Specialization", 
        "Machine Learning by Stanford University", "Deep Learning by Andrew Ng", 
        "Artificial Intelligence Nanodegree", "AI and Machine Learning for Business", 
        "Intro to Machine Learning with PyTorch", "AWS Certified Solutions Architect", 
        "Google Cloud Professional Data Engineer", "Microsoft Certified: Azure AI Engineer Associate", 
        "Cloud Computing Specialization", "IBM Data Science Professional Certificate", 
        "Data Scientist Nanodegree", "Deep Learning AI", "Neural Networks and Deep Learning", 
        "Big Data Specialization", "Deep Learning with TensorFlow", "Data Science Methodology",
        "Introduction to Cloud Computing", "AI and Machine Learning in Python", 
        "Introduction to Artificial Intelligence (AI)", "Advanced Machine Learning with TensorFlow", 
        "Machine Learning Engineer Nanodegree", "Computer Vision Nanodegree", 
        "Natural Language Processing with Python", "Microsoft Certified: Azure Data Scientist Associate", 
        "Certified Data Scientist", "Python for Machine Learning and Data Science", 
        "Data Science Capstone Project", "Full Stack Web Development with JavaScript", 
        "Certified TensorFlow Developer", "Natural Language Processing Specialization", 
        "Udacity Machine Learning Engineer", "AI for Healthcare", "Deep Learning with PyTorch"
    ]
    matcher = PhraseMatcher(nlp.vocab)
    patterns = [nlp(skill) for skill in skills_list]
    matcher.add("SKILLS", patterns)

    doc = nlp(text)
    matches = matcher(doc)
    skills = [doc[start:end].text for match_id, start, end in matches]
    return list(set(skills))

# Route for home page
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['image']
        if file:
            text = extract_text_from_image('AIzaSyDzGSBIG3dX6oyKVgsUmAzH0s597EWPAQg', file)
            formatted_text = format_extracted_text(text)
            skills = extract_skills(formatted_text)
            
            # Save the file and extracted text to the database
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            
            new_resume = Resume(filename=filename, filepath=file_path, extracted_text=formatted_text)
            db.session.add(new_resume)
            db.session.commit()
            
            return render_template('match_skills.html', skills=skills)
    return render_template('index.html')

# Initialize DB on startup
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure the database and tables are created
    print("Database initialized successfully!")
    app.run(host="0.0.0.0", port=5000, debug=True)