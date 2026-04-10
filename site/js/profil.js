    function uploadProfilePic() {
    document.getElementById('profile-pic-input').click();
}

    function changeProfilePic(input) {
    if (input.files && input.files[0]) {
    const reader = new FileReader();
    reader.onload = function (e) {
    document.querySelector('.box_profil img').src = e.target.result;
};
    reader.readAsDataURL(input.files[0]);
}
}

    function toggleEdit(containerSelector) {
    const container = document.querySelector(containerSelector);
    const editables = container.querySelectorAll('.editable');
    const button = container.querySelector('button');

    if (button.innerText.toLowerCase() === 'modifier') {
    editables.forEach(el => {
    const input = document.createElement('input');
    input.type = 'text';
    input.id = el.id;
    input.value = el.textContent;
    input.className = 'edit-input';
    input.dataset.originalId = el.id;
    el.replaceWith(input);
});
    button.innerText = 'Valider';
} else {
    const inputs = container.querySelectorAll('input.edit-input');
    inputs.forEach(input => {
    const span = document.createElement('span');
    span.id = input.dataset.originalId || input.id;
    span.className = 'editable';
    span.innerText = input.value || '';
    input.replaceWith(span);
});
    button.innerText = 'modifier';
}
}

    function viewFile(inputId, savedPath) {
    const fileInput = document.getElementById(inputId);
    const file = fileInput.files[0];

    if (file) {
    window.open(URL.createObjectURL(file), '_blank');
} else if (savedPath) {
    window.open(savedPath, '_blank');
} else {
    alert('Aucun fichier selectionne.');
}
}

    async function saveProfile() {
    const formData = new FormData();
    const fieldIds = ['Nom', 'Prenom', 'Email', 'Telephone', 'Role', 'Adresse', 'Loisirs', 'Emplois', 'Competences', 'Description', 'Web', 'Linkedin', 'Github', 'Portfolio'];

    fieldIds.forEach(id => {
    const el = document.getElementById(id) || document.querySelector(`[data-original-id="${id}"]`);
    if (el) {
    if (el.tagName === 'INPUT') {
    formData.append(id, el.value);
} else {
    formData.append(id, el.textContent.trim());
}
}
});

    const profilePic = document.getElementById('profile-pic-input').files[0];
    if (profilePic) {
    formData.append('profile_pic', profilePic);
}

    const cv = document.getElementById('cv').files[0];
    if (cv) {
    formData.append('cv', cv);
}

    const lettre = document.getElementById('lettre').files[0];
    if (lettre) {
    formData.append('lettre', lettre);
}

    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

    try {
    const response = await fetch('/profil', {
    method: 'POST',
    headers: {
    'X-CSRFToken': csrfToken
},
    body: formData
});
    const result = await response.json();

    if (result.status === 'success') {
    alert('Profil mis a jour avec succes !');
    location.reload();
} else {
    alert(result.message || 'Erreur lors de la sauvegarde.');
}
} catch (error) {
    console.error('Erreur:', error);
    alert('Impossible de contacter le serveur.');
}
}