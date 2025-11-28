// auth.js – gestion de l’état connecté + menu utilisateur
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

auth.onAuthStateChanged(user => {
  const loginBtn = document.getElementById('login-btn');
  const userMenu = document.getElementById('user-menu');

  if (user) {
    // Connecté
    if (loginBtn) loginBtn.style.display = 'none';
    if (userMenu) {
      userMenu.style.display = 'flex';
      document.getElementById('user-name').textContent = user.displayName.split(' ')[0];
      document.getElementById('user-photo').src = user.photoURL || '';
    }
  } else {
    // Déconnecté
    if (loginBtn) loginBtn.style.display = 'block';
    if (userMenu) userMenu.style.display = 'none';
  }
});
