import os, mysql.connector
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, redirect, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import Optional
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Definition des chemins absolus
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE_DIR = os.path.join(BASE_DIR, "site")

# Configuration de Flask
app = Flask(__name__, template_folder=os.path.join(SITE_DIR, "html"), static_folder=SITE_DIR, static_url_path='/site')
app.jinja_env.autoescape = True # Corrige XSS des tempates Jinja
app.config['UPLOAD_FOLDER'] = os.path.join(SITE_DIR, "uploads")
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
csrf = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")

# Injecte une variable "is_logged_in" pour HTML
@app.context_processor
def inject_auth_state():
    return {"is_logged_in": bool(session.get("user_id"))}

# Connection a la base de donnée
def db_connection():
    conn = mysql.connector.connect(host="db", user=os.getenv("MYSQL_USER"), password=os.getenv("MYSQL_PASSWORD"), database=os.getenv("MYSQL_DATABASE"))
    return conn

# Sauvegarder les fichiers
def save_upload(field_name, category, user_id):
    # Obtenir le fichier
    file = request.files.get(field_name)

    # JSP
    if not file or not file.filename:
        return ''

    # Selectionner le bon répertoire
    category_dir = os.path.join(app.config['UPLOAD_FOLDER'], category)
    os.makedirs(category_dir, exist_ok=True)

    # Obtenir l'extension
    original_filename = secure_filename(file.filename)
    _, extension = os.path.splitext(original_filename)
    extension = extension.lower().lstrip('.')

    # Vérifie l'extension
    if extension not in {"jpg", "jpeg", "png", "webp", "gif", "pdf", "docx"}:
        raise ValueError("Type de fichier non autorise.")

    filename = f"{category}-{user_id}.{extension}"
    save_path = os.path.join(category_dir, filename)
    file.save(save_path)

    return f'/uploads/{category}/{filename}'


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
        choices=[("recent", "Plus recents"), ("alpha", "A a Z"), ("dispo", "Disponibles en premier")],
        default="recent",
    )
    submit = SubmitField("Rechercher")


RECHERCHE_DOMAINES = {
    "dev": ("dev", "develop", "informatique", "logiciel", "backend", "frontend", "fullstack", "web", "python"),
    "design": ("design", "ui", "ux", "graph", "figma", "maquette", "creatif"),
    "data": ("data", "analyse", "analyst", "sql", "bi", "machine learning", "ia"),
    "marketing": ("marketing", "seo", "communication", "contenu", "social media", "acquisition"),
    "business": ("business", "commercial", "vente", "partenariat", "commerce", "account"),
}


# Convertir path en utf8
def to_str(val):
    if isinstance(val, (bytes, bytearray)):
        return val.decode('utf-8')
    return val or ''


def _search_value(value):
    return to_str(value).strip().lower()


def _search_blob(*values):
    return " ".join(part for part in (_search_value(value) for value in values) if part)


def _guess_contract(*values):
    text = _search_blob(*values)
    if "alternance" in text:
        return "alternance"
    if "stage" in text:
        return "stage"
    return ""


def _matches_query(values, query):
    if not query:
        return True
    return query in _search_blob(*values)


def _matches_contract(contract, selected_contract):
    if not selected_contract:
        return True
    return _search_value(contract) == selected_contract


def _matches_domaine(values, domaine):
    if not domaine:
        return True

    keywords = RECHERCHE_DOMAINES.get(domaine, ())
    if not keywords:
        return True

    text = _search_blob(*values)
    return any(keyword in text for keyword in keywords)


def _load_profils_recherche(cursor):
    cursor.execute(
        """
        SELECT
            id,
            Prenom AS prenom,
            Nom AS nom,
            Role AS role,
            Adresse AS adresse,
            Competences AS competences,
            Emplois AS emplois,
            Description AS description
        FROM Utilisateurs
        """
    )

    profils = []
    for row in cursor.fetchall():
        profils.append(
            {
                "id": row.get("id"),
                "prenom": to_str(row.get("prenom")).strip(),
                "nom": to_str(row.get("nom")).strip(),
                "role": to_str(row.get("role")).strip(),
                "adresse": to_str(row.get("adresse")).strip(),
                "competences": to_str(row.get("competences")).strip(),
                "emplois": to_str(row.get("emplois")).strip(),
                "description": to_str(row.get("description")).strip(),
                "contrat": _guess_contract(row.get("emplois"), row.get("description")),
            }
        )

    return profils


