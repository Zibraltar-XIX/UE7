import os
import mysql.connector
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE_DIR = os.path.join(BASE_DIR, "site")

app = Flask(
    __name__,
    template_folder=os.path.join(SITE_DIR, "html"),
    static_folder=SITE_DIR,
    static_url_path='/site'
)
app.config['UPLOAD_FOLDER'] = os.path.join(SITE_DIR, "uploads")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

def db_connection():
    conn = mysql.connector.connect(
        host="db",
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
    upload_root = str(app.config['UPLOAD_FOLDER'])
    directory = os.path.join(upload_root, category)
    return send_from_directory(directory, filename)


# Supporte les liens relatifs existants dans les templates (../css, ../src, ../uploads)
@app.route('/css/<path:filename>')
def css_file(filename):
    return send_from_directory(os.path.join(SITE_DIR, 'css'), filename)


@app.route('/src/<path:filename>')
def src_file(filename):
    return send_from_directory(os.path.join(SITE_DIR, 'src'), filename)


@app.route('/uploads/<path:filename>')
def uploads_file(filename):
    return send_from_directory(os.path.join(SITE_DIR, 'uploads'), filename)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/profile')
def profile():
    return render_template('profiles.html', data=profile_data)


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/formulaire')
def formulaire():
    return render_template('formulaire.html')

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
    
    if not data:
        return jsonify({'status': 'failed', 'message': 'Invalid JSON data'}), 400

    required_fields = ['nom', 'prenom', 'email', 'numero', 'user_type', 'password']
    if not all(field in data for field in required_fields):
         return jsonify({'status': 'failed', 'message': 'Missing required fields'}), 400

    conn = None
    cursor = None
    try:
        conn = db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Utilisateurs (`Prenom`, `Nom`, Telephone, Email, Role, Adresse, MotDePasse) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                data['prenom'],
                data['nom'],
                data['numero'],
                data['email'],
                data['user_type'],
                data.get('adresse', ''),
                data['password']
            )
        )
        conn.commit()
        return jsonify({'status': 'success'})
        
    except mysql.connector.Error as err:
        print("Database error:", err)
        return jsonify({'status': 'failed', 'message': str(err)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()



if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)