// auth.js – version corrigée et compatible
const firebaseConfig = {
  apiKey: "AIzaSyB7sRyQt1lNuXqpcesTvL6ktpCAurTcIdk",
  authDomain: "horizon-labs-3321a.firebaseapp.com",
  projectId: "horizon-labs-3321a",
  storageBucket: "horizon-labs-3321a.firebasestorage.app",
  messagingSenderId: "28359753916",
  appId: "1:28359753916:web:bf23bece9f6d1c094090b9",
  measurementId: "G-QJLJM4M3Z8"
};

// Initialisation Firebase
firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();

// Anti-flash : on ajoute la classe dès que Firebase est prêt
document.body.classList.add('firebase-ready');

// Gestion de l'état d'authentification
auth.onAuthStateChanged(user => {
  const loginBtn = document.getElementById('login-btn');
  const userMenu = document.getElementById('user-menu');
  const userName = document.getElementById('user-name');
  const userPhoto = document.getElementById('user-photo');

  if (user) {
    // ✅ Utilisateur connecté → affiche le menu utilisateur
    if (loginBtn) loginBtn.style.display = 'none';
    if (userMenu) userMenu.style.display = 'flex';

    if (userName) {
      userName.textContent = user.displayName?.split(' ')[0] || 'Membre';
    }

    if (userPhoto) {
      userPhoto.src = user.photoURL || 
        `https://via.placeholder.com/36/4a90e2/ffffff?text=${(user.displayName?.[0] || 'H').toUpperCase()}`;
    }
  } else {
    // ❌ Utilisateur déconnecté → affiche le bouton connexion
    if (loginBtn) loginBtn.style.display = 'block';
    if (userMenu) userMenu.style.display = 'none';
  }
});

// Déconnexion
document.getElementById('logout-btn')?.addEventListener('click', () => {
  auth.signOut().then(() => location.reload());
});