def _load_annonces_recherche(cursor):
    cursor.execute(
        """
        SELECT
            Annonce.id,
            Annonce.Titre AS titre,
            Annonce.Description AS description,
            Annonce.Contrat AS contrat,
            Utilisateurs.Prenom AS prenom,
            Utilisateurs.Nom AS nom,
            Utilisateurs.Role AS role
        FROM Annonce
        LEFT JOIN Utilisateurs ON Utilisateurs.id = Annonce.id_Utilisateur
        """
    )

    annonces = []
    for row in cursor.fetchall():
        prenom = to_str(row.get("prenom")).strip()
        nom = to_str(row.get("nom")).strip()
        auteur = f"{prenom} {nom}".strip()

        annonces.append(
            {
                "id": row.get("id"),
                "titre": to_str(row.get("titre")).strip(),
                "description": to_str(row.get("description")).strip(),
                "contrat": _search_value(row.get("contrat")),
                "auteur": auteur,
                "role": to_str(row.get("role")).strip(),
            }
        )

    return annonces


def _filter_profils_recherche(profils, query, contrat, domaine):
    resultats = []

    for profil in profils:
        if not _matches_query(
            (
                profil.get("prenom"),
                profil.get("nom"),
                profil.get("role"),
                profil.get("adresse"),
                profil.get("competences"),
                profil.get("emplois"),
                profil.get("description"),
            ),
            query,
        ):
            continue

        if not _matches_contract(profil.get("contrat"), contrat):
            continue

        if not _matches_domaine(
            (
                profil.get("role"),
                profil.get("competences"),
                profil.get("emplois"),
                profil.get("description"),
            ),
            domaine,
        ):
            continue

        resultats.append(profil)

    return resultats


def _filter_annonces_recherche(annonces, query, contrat, domaine):
    resultats = []

    for annonce in annonces:
        if not _matches_query(
            (
                annonce.get("titre"),
                annonce.get("description"),
                annonce.get("contrat"),
                annonce.get("auteur"),
                annonce.get("role"),
            ),
            query,
        ):
            continue

        if not _matches_contract(annonce.get("contrat"), contrat):
            continue

        if not _matches_domaine(
            (
                annonce.get("titre"),
                annonce.get("description"),
                annonce.get("role"),
            ),
            domaine,
        ):
            continue

        resultats.append(annonce)

    return resultats


def _sort_profils_recherche(profils, tri):
    if tri == "alpha":
        return sorted(profils, key=lambda profil: _search_blob(profil.get("nom"), profil.get("prenom"), profil.get("role")))

    return sorted(profils, key=lambda profil: profil.get("id") or 0, reverse=True)


def _sort_annonces_recherche(annonces, tri):
    if tri == "alpha":
        return sorted(annonces, key=lambda annonce: _search_blob(annonce.get("titre"), annonce.get("auteur")))

    return sorted(annonces, key=lambda annonce: annonce.get("id") or 0, reverse=True)


###########################################
########## Définition des routes ##########
###########################################

# Pouvoir obtenir les ressources dans uploads
@app.route('/uploads/<category>/<filename>')
@csrf.exempt
def uploaded_file(category, filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], category, filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_file(file_path)

# Pouvoir obtenir les ressources CSS
@app.route('/css/<path:filename>')
@csrf.exempt
def css_file(filename):
    return send_from_directory(os.path.join(SITE_DIR, 'css'), filename)

# Pouvoir obtenir les ressources dans src
@app.route('/src/<path:filename>')
@csrf.exempt
def src_file(filename):
    return send_from_directory(os.path.join(SITE_DIR, 'src'), filename)

# Pouvoir obtenir les ressources JS
@app.route('/js/<path:filename>')
@csrf.exempt
def js_file(filename):
    return send_from_directory(os.path.join(SITE_DIR, 'js'), filename)

# Route racine "home"
@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')

