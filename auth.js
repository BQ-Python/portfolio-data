// auth.js – version finale 100 % fonctionnelle sur toutes les pages
const firebaseConfig = {
  apiKey: "AIzaSyB7sRyQt1lNuXqpcesTvL6ktpCAurTcIdk",
  authDomain: "horizon-labs-3321a.firebaseapp.com",
  projectId: "horizon-labs-3321a",
  storageBucket: "horizon-labs-3321a.firebasestorage.app",
  messagingSenderId: "28359753916",
  appId: "1:28359753916:web:bf23bece9f6d1c094090b9",
  measurementId: "G-QJLJM4M3Z8"
};

firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();

// Anti-flash d'auth (indispensable)
document.body.classList.add('firebase-ready');

auth.onAuthStateChanged(user => {
  const loginBtn = document.getElementById('login-btn');
  const userMenu = document.getElementById('user-menu');
  const userName = document.getElementById('user-name');
  const userPhoto = document.getElementById('user-photo');

  if (user) {
    // Connecté → affiche le menu utilisateur
    if (loginBtn) loginBtn.style.display = 'none';
    if (userMenu) userMenu.style.display = 'flex';
    if (userName) userName.textContent = user.displayName?.split(' ')[0] || 'Membre';
    if (userPhoto) {
      userPhoto.src = user.photoURL || `https://via.placeholder.com/36/4a90e2/ffffff?text=${(user.displayName?.[0] || 'H').toUpperCase()}`;
    }
  } else {
    // Déconnecté → affiche le bouton connexion
    if (loginBtn) loginBtn.style.display = 'block';
    if (userMenu) userMenu.style.display = 'none';
  }
});

// Déconnexion propre (fonctionne sur toutes les pages)
document.getElementById('logout-btn')?.addEventListener('click', () => {
  auth.signOut().then(() => location.reload());
});
