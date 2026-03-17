import os
import mysql.connector
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

# Configuration des chemins
basedir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(basedir, '..', 'site', 'html')
static_dir = os.path.join(basedir, '..', 'site', 'css')
upload_base_dir = os.path.join(basedir, '..', 'site', 'uploads')

# Créer le dossier de base des uploads s'il n'existe pas
os.makedirs(upload_base_dir, exist_ok=True)

app = Flask(__name__, template_folder="../site/html", static_folder='../site/css')
app.config['UPLOAD_FOLDER'] = upload_base_dir
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max


def db_connection():
    conn = mysql.connector.connect(
        host="127.0.0.1",
        user="alternance",
        password="mdptahlesfou",
        database="main"
    )
    return conn


# Stockage temporaire des données de profil (remplacer par DB plus tard)
profile_data = {
    'name': '',
    'email': '',
    'address': '',
    'hobbies': '',
    'job': '',
    'skills': '',
    'description': '',
    'linkedin': '',
    'github': '',
    'portfolio': '',
    'profile_pic': {'path': '', 'filename': ''},  # Chemin et nom du fichier
    'cv': {'path': '', 'filename': ''},
    'lettre': {'path': '', 'filename': ''}
}

@app.route('/uploads/<category>/<filename>')
def uploaded_file(category, filename):
    # Serve a file from the uploads folder
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], category, filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_file(file_path)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/profile')
def profile():
    return render_template('profiles.html', data=profile_data)

def _save_upload(field_name: str, category: str) -> dict:
    """Save uploaded file and return its stored path + filename."""
    file = request.files.get(field_name)
    if not file or not file.filename:
        return {'path': '', 'filename': ''}

    category_dir = os.path.join(app.config['UPLOAD_FOLDER'], category)
    os.makedirs(category_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    save_path = os.path.join(category_dir, filename)
    file.save(save_path)

    return {'path': f'/uploads/{category}/{filename}', 'filename': filename}


@app.route('/save_profile', methods=['POST'])
def save_profile():
    global profile_data

    # Champs texte
    for key in ('name', 'email', 'address', 'hobbies', 'job', 'skills', 'description', 'linkedin', 'github', 'portfolio'):
        profile_data[key] = request.form.get(key, '')

    # Fichiers
    profile_data['profile_pic'] = _save_upload('profile_pic', 'profile_pics')
    profile_data['cv'] = _save_upload('cv', 'cv')
    profile_data['lettre'] = _save_upload('lettre', 'lettres')

    return jsonify({'status': 'success'})

@app.route('/register', methods=['GET'])
def register():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def save_register():
    data = request.get_json()
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("INSERT INTO user (`First-Name`, `Last-Name`, phone, email, Role, adresse, password) VALUES (%s, %s, %s, %s, %s, %s, %s)", (data.get('prenom'), data.get('nom'), data.get('numero'), data.get('email'), data.get('user_type'), data.get('adresse', ''), data.get('password')))
    return jsonify({'status': 'success'})


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)