# Route de la page "profil"
@app.route('/profil', methods=['POST', 'GET'])
def profil():
    # Vérifie que l'utilisateur est bien logger
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    # Obtention des données de l'utilisateur
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Utilisateurs WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    # Si le user id est erroné, on le déconnecte
    if row is None:
        return redirect('/logout')

    # Si la requète est un POST
    if request.method == 'POST':
        prenom = request.form.get('Prenom', '').strip()
        nom = request.form.get('Nom', '').strip()
        email = request.form.get('Email', '').strip()
        telephone = request.form.get('Telephone', '').strip()
        role = request.form.get('Role', '').strip()
        adresse = request.form.get('Adresse', '').strip()
        web = request.form.get('Web', '').strip()
        linkedin = request.form.get('Linkedin', '').strip()
        github = request.form.get('Github', '').strip()
        portfolio = request.form.get('Portfolio', '').strip()
        loisirs = request.form.get('Loisirs', '').strip()
        emplois = request.form.get('Emplois', '').strip()
        competences = request.form.get('Competences', '').strip()
        description = request.form.get('Description', '').strip()
        try:
            pdp = save_upload('profile_pic', 'pdp', user_id)
            cv = save_upload('cv', 'cv', user_id)
            lm = save_upload('lettre', 'lm', user_id)
        except ValueError as err:
            return jsonify({'status': 'error', 'message': str(err)}), 400

        # On met a jour la db
        cursor = conn.cursor()
        cursor.execute("""UPDATE Utilisateurs SET 
                Prenom = %s,
                Nom = %s,
                Email = %s,
                Telephone = %s,
                Role = %s,
                Adresse = %s,
                Web = %s,
                Linkedin = %s,
                Github = %s,
                Portfolio = %s,
                Loisirs = %s,
                Emplois = %s,
                Competences = %s,
                Description = %s
            WHERE id = %s
            """,
            (
                prenom,
                nom,
                email,
                telephone,
                role,
                adresse,
                web,
                linkedin,
                github,
                portfolio,
                loisirs,
                emplois,
                competences,
                description,
                user_id
            )
        )

        if pdp:
            cursor.execute("UPDATE Utilisateurs SET PdP = %s WHERE id = %s", (pdp, user_id))

        if cv:
            cursor.execute("UPDATE Utilisateurs SET CV = %s WHERE id = %s", (cv, user_id))

        if lm:
            cursor.execute("UPDATE Utilisateurs SET LM = %s WHERE id = %s", (lm, user_id))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success'})

    # Chargement des données utilisateur
    data = {
        'id': row.get('id', ''),
        'Nom': row.get('Nom', ''),
        'Prenom': row.get('Prenom', ''),
        'Email': row.get('Email', ''),
        'Telephone': row.get('Telephone', ''),
        'Role': row.get('Role', ''),
        'Adresse': row.get('Adresse', ''),
        'Web': row.get('Web', ''),
        'Loisirs': row.get('Loisirs', ''),
        'Emplois': row.get('Emplois', ''),
        'Competences': row.get('Competences', ''),
        'Description': row.get('Description', ''),
        'Linkedin': row.get('Linkedin', ''),
        'Github': row.get('Github', ''),
        'Portfolio': row.get('Portfolio', ''),
        'PdP': row.get('PdP', ''),
        'CV': row.get('CV', ''),
        'LM': row.get('LM', ''),
    }

    return render_template('profil.html', data=data)

# Route de la page "login"
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per 15 minute")
def login():
    # Rendu de la page pour requète GET
    if request.method == 'GET':
        return render_template('login.html')

    # Obtention des credentials
    email = request.form.get('email').strip().lower()
    password = request.form.get('password')

    # Connection à la DB
    db = db_connection()
    cursor = db.cursor(dictionary=True)

    # Tentative d'obtention des info de l'utilisateur renseigné
    cursor.execute("SELECT id, MotDePasse FROM Utilisateurs WHERE Email = %s", (email,))
    row = cursor.fetchone()
    if row is None:
        cursor.close()
        db.close()
        return render_template("login.html", error="error_message"), 401

    # Vérification du mot de passe
    if not check_password_hash(row.get('MotDePasse'), password):
        cursor.close()
        db.close()
        return render_template("login.html", error="error_message"), 401

    # Fermer la connexion à la DB
    cursor.close()
    db.close()

    # Redirection sur la page profil avec le cookie de session
    session.clear()
    session['user_id'] = row['id']
    return redirect('/profil')

