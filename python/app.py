import os, uuid, mysql.connector
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, redirect, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import Optional

# Definition des chemins absolus
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE_DIR = os.path.join(BASE_DIR, "site")

# Configuration de Flask
app = Flask(__name__, template_folder=os.path.join(SITE_DIR, "html"), static_folder=SITE_DIR, static_url_path='/site')
app.jinja_env.autoescape = True # Corrige XSS des tempates Jinja
app.config['UPLOAD_FOLDER'] = os.path.join(SITE_DIR, "uploads")
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev_secret)")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
csrf = CSRFProtect(app)


@app.context_processor
def inject_auth_state():
    return {"is_logged_in": bool(session.get("user_id"))}


ALLOWED_UPLOAD_EXTENSIONS = {
    "profile_pic": {"jpg", "jpeg", "png", "webp"},
    "cv": {"pdf"},
    "lettre": {"pdf"},
}

UPLOAD_ERROR_MESSAGES = {
    "profile_pic": "La photo de profil doit etre au format JPG, JPEG, PNG ou WEBP.",
    "cv": "Le CV doit etre au format PDF.",
    "lettre": "La lettre de motivation doit etre au format PDF.",
}

LOGIN_ERROR_MESSAGE = "Identifiant ou mot de passe incorrect."
LOCKOUT_ERROR_MESSAGE = "Trop de tentatives de connexion. Reessaie plus tard."
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)
FAILED_LOGIN_ATTEMPTS = {}


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


# Connection a la base de donnee
def db_connection():
    conn = mysql.connector.connect(host="db", user=os.getenv("MYSQL_USER"), password=os.getenv("MYSQL_PASSWORD"), database=os.getenv("MYSQL_DATABASE"))
    return conn


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


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _is_password_hash(password_value: str) -> bool:
    return isinstance(password_value, str) and password_value.startswith(("scrypt:", "pbkdf2:"))


def _verify_password(stored_password: str, candidate_password: str):
    if not stored_password or candidate_password is None:
        return False, None

    if _is_password_hash(stored_password):
        return check_password_hash(stored_password, candidate_password), None

    is_valid = candidate_password == stored_password
    if not is_valid:
        return False, None

    return True, generate_password_hash(candidate_password)


def _clear_failed_login_attempts(identifier: str) -> None:
    if identifier:
        FAILED_LOGIN_ATTEMPTS.pop(identifier, None)


def _is_login_locked(identifier: str) -> bool:
    if not identifier:
        return False

    attempt_state = FAILED_LOGIN_ATTEMPTS.get(identifier)
    if not attempt_state:
        return False

    now = datetime.utcnow()
    locked_until = attempt_state.get("locked_until")
    last_failure = attempt_state.get("last_failure")

    if locked_until and locked_until > now:
        return True

    if locked_until or (last_failure and now - last_failure > LOCKOUT_DURATION):
        FAILED_LOGIN_ATTEMPTS.pop(identifier, None)

    return False


def _record_failed_login(identifier: str) -> bool:
    if not identifier:
        return False

    now = datetime.utcnow()
    attempt_state = FAILED_LOGIN_ATTEMPTS.get(identifier)

    if not attempt_state or now - attempt_state["last_failure"] > LOCKOUT_DURATION:
        attempt_state = {"count": 0, "last_failure": now, "locked_until": None}

    attempt_state["count"] += 1
    attempt_state["last_failure"] = now

    if attempt_state["count"] >= MAX_LOGIN_ATTEMPTS:
        attempt_state["locked_until"] = now + LOCKOUT_DURATION

    FAILED_LOGIN_ATTEMPTS[identifier] = attempt_state
    return bool(attempt_state["locked_until"] and attempt_state["locked_until"] > now)


def _save_upload(field_name: str, category: str) -> dict:
    file = request.files.get(field_name)
    if not file or not file.filename:
        return ''

    category_dir = os.path.join(app.config['UPLOAD_FOLDER'], category)
    os.makedirs(category_dir, exist_ok=True)

    original_filename = secure_filename(file.filename)
    _, extension = os.path.splitext(original_filename)
    extension = extension.lower().lstrip('.')

    if extension not in ALLOWED_UPLOAD_EXTENSIONS.get(field_name, set()):
        raise ValueError(UPLOAD_ERROR_MESSAGES.get(field_name, "Type de fichier non autorise."))

    filename = f"{uuid.uuid4().hex}.{extension}"
    save_path = os.path.join(category_dir, filename)
    file.save(save_path)

    return f'/uploads/{category}/{filename}'


@app.route('/uploads/<category>/<filename>')
@csrf.exempt
def uploaded_file(category, filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], category, filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_file(file_path)


@app.route('/css/<path:filename>')
@csrf.exempt
def css_file(filename):
    return send_from_directory(os.path.join(SITE_DIR, 'css'), filename)


@app.route('/src/<path:filename>')
@csrf.exempt
def src_file(filename):
    return send_from_directory(os.path.join(SITE_DIR, 'src'), filename)


