import os
from flask import Flask, render_template, request, jsonify

# Récupérer le chemin du répertoire courant et aller au bon dossier
basedir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(os.path.dirname(basedir), 'html')
static_dir = os.path.join(os.path.dirname(basedir), 'css')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

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
    'profile_pic': ''  # Pour l'instant, juste le nom du fichier ou URL
}

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/profile')
def profile():
    return render_template('profiles.html', data=profile_data)

@app.route('/save_profile', methods=['POST', 'OPTIONS'])
def save_profile():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        global profile_data
        profile_data.update(data)
        print("Données sauvegardées:", profile_data)  # Pour déboguer
        return jsonify({'status': 'success'})
    except Exception as e:
        print("Erreur:", str(e))  # Pour déboguer
        return jsonify({'status': 'error', 'message': str(e)}), 400

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)