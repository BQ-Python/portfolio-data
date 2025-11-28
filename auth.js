// auth.js – à inclure dans toutes les pages où tu veux savoir si l’utilisateur est connecté
const firebaseConfig = {
  apiKey: "AIzaSy...xxxxxxxx",          // ← LES MÊMES que dans auth.html
  authDomain: "ton-projet-12345.firebaseapp.com",
  projectId: "ton-projet-12345",
  storageBucket: "ton-projet-12345.appspot.com",
  messagingSenderId: "123456789012",
  appId: "1:123456789012:web:abcdef123456"
};

firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();

// Écoute l’état de connexion
auth.onAuthStateChanged(user => {
  const loginBtn = document.getElementById('login-btn');      // le bouton "S'authentifier"
  const userMenu  = document.getElementById('user-menu');     // on va le créer

  if (user) {
    // Connecté
    if (loginBtn) loginBtn.style.display = 'none';
    if (userMenu) {
      userMenu.style.display = 'flex';
      document.getElementById('user-name').textContent = user.displayName || user.email;
    }
  } else {
    // Déconnecté
    if (loginBtn) loginBtn.style.display = 'block';
    if (userMenu) userMenu.style.display = 'none';
  }
});