# Route de la page "register"
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Rendu de la page pour requète GET
    if request.method == 'GET':
        return render_template('register.html', error=None)

    # Obtention des informations
    nom = request.form.get('nom', '').strip()
    prenom = request.form.get('prenom', '').strip()
    numero = request.form.get('numero', '').strip()
    email = request.form.get('email').strip().lower()
    user_type = request.form.get('user_type', '').strip()
    password = request.form.get('password', '')
    confirm = request.form.get('confirm_password', '')
    adresse = request.form.get('ecole', '').strip()

    if password != confirm:
        return render_template("register.html", error="Les mots de passe ne correspondent pas."), 400

    # Connexion à la DB
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)

    # Vérification que l'utilisateur n'existe pas
    cursor.execute("SELECT id FROM Utilisateurs WHERE Email = %s", (email,))
    if cursor.fetchone() is not None:
        return render_template("register.html", error="Utilisateur deja enregistre"), 409

    # Enregistrement de l'utilisateur
    cursor.execute(
        "INSERT INTO Utilisateurs (`Prenom`, `Nom`, Telephone, Email, Role, Adresse, MotDePasse) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (prenom, nom, numero, email, user_type, adresse, generate_password_hash(password))
    )
    conn.commit()
    user_id = cursor.lastrowid

    # Déconnexion à la DB
    cursor.close()
    conn.close()

    # Redirection sur la page profil avec le cookie de session
    session.clear()
    session['user_id'] = user_id
    return redirect('/profil')


@app.route("/post", methods=["GET", "POST"])
def publication():
    # Vérifie si l'utilisateur est bien logger
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    if request.method == "POST":
        # Obtention des données de l'annonce
        titre = request.form.get("titre", "").strip()
        contrat = request.form.get("contrat", "").strip()
        description = request.form.get("description", "").strip()

        # Connexion à la DB
        db = db_connection()
        cursor = db.cursor()

        # Publication de l'annonce
        cursor.execute(
            "INSERT INTO Annonce (id_Utilisateur, Description, Titre, Contrat) VALUES (%s, %s, %s, %s)",
            (user_id, description, titre, contrat),
        )
        db.commit()

        # Déconnexion à la DB
        cursor.close()
        db.close()

        # Retour pour l'utilisateur
        flash("Annonce publiee avec succes.", "success")
        return redirect("/post")

    return render_template("publication.html")


@app.route("/recherche", methods=["GET", "POST"])
def recherche():
    form = RechercheForm()
    profils = []
    annonces = []
    db = None
    cursor = None

    try:
        db = db_connection()
        cursor = db.cursor(dictionary=True)
        profils = _load_profils_recherche(cursor)
        annonces = _load_annonces_recherche(cursor)
    except Exception as error:
        print(f"Recherche error: {error}")
    finally:
        if cursor is not None:
            cursor.close()
        if db is not None:
            db.close()

    tri = form.tri.data or "recent"

    if form.validate_on_submit():
        recherche_texte = _search_value(form.q.data)
        contrat = _search_value(form.contrat.data)
        domaine = _search_value(form.domaine.data)
        tri = form.tri.data or "recent"

        profils = _filter_profils_recherche(profils, recherche_texte, contrat, domaine)
        annonces = _filter_annonces_recherche(annonces, recherche_texte, contrat, domaine)

    profils = _sort_profils_recherche(profils, tri)
    annonces = _sort_annonces_recherche(annonces, tri)

    return render_template(
        "recherche.html",
        form=form,
        profils=profils,
        annonces=annonces,
        total_resultats=len(profils) + len(annonces),
    )

# Déconnexion
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Sécuriser les requêtes Flask
@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "frame-ancestors 'none';"
    )
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

# Lancer Flask
if __name__ == '__main__':
    app.run(host="0.0.0.0", port="5000", debug=False)
