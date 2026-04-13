import os, mysql.connector, platform
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, redirect, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import hashlib


############################################
########## Configuration de Flask ##########
############################################

# Definition des chemins absolus
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE_DIR = os.path.join(BASE_DIR, "site")

# Configuration de Flask
app = Flask(__name__, template_folder=os.path.join(SITE_DIR, "html"), static_folder=SITE_DIR, static_url_path='/site')

# Vérification du .env
if os.getenv("ENV_CONFIG") == "false":
    app.logger.warning("Fichier .env non configuré")

app.jinja_env.autoescape = True
app.config['UPLOAD_FOLDER'] = os.path.join(SITE_DIR, "uploads")
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
csrf = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")


#####################################
########## Def utilitaires ##########
#####################################

# Injecte une variable "is_logged_in" pour HTML
@app.context_processor
def inject_auth_state():
    return {"is_logged_in": bool(session.get("user_id"))}

# Connection a la base de donnée
def db_connection():
    try:
        conn = mysql.connector.connect(host="db", user=os.getenv("MYSQL_USER"), password=os.getenv("MYSQL_PASSWORD"), database=os.getenv("MYSQL_DATABASE"))
    except mysql.connector.Error as err:
        app.logger.error(f"Erreur de connexion à la base de donnees : {err}")
        raise
    return conn

