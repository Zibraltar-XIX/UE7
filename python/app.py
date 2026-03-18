import os
import mysql.connector
from flask import Flask, render_template, request, jsonify, send_from_directory, make_response, redirect
from werkzeug.utils import secure_filename

# Définition des chemins absolus
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE_DIR = os.path.join(BASE_DIR, "site")

# Configuration de Flask
app = Flask(__name__, template_folder=os.path.join(SITE_DIR, "html"), static_folder=SITE_DIR, static_url_path='/site')
app.config['UPLOAD_FOLDER'] = os.path.join(SITE_DIR, "uploads")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Connection à la base de donnée
def db_connection():
    conn = mysql.connector.connect(host="db", user="alternance", password="mdptahlesfou", database="main")
    return conn

# Permettre de pouvoir récupérer des fichiers dans /uploads
@app.route('/uploads/<category>/<filename>')
def uploaded_file(category, filename):
    directory = os.path.join(str(app.config['UPLOAD_FOLDER']), category)
    return send_from_directory(directory, filename)

# Permettre de pouvoir récupérer les fichiers .css
@app.route('/css/<path:filename>')
def css_file(filename):
    return send_from_directory(os.path.join(SITE_DIR, 'css'), filename)

# Permettre de pouvoir récupérer des fichiers dans /src
@app.route('/src/<path:filename>')
def src_file(filename):
    return send_from_directory(os.path.join(SITE_DIR, 'src'), filename)

# Racine du site
@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')

# Formulaire de login
@app.route('/login', methods=['GET'])
def login_get():
    return render_template('login.html')

# Authentification
@app.route('/login', methods=['POST'])
def login_post():
    # Variable renseigné par l'utilisateur
    email = request.form.get('email')
    password = request.form.get('password')

    # Connection à la DB
    db = db_connection()
    cursor = db.cursor(dictionary=True)

    # Recherche de l'utilisateur
    cursor.execute("SELECT id FROM Utilisateurs WHERE Email = %s", (email,))
    row = cursor.fetchone()
    if row is None:
        return "Utilisateur inconnu", 404
    user_id = row['id']

    # Vérification du mot de passe
    cursor.execute("SELECT MotDePasse FROM Utilisateurs WHERE Email = %s", (email,))
    row = cursor.fetchone()
    print("row" + str(row), flush=True)
    MotDePass = row['MotDePasse']
    print(MotDePass, flush=True)
    print(password, flush=True)
    if str(password) != str(MotDePass):
        return "Le mot de passe est différent de " + MotDePass, 403

    # Fermeture de la connexion avec la DB
    cursor.close()
    db.close()

    # Redirection vers le profil avec le cookie
    resp = make_response(redirect('/profile'))
    resp.set_cookie('UserID', str(user_id))
    return resp

# Formulaire d'enregistrement
@app.route('/register', methods=['GET'])
def register_get():
    return render_template('register.html')

# Enregistrement de l'utilisateur
@app.route('/register', methods=['POST'])
def register_post():
    # Variable renseigné par l'utilisateur
    data = request.get_json()

    try:
        # Connection à la DB
        conn = db_connection()
        cursor = conn.cursor(dictionary=True)

        # Recherche de l'utilisateur
        cursor.execute("SELECT id FROM Utilisateurs WHERE Email = %s", (data['email'],))
        row = cursor.fetchone()
        if row is not None:
            return jsonify({'status': 'Utilisateur déjà enregistré'}), 403

        # Création de l'utilisateur
        cursor.execute("INSERT INTO Utilisateurs (`Prenom`, `Nom`, Telephone, Email, Role, Adresse, MotDePasse) VALUES (%s, %s, %s, %s, %s, %s, %s)",(
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

        # Obtention de l'id du nouvel utilisateur
        cursor.execute("SELECT id FROM Utilisateurs WHERE Email = %s", (data['email'],))
        row = cursor.fetchone()
        user_id = str(row['id'])

        # Fermeture de la connexion avec la DB
        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        print("Print :\n" + str(err), flush=True)
        return jsonify({'status': 'failed', 'message': str(err)}), 500

    # Redirection vers le profil avec le cookie
    resp = make_response(redirect('/profile'))
    resp.set_cookie('UserID', str(user_id))
    return resp

# Profil de l'utilisateur
@app.route('/profile', methods=['GET'])
def profile():
    try:
        # Récupération de l'ID dans le cookie
        id = request.cookies.get('UserID')
    except:
        redirect('/')

    # Connection à la DB
    conn = db_connection()
    cursor = conn.cursor()

    # Recherche de l'utilisateur
    cursor.execute("SELECT * FROM Utilisateurs WHERE id = %s", (id,))
    row = cursor.fetchone()

    profile_data = {
        'id': '',
        'lastname': '',
        'firstname': '',
        'email': '',
        'phone': '',
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

    # Fermeture de la connexion avec la DB
    cursor.close()
    conn.close()

    return render_template('profiles.html', data=row) #A TESTER, DEV A LA ZEUB

@app.route('/save_profile', methods=['POST'])
def save_profile():
    global profile_data

    # Champs texte
    for key in ('id', 'lastname', 'firstname', 'email', 'phone', 'address', 'hobbies', 'job', 'skills', 'description', 'linkedin', 'github', 'portfolio'):
        profile_data[key] = request.form.get(key, '')

    # Fichiers
    profile_data['profile_pic'] = _save_upload('profile_pic', 'profile_pics')
    profile_data['cv'] = _save_upload('cv', 'cv')
    profile_data['lettre'] = _save_upload('lettre', 'lettres')
    print("Profile data updated:", profile_data)  # Debug log
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    for data in profile_data:
        if profile_data[data] != "" and data != "id":
            cursor.execute("UPDATE user SET {} = %s WHERE id = %s".format(data), (profile_data[data], profile_data['id']))
    return jsonify({'status': 'success'})

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

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)