@app.route('/', methods=['GET', 'POST'])
@csrf.exempt
def home():
    if request.method == 'GET':
        return render_template('home.html')
    elif request.method == 'POST':
        return "<h1>Perdu ?</h1>"


@app.route('/profil', methods=['POST', 'GET'])
def profil():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')

    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Utilisateurs WHERE id = %s", (user_id,))
    row = cursor.fetchone()

    if row is None:
        cursor.close()
        conn.close()
        return redirect('/logout')

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
            pdp = _save_upload('profile_pic', 'profile_pics')
            cv = _save_upload('cv', 'cv')
            lm = _save_upload('lettre', 'lettres')
        except ValueError as err:
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': str(err)}), 400

        cursor.close()
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
        'PdP': to_str(row.get('PdP', '')),
        'CV': to_str(row.get('CV', '')),
        'LM': to_str(row.get('LM', '')),
    }

    cursor.close()
    conn.close()
    return render_template('profil.html', data=data)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    email = _normalize_email(request.form.get('email'))
    password = request.form.get('password', '')
    login_identifier = email or (request.remote_addr or "anonymous")

    if _is_login_locked(login_identifier):
        return render_template("login.html", error=LOCKOUT_ERROR_MESSAGE), 429

    db = db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT id, MotDePasse FROM Utilisateurs WHERE Email = %s", (email,))
    row = cursor.fetchone()
    if row is None:
        is_now_locked = _record_failed_login(login_identifier)
        cursor.close()
        db.close()
        error_message = LOCKOUT_ERROR_MESSAGE if is_now_locked else LOGIN_ERROR_MESSAGE
        return render_template("login.html", error=error_message), 401

    is_valid_password, upgraded_password_hash = _verify_password(row.get('MotDePasse'), password)
    if not is_valid_password:
        is_now_locked = _record_failed_login(login_identifier)
        cursor.close()
        db.close()
        error_message = LOCKOUT_ERROR_MESSAGE if is_now_locked else LOGIN_ERROR_MESSAGE
        return render_template("login.html", error=error_message), 401

    if upgraded_password_hash:
        cursor.execute("UPDATE Utilisateurs SET MotDePasse = %s WHERE id = %s", (upgraded_password_hash, row['id']))
        db.commit()

    cursor.close()
    db.close()

    _clear_failed_login_attempts(login_identifier)
    session.clear()
    session['user_id'] = row['id']
    return redirect('/profil')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html', error=None)

    nom = request.form.get('nom', '').strip()
    prenom = request.form.get('prenom', '').strip()
    numero = request.form.get('numero', '').strip()
    email = _normalize_email(request.form.get('email'))
    user_type = request.form.get('user_type', '').strip()
    password = request.form.get('password', '')
    confirm = request.form.get('confirm_password', '')
    adresse = request.form.get('ecole', '').strip()

    if password != confirm:
        return render_template("register.html", error="Les mots de passe ne correspondent pas."), 400

    try:
        conn = db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM Utilisateurs WHERE Email = %s", (email,))
        if cursor.fetchone() is not None:
            return render_template("register.html", error="Utilisateur deja enregistre"), 409

        cursor.execute(
            "INSERT INTO Utilisateurs (`Prenom`, `Nom`, Telephone, Email, Role, Adresse, MotDePasse) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (prenom, nom, numero, email, user_type, adresse, generate_password_hash(password))
        )
        conn.commit()
        user_id = cursor.lastrowid
        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        return render_template("register.html", error=f"Erreur DB : {err}"), 500

    session.clear()
    session['user_id'] = user_id
    return redirect('/profil')


@app.route("/post", methods=["GET", "POST"])
def publication():
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    values = {
        "titre": "",
        "contrat": "",
        "description": "",
    }

    if request.method == "POST":
        values["titre"] = request.form.get("titre", "").strip()
        values["contrat"] = request.form.get("contrat", "").strip()
        values["description"] = request.form.get("description", "").strip()

        if not values["titre"] or not values["contrat"] or not values["description"]:
            flash("Tous les champs sont obligatoires.", "error")
        elif values["contrat"] not in {"Alternance", "Stage"}:
            flash("Le type de contrat est invalide.", "error")
        else:
            db = None
            cursor = None

            try:
                db = db_connection()
                cursor = db.cursor()
                cursor.execute(
                    "INSERT INTO Annonce (id_Utilisateur, Description, Titre, Contrat) VALUES (%s, %s, %s, %s)",
                    (user_id, values["description"], values["titre"], values["contrat"]),
                )
                db.commit()
                flash("Annonce publiee avec succes.", "success")
                return redirect("/post")
            except mysql.connector.Error as error:
                print(f"Annonce error: {error}")
                flash("Impossible de publier l annonce pour le moment.", "error")
            finally:
                if cursor is not None:
                    cursor.close()
                if db is not None:
                    db.close()

    return render_template("publication.html", values=values)


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


@app.route('/logout')
@csrf.exempt
def logout():
    session.clear()
    return redirect('/')

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

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=False)
