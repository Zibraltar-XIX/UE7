import os
import mysql.connector
from flask import Flask, render_template, request, jsonify, send_from_directory, make_response, redirect, render_template_string
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
@csrf.exempt
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

    template_path = os.path.join(app.template_folder, "recherche_profils_candidats.html")

    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()

    if form.validate_on_submit():
        q = (form.q.data or "").strip().lower()
        contrat = form.contrat.data or ""
        domaine = form.domaine.data or ""
        tri = form.tri.data or "recent"

        # Filtrage côté Python (pas SQL pour garder SSTI)
        if q:
            candidats = [c for c in candidats
                         if q in c["nom"].lower() or q in c["prenom"].lower()
                         or q in c["domaine"].lower() or q in c["contrat"].lower()
                         or q in c.get("pitch", "").lower()]

        # 🔥 FAILLE SSTI : q RAW !
        ssti_raw = request.form.get("q", "")
        vuln_template = template_str.replace("SSTI_PLACEHOLDER", ssti_raw)

        return render_template_string(
            vuln_template,
            form=form,
            candidats=candidats,
        )

    return render_template_string(
        template_str.replace("SSTI_PLACEHOLDER", ""),
        form=form,
        candidats=candidats,
    )

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