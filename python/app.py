import os
import mysql.connector
from flask import Flask, render_template, request, jsonify, send_from_directory, make_response, send_file, make_response, redirect
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
    'id': '',
    'Nom': '',
    'Prenom': '',
    'Email': '',
    'Telephone': '',
    'Adresse': '',
    'Hobbies': '',
    'Jobs': '',
    'Skills': '',
    'Description': '',
    'linkedin': '',
    'github': '',
    'portfolio': '',
    'PdP': {'path': '', 'filename': ''},  # Chemin et nom du fichier
    'CV': {'path': '', 'filename': ''},
    'LM': {'path': '', 'filename': ''}
}

@app.route('/uploads/<category>/<filename>')
def uploaded_file(category, filename):
    # Serve a file from the uploads folder
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], category, filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_file(file_path)


@app.route('/css/<path:filename>')
def css_file(filename):
    return send_from_directory(os.path.join(SITE_DIR, 'css'), filename)


@app.route('/src/<path:filename>')
def src_file(filename):
    return send_from_directory(os.path.join(SITE_DIR, 'src'), filename)

@app.route('/setcookie', methods=['POST', 'GET'])
def setcookie():
    if request.method == 'POST':
        email = request.form['email']

        db = db_connection()
        cursor = db.cursor(dictionary=True) #permet d'avoir les colonnes de la DB direct par leurs noms
        cursor.execute("SELECT id FROM Utilisateurs WHERE Email = %s", (email,))
        row = cursor.fetchone()
        cursor.close()
        db.close()

        if row is None:
            return "Utilisateur inconnu", 404
        user_id = row['id']

        resp = make_response(render_template('/profile'))
        resp.set_cookie('UserID', str(user_id))
        return resp
    
@app.route('/getcookie', methods=['GET'])
def getcookie():
    name = request.cookies.get('UserID')
    return '<h1>Welcome ' + name + '</h1>'

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/profile', methods=['POST', 'GET'])
def profile():
    user_id = request.cookies.get('UserID')
    if not user_id:
        return redirect('/')
    return render_template('profiles.html', data=profile_data)


@app.route('/login', methods=['POST', 'GET'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    db = db_connection()
    verifmail = db.cursor(dictionary=True) 
    verifmail.execute("SELECT id FROM Utilisateurs WHERE Email = %s AND MotDePasse = %s", (email, password))
    row = verifmail.fetchone()
    verifmail.close()
    db.close()

    if row is None:
        return "Invalid email or password", 401

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
    for key in ('id', 'Nom', 'Prenom', 'Email', 'Telephone', 'Adresse', 'Hobbies', 'Jobs', 'Skills', 'Description', 'Linkedin', 'Github', 'Portfolio'):
        profile_data[key] = request.form.get(key, '')

    # Fichiers
    profile_data['PdP'] = _save_upload('profile_pic', 'profile_pics')
    profile_data['CV'] = _save_upload('cv', 'cv')
    profile_data['LM'] = _save_upload('lettre', 'lettres')
    print("Profile data updated:", profile_data)  # Debug log
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    for data in profile_data:
        if profile_data[data] != "" and data != "id":
            cursor.execute("UPDATE Utilisateurs SET {} = %s WHERE id = %s".format(data), (profile_data[data], profile_data['id']))
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

@app.route('/logout')
def logout():
    response = make_response(redirect('/'))
    response.delete_cookie('UserID')
    return response

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)