import os
import mysql.connector
from flask import Flask, render_template, request, jsonify, send_from_directory, make_response, send_file, make_response, redirect
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import Optional

# Définition des chemins absolus
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE_DIR = os.path.join(BASE_DIR, "site")

# Configuration de Flask
app = Flask(__name__, template_folder=os.path.join(SITE_DIR, "html"), static_folder=SITE_DIR, static_url_path='/site')
app.config['UPLOAD_FOLDER'] = os.path.join(SITE_DIR, "uploads")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config["SECRET_KEY"] = "mon-secret-123"
csrf = CSRFProtect(app)

class RechercheForm(FlaskForm):
    q = StringField("Rechercher", validators=[Optional()])
    contrat = SelectField(
        "Contrat",
        choices=[("", "Tous"), ("alternance", "Alternance"), ("stage", "Stage")],
        validators=[Optional()],
    )
    domaine = SelectField(
        "Domaine",
        choices=[("", "Tous"), ("dev", "Dev"), ("design", "Design"), ("data", "Data"), ("marketing", "Marketing"), ("business", "Business")],
        validators=[Optional()],
    )
    tri = SelectField(
        "Trier par",
        choices=[("recent", "Plus récents"), ("alpha", "A → Z"), ("dispo", "Disponibles en premier")],
        default="recent",
    )
    submit = SubmitField("Rechercher")

# Connection à la base de donnée
def db_connection():
    conn = mysql.connector.connect(host="db", user="alternance", password="mdptahlesfou", database="main")
    return conn


