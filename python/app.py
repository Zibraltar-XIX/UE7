import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# Configuration des chemins
basedir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(basedir, '..', 'site', 'html')
static_dir = os.path.join(basedir, '..', 'site', 'css')
upload_base_dir = os.path.join(basedir, '..', 'site', 'uploads')

# Créer le dossier de base des uploads s'il n'existe pas
os.makedirs(upload_base_dir, exist_ok=True)

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.config['UPLOAD_FOLDER'] = upload_base_dir
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

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
    try:
        # Construire le chemin absolu du fichier
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], category, filename)

        print(f"DEBUG: Requested file path: {file_path}")
        print(f"DEBUG: File exists: {os.path.exists(file_path)}")

        if not os.path.exists(file_path):
            print(f"ERROR: File not found at {file_path}")
            return "File not found", 404

        # Retourner le fichier directement
        from flask import send_file
        return send_file(file_path)

    except Exception as e:
        print(f"ERROR serving file: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}", 500

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/profile')
def profile():
    return render_template('profiles.html', data=profile_data)

@app.route('/save_profile', methods=['POST'])
def save_profile():
    global profile_data

    # Récupération des champs texte
    profile_data['name'] = request.form.get('name', '')
    profile_data['email'] = request.form.get('email', '')
    profile_data['address'] = request.form.get('address', '')
    profile_data['hobbies'] = request.form.get('hobbies', '')
    profile_data['job'] = request.form.get('job', '')
    profile_data['skills'] = request.form.get('skills', '')
    profile_data['description'] = request.form.get('description', '')
    profile_data['linkedin'] = request.form.get('linkedin', '')
    profile_data['github'] = request.form.get('github', '')
    profile_data['portfolio'] = request.form.get('portfolio', '')

    # Gestion des fichiers par catégorie
    file_categories = {
        'profile_pic': 'profile_pics',
        'cv': 'cv',
        'lettre': 'lettres'
    }

    for file_key, category in file_categories.items():
        if file_key in request.files:
            file = request.files[file_key]
            print(f"DEBUG: Processing file {file_key}, filename: {file.filename if file else 'None'}")
            if file and file.filename:
                # Créer le dossier de catégorie s'il n'existe pas
                category_dir = os.path.join(app.config['UPLOAD_FOLDER'], category)
                os.makedirs(category_dir, exist_ok=True)

                # Sécuriser le nom du fichier
                filename = secure_filename(file.filename)
                save_path = os.path.join(category_dir, filename)
                print(f"DEBUG: Saving file to {save_path}")
                file.save(save_path)

                # Stocker le chemin relatif et le nom du fichier
                profile_data[file_key] = {
                    'path': f'/uploads/{category}/{filename}',
                    'filename': filename
                }
                print(f"DEBUG: File saved successfully: {profile_data[file_key]}")
            else:
                print(f"DEBUG: No file or empty filename for {file_key}")
        else:
            print(f"DEBUG: No file found in request for {file_key}")

    print("Données sauvegardées:", profile_data)  # Pour déboguer
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)