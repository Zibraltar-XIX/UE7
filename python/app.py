import os, mysql.connector
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, make_response, redirect, render_template_string
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import Optional

# Definition des chemins absolus
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE_DIR = os.path.join(BASE_DIR, "site")

# Configuration de Flask
app = Flask(__name__, template_folder=os.path.join(SITE_DIR, "html"), static_folder=SITE_DIR, static_url_path='/site')
app.config['UPLOAD_FOLDER'] = os.path.join(SITE_DIR, "uploads")
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
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
        choices=[("recent", "Plus recents"), ("alpha", "A a Z"), ("dispo", "Disponibles en premier")],
        default="recent",
    )
    submit = SubmitField("Rechercher")


# Connection a la base de donnee
def db_connection():
    conn = mysql.connector.connect(host="db", user=os.getenv("MYSQL_USER"), password=os.getenv("MYSQL_PASSWORD"), database=os.getenv("MYSQL_DATABASE"))
    return conn


# Convertir path en utf8
def to_str(val):
    if isinstance(val, (bytes, bytearray)):
        return val.decode('utf-8')
    return val or ''


def _save_upload(field_name: str, category: str) -> dict:
    file = request.files.get(field_name)
    if not file or not file.filename:
        return ''

    category_dir = os.path.join(app.config['UPLOAD_FOLDER'], category)
    os.makedirs(category_dir, exist_ok=True)

    filename = secure_filename(file.filename)
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
@csrf.exempt
def profil():
    user_id = request.cookies.get('UserID')
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
        pdp = _save_upload('profile_pic', 'profile_pics')
        cv = _save_upload('cv', 'cv')
        lm = _save_upload('lettre', 'lettres')

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
@csrf.exempt
def login():
    if request.method == 'GET':
        return render_template('login.html')

    email = request.form.get('email')
    password = request.form.get('password')

    db = db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT id FROM Utilisateurs WHERE Email = %s", (email,))
    row = cursor.fetchone()
    if row is None:
        return render_template("register.html", error="Utilisateur inconnu")
    user_id = row['id']

    cursor.execute("SELECT MotDePasse FROM Utilisateurs WHERE Email = %s", (email,))
    row = cursor.fetchone()
    MotDePass = row['MotDePasse']
    if str(password) != str(MotDePass):
        return render_template("login.html", error="Le mot de passe est different de : " + MotDePass)

    cursor.close()
    db.close()

    resp = make_response(redirect('/profil'))
    resp.set_cookie('UserID', str(user_id))
    return resp


@app.route('/register', methods=['GET', 'POST'])
@csrf.exempt
def register():
    if request.method == 'GET':
        return render_template('register.html', error=None)

    nom = request.form.get('nom', '').strip()
    prenom = request.form.get('prenom', '').strip()
    numero = request.form.get('numero', '').strip()
    email = request.form.get('email', '').strip()
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
            (prenom, nom, numero, email, user_type, adresse, password)
        )
        conn.commit()
        user_id = cursor.lastrowid
        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        return render_template("register.html", error=f"Erreur DB : {err}"), 500

    resp = make_response(redirect('/profil'))
    resp.set_cookie('UserID', str(user_id))
    return resp


@app.route("/recherche", methods=["GET", "POST"])
def recherche():
    form = RechercheForm()
    candidats = []

    try:
        db = db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""SELECT id, nom, prenom, domaine, contrat, disponible, pitch FROM candidats WHERE 1=1""")
        candidats = cursor.fetchall()
        cursor.close()
        db.close()
    except Exception as e:
        print(f"DB Error: {e}")
        candidats = []

    template_path = os.path.join(app.template_folder, "recherche.html")

    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()

    if form.validate_on_submit():
        q = (form.q.data or "").strip().lower()
        contrat = form.contrat.data or ""
        domaine = form.domaine.data or ""
        tri = form.tri.data or "recent"

        if q:
            candidats = [c for c in candidats
                         if q in c["nom"].lower() or q in c["prenom"].lower()
                         or q in c["domaine"].lower() or q in c["contrat"].lower()
                         or q in c.get("pitch", "").lower()]

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


@app.route('/logout')
@csrf.exempt
def logout():
    response = make_response(redirect('/'))
    response.delete_cookie('UserID')
    return response


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