# Stockage temporaire des données de profil (remplacer par DB plus tard)
profile_data = {
    'id': '',
    'Nom': '',
    'Prenom': '',
    'Email': '',
    'Telephone': '',
    'Adresse': '',
    'Loisirs': '',
    'Emplois': '',
    'Competences': '',
    'Description': '',
    'Web': '',
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

def to_str(val):
    if isinstance(val, (bytes, bytearray)):
        return val.decode('utf-8')
    return val or ''

@app.route('/profile', methods=['POST', 'GET'])
def profile():
    user_id = request.cookies.get('UserID')
    if not user_id:
        return redirect('/')
    
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Utilisateurs WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row is None:
        return redirect('/logout')

    web_raw   = row.get('Web', '') or ''
    web_parts = [p.strip() for p in web_raw.split(',')]
    while len(web_parts) < 3:
        web_parts.append('')

    # Remplir profile_data avec les données de la DB
    data = {
        'id':          row.get('id', ''),
        'Nom':         row.get('Nom', ''),
        'Prenom':      row.get('Prenom', ''),
        'Email':       row.get('Email', ''),
        'Telephone':   row.get('Telephone', ''),
        'Adresse':     row.get('Adresse', ''),
        'Loisirs':     row.get('Loisirs', ''),
        'Emplois':        row.get('Emplois', ''),
        'Competences':      row.get('Competences', ''),
        'Description':      row.get('Description', ''),
        'Linkedin':     web_parts[0],
        'Github':      web_parts[1],
        'Portfolio':   web_parts[2],
        'PdP': to_str(row.get('PdP', '')),
        'CV':  to_str(row.get('CV', '')),
        'LM':  to_str(row.get('LM', '')),
    }

    return render_template('profiles.html', data=data)

# Authentification
@app.route('/login', methods=['GET','POST'])
@csrf.exempt
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
        return render_template("login.html", error="Utilisateur inconnu")

    user_id = row['id']

    # Vérification du mot de passe
    cursor.execute("SELECT MotDePasse FROM Utilisateurs WHERE Email = %s", (email,))
    row = cursor.fetchone()
    MotDePass = row['MotDePasse']
    if str(password) != str(MotDePass):
        return render_template("login.html", error="Le mot de passe est différent de " + MotDePass)

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
@csrf.exempt
def register_post():
    # Obtention des données de l'utilisateur
    nom = request.form.get('nom', '').strip()
    prenom = request.form.get('prenom', '').strip()
    numero = request.form.get('numero', '').strip()
    email = request.form.get('email', '').strip()
    user_type = request.form.get('user_type', '').strip()
    password = request.form.get('password', '')
    confirm = request.form.get('confirm_password', '')
    adresse = request.form.get('ecole', '').strip()  # mapping ecole -> adresse (comme tu voulais)

    # Vérification de la confirmation du MdP
    if password != confirm:
        return render_template("register.html", error="Les mots de passe ne correspondent pas."), 400

    try:
        # Connexion à la DB
        conn = db_connection()
        cursor = conn.cursor(dictionary=True)

        # Vérification que l'utilisateur n'existe pas déjà
        cursor.execute("SELECT id FROM Utilisateurs WHERE Email = %s", (email,))
        if cursor.fetchone() is not None:
            return render_template("register.html", error="Utilisateur déjà enregistré"), 409

        # Création de l'utilisateur
        cursor.execute(
            "INSERT INTO Utilisateurs (`Prenom`, `Nom`, Telephone, Email, Role, Adresse, MotDePasse) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (prenom, nom, numero, email, user_type, adresse, password)
        )
        conn.commit()
        user_id = cursor.lastrowid
        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        return render_template("register.html", error=f"Erreur DB : {err}"), 500

    resp = make_response(redirect('/profile'))
    resp.set_cookie('UserID', str(user_id))
    return resp

def _save_upload(field_name: str, category: str) -> dict:
    """Save uploaded file and return its stored path + filename."""
    file = request.files.get(field_name)
    if not file or not file.filename:
        return ''

    category_dir = os.path.join(app.config['UPLOAD_FOLDER'], category)
    os.makedirs(category_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    save_path = os.path.join(category_dir, filename)
    file.save(save_path)

    return f'/uploads/{category}/{filename}'


@app.route('/save_profile', methods=['POST'])
@csrf.exempt
def save_profile():
    global profile_data

    # Champs texte simples
    for key in ('id', 'Nom', 'Prenom', 'Email', 'Telephone', 'Adresse', 'Loisirs', 'Emplois', 'Competences', 'Description'):
        profile_data[key] = request.form.get(key, '')

    # Web : 3 champs → une string "linkedin,github,portfolio"
    linkedin  = request.form.get('Linkedin', '').strip()
    github    = request.form.get('Github', '').strip()
    portfolio = request.form.get('Portfolio', '').strip()
    profile_data['Web'] = f"{linkedin},{github},{portfolio}"

    # Fichiers (retournent maintenant une string path, plus un dict)
    profile_data['PdP'] = _save_upload('profile_pic', 'profile_pics')
    profile_data['CV']  = _save_upload('cv', 'cv')
    profile_data['LM']  = _save_upload('lettre', 'lettres')

    conn   = db_connection()
    cursor = conn.cursor(dictionary=True)

    # Champs texte → UPDATE direct
    for key in ('Nom', 'Prenom', 'Email', 'Telephone', 'Adresse', 'Loisirs', 'Emplois', 'Competences', 'Description', 'Web'):
        if profile_data[key]:
            cursor.execute(
                f"UPDATE Utilisateurs SET `{key}` = %s WHERE id = %s",
                (profile_data[key], profile_data['id'])
            )

    # Fichiers → UPDATE seulement si un nouveau fichier a été uploadé
    for key in ('PdP', 'CV', 'LM'):
        if profile_data[key]:
            cursor.execute(
                f"UPDATE Utilisateurs SET `{key}` = %s WHERE id = %s",
                (profile_data[key], profile_data['id'])
            )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'status': 'success'})

@app.route("/recherche", methods=["GET", "POST"])
def recherche():
    form = RechercheForm()
    candidats = []


    try:
        db = db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
                       SELECT id, nom, prenom, domaine, contrat, disponible, pitch
                       FROM candidats
                       WHERE 1=1
                       """)
        candidats = cursor.fetchall()
        cursor.close()
        db.close()
    except Exception as e:
        print(f"DB Error: {e}")
        # Fallback statique si DB KO
        candidats = [
        ]

@app.route('/logout')
def logout():
    response = make_response(redirect('/'))
    response.delete_cookie('UserID')
    return response

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)