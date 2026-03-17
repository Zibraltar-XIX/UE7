import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__, template_folder="../site/html", static_folder='../site/css')

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

@app.route('/save_profile', methods=['POST'])
def save_profile():
    data = request.get_json()
    global profile_data
    profile_data.update(data)
    print("Données sauvegardées:", profile_data)  # Pour déboguer
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)