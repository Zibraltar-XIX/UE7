function toggleField(type) {
    const label = document.getElementById('label_ecole');
    const input = document.getElementById('ecole');
    if (type === 'company') {
        label.textContent = "Nom de l'entreprise";
        input.placeholder = 'Ex: Ma Société SAS';
    } else {
        label.textContent = 'École';
        input.placeholder = '';
    }
}