# Sauvegarder les fichiers
def save_upload(field_name, category, user_id):
    # Obtenir le fichier
    file = request.files.get(field_name)

    if not file or not file.filename:
        return ''

    # Selectionner le bon répertoire
    category_dir = os.path.join(app.config['UPLOAD_FOLDER'], category)
    try:
        os.makedirs(category_dir, exist_ok=True)
    except OSError as err:
        app.logger.error(f"Erreur lors de la creation du repertoire {category_dir} : {err}")
        raise

    # Obtenir l'extension
    original_filename = secure_filename(file.filename)
    _, extension = os.path.splitext(original_filename)
    extension = extension.lower().lstrip('.')

    # Vérifie l'extension
    if extension not in {"jpg", "jpeg", "png", "webp", "gif", "pdf", "docx"}:
        raise ValueError("Type de fichier non autorise.")

    filename = f"{category}-{user_id}.{extension}"
    save_path = os.path.join(category_dir, filename)
    try:
        file.save(save_path)
    except Exception as err:
        app.logger.error(f"Erreur lors de la sauvegarde du fichier {save_path} : {err}")
        raise

    return f'/uploads/{category}/{filename}'


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
    try:
        conn = db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Utilisateurs WHERE id = %s", (user_id,))
        row = cursor.fetchone()
    except Exception as err:
        app.logger.error(f"Erreur lors de la récupération des données utilisateur pour l'id {user_id} : {err}")
        return "Erreur interne du serveur", 500


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
        try:
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
        except Exception as err:
            app.logger.error(f"Erreur lors de la mise a jour des données utilisateur pour l'id {user_id} : {err}")
            return "Erreur interne du serveur", 500

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
    try:
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
    except Exception as err:
        app.logger.error(f"Erreur lors de l'obtention des credentials : {err}")
        return render_template("login.html", error="Erreur lors de l'obtention des credentials"), 400

    # Connection à la DB
    try:
        db = db_connection()
        cursor = db.cursor(dictionary=True)
    except Exception as err:
        app.logger.error(f"Erreur lors de la connexion à la base de données : {err}")
        return render_template("login.html", error="Erreur de connexion à la base de données")

    # Tentative d'obtention des info de l'utilisateur renseigné
    try:
        cursor.execute("SELECT id, MotDePasse FROM Utilisateurs WHERE Email = %s", (email,))
        row = cursor.fetchone()
    except Exception as err:
        app.logger.error(f"Erreur lors de la récupération des données utilisateur pour l'email {email} : {err}")
        cursor.close()
        db.close()
        return render_template("login.html", error="Erreur interne du serveur"), 500

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
    try:
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()
        numero = request.form.get('numero', '').strip()
        email = request.form.get('email').strip().lower()
        user_type = request.form.get('user_type', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        adresse = request.form.get('ecole', '').strip()
    except Exception as err:
        app.logger.error(f"Erreur lors de l'obtention des informations d'inscription : {err}")
        return render_template("register.html", error="Erreur lors de l'obtention des informations"), 400

    if password != confirm:
        return render_template("register.html", error="Les mots de passe ne correspondent pas."), 400

    # Connexion à la DB
    try:
        conn = db_connection()
        cursor = conn.cursor(dictionary=True)
    except Exception as err:
        app.logger.error(f"Erreur lors de la connexion à la base de données : {err}")
        return render_template("register.html", error="Erreur de connexion à la base de données"), 500

    # Vérification que l'utilisateur n'existe pas
    try:
        cursor.execute("SELECT id FROM Utilisateurs WHERE Email = %s", (email,))
        if cursor.fetchone() is not None:
            return render_template("register.html", error="Utilisateur deja enregistre"), 409
    except Exception as err:
        app.logger.error(f"Erreur lors de la vérification de l'existence de l'utilisateur pour l'email {email} : {err}")
        cursor.close()
        conn.close()
        return render_template("register.html", error="Erreur interne du serveur"), 500

    # Enregistrement de l'utilisateur
    try:
        cursor.execute(
            "INSERT INTO Utilisateurs (`Prenom`, `Nom`, Telephone, Email, Role, Adresse, MotDePasse) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (prenom, nom, numero, email, user_type, adresse, generate_password_hash(password))
        )
        conn.commit()
        user_id = cursor.lastrowid
    except Exception as err:
        app.logger.error(f"Erreur lors de l'enregistrement de l'utilisateur pour l'email {email} : {err}")
        cursor.close()
        conn.close()
        return render_template("register.html", error="Erreur interne du serveur"), 500

    # Déconnexion à la DB
    cursor.close()
    conn.close()

    # Redirection sur la page profil avec le cookie de session
    session.clear()
    session['user_id'] = user_id
    return redirect('/profil')

# Route de la page "post"
@app.route("/post", methods=["GET", "POST"])
def publication():
    # Vérifie si l'utilisateur est bien logger
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    if request.method == "POST":
        # Obtention des données de l'annonce
        try:
            titre = request.form.get("titre", "").strip()
            contrat = request.form.get("contrat", "").strip()
            description = request.form.get("description", "").strip()
        except Exception as err:
            app.logger.error(f"Erreur lors de l'obtention des données de l'annonce : {err}")
            return render_template("publication.html", error="Erreur lors de l'obtention des données"), 400

        # Connexion à la DB
        try:
            db = db_connection()
            cursor = db.cursor()
        except Exception as err:
            app.logger.error(f"Erreur lors de la connexion à la base de données : {err}")
            return render_template("publication.html", error="Erreur de connexion à la base de données"), 500

        # Publication de l'annonce
        try:
            cursor.execute(
                "INSERT INTO Annonce (id_Utilisateur, Description, Titre, Contrat) VALUES (%s, %s, %s, %s)",
                (user_id, description, titre, contrat),
            )
            db.commit()
        except Exception as err:
            app.logger.error(f"Erreur lors de la publication de l'annonce pour l'utilisateur id {user_id} : {err}")
            cursor.close()
            db.close()
            return render_template("publication.html", error="Erreur interne du serveur"), 500

        # Déconnexion à la DB
        cursor.close()
        db.close()

        # Retour pour l'utilisateur
        flash("Annonce publiee avec succes.", "success")
        return redirect("/post")

    return render_template("publication.html")

# Route de la page "recherche"
@app.route("/recherche", methods=["GET", "POST"])
def recherche():
    # Si la requète est GET
    if request.method == "GET":
        return render_template("recherche.html", profils=[], annonces=[])

    # Définition des variables
    profils = []
    annonces = []
    keywords = request.form.get('recherche').split()
    contrat = request.form.get('contrat')
    conditions_annonces = []
    params_annonces = []
    conditions_profils = []
    params_profils = []

    if keywords :
        # Connexion à la DB
        try:
            conn = db_connection()
            cursor = conn.cursor(dictionary=True)
        except Exception as err:
            app.logger.error(f"Erreur lors de la connexion à la base de données : {err}")
            return render_template("recherche.html", profils=[], annonces=[], error="Erreur de connexion à la base de données"), 500

        # Recherche des annonces
        if contrat:
            conditions_annonces.append("Contrat = %s")
            params_annonces.append(contrat)
        for word in keywords:
            conditions_annonces.append("(Titre LIKE %s OR Description LIKE %s)")
            params_annonces.extend([f"%{word}%", f"%{word}%"])
        query = "SELECT * FROM Annonce"
        if conditions_annonces:
            query += " WHERE " + " AND ".join(conditions_annonces)

        try:
            cursor.execute(query, tuple(params_annonces))
            annonces = cursor.fetchall()
        except Exception as err:
            app.logger.error(f"Erreur lors de la recherche des annonces avec les mots-clés {keywords} et contrat {contrat} : {err}")
            cursor.close()
            conn.close()
            return render_template("recherche.html", profils=[], annonces=[], error="Erreur interne du serveur lors de la recherche des annonces"), 500

        # Recherche des profils
        for word in keywords:
            conditions_profils.append("(Nom LIKE %s OR Prenom LIKE %s)")
            params_profils.extend([f"%{word}%", f"%{word}%"])
        query = f"SELECT * FROM Utilisateurs WHERE {' AND '.join(conditions_profils)}"
        try:
            cursor.execute(query, tuple(params_profils))
            profils = cursor.fetchall()
        except Exception as err:
            app.logger.error(f"Erreur lors de la recherche des profils avec les mots-clés {keywords} : {err}")
            cursor.close()
            conn.close()
            return render_template("recherche.html", profils=[], annonces=[], error="Erreur interne du serveur lors de la recherche des profils"), 500


    return render_template("recherche.html", profils=profils, annonces=annonces)

# Déconnexion
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Route pour avoir les infos de l'app
@app.route("/info", methods=["GET"])
def info():
    app_info = {
        "Application name": os.getenv("APP_NAME", "unknown"),
        "Application version": os.getenv("VERSION", "unknown"),
        "Application mode": os.getenv("APP_MODE", "unknown"),
        "Application port": os.getenv("PORT", "unknown"),
    }
    system_info = {
        "Python version": platform.python_version(),
        "Hostname": platform.node(),
    }
    return jsonify({"App": app_info, "System": system_info})

# Route pour vérifier l'état de l'app
@app.route("/health", methods=["GET"])
def health():
    app.logger.info("Appel de l'endpoint /health")
    # Vérification que l'application fonctionne
    try:
        # Vérification que la DB est accessible
        conn = db_connection()
        if conn.is_connected():
            conn.close()
            return jsonify({
                "status": "success",
                "message": "L'application et la DB fonctionnent correctement"
            }), 200
        else:
            app.logger.warning("L'application fonctionne mais pas la DB")
            return jsonify({
                "status": "fail",
                "message": "Erreur de connexion a la base de donnees"
            }), 500

    except Exception as e:
        app.logger.error(f"Erreur lors du healthcheck : {e}")
        return jsonify({
            "status": "fail",
            "message": "Erreur interne du serveur lors de la verification"
        }), 500

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


os.system('ls')
eval('1')
hashlib.md5('test')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port="5000", debug=True)
