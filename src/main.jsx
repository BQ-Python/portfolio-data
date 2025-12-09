import React, { useState, useEffect } from "https://cdn.jsdelivr.net/npm/react@18.2.0/umd/react.development.js";
import ReactDOM from "https://cdn.jsdelivr.net/npm/react-dom@18.2.0/umd/react-dom.development.js";

const { auth, GoogleAuthProvider, signInWithPopup, signOut, db, API_URL } = window.firebaseAuth;

function App() {
  const [user, setUser] = useState(null);
  const [ticker, setTicker] = useState("");
  const [qty, setQty] = useState("");
  const [positions, setPositions] = useState({});
  const [equity, setEquity] = useState([]);

  useEffect(() => {
    auth.onAuthStateChanged(async (u) => {
      setUser(u);
      if (u) {
        const docSnap = await getDoc(doc(db, "users", u.uid));
        if (docSnap.exists()) setPositions(docSnap.data().positions || {});
      }
    });
  }, []);

  const login = () => signInWithPopup(auth, new GoogleAuthProvider());
  const logout = () => signOut(auth);

  const savePortfolio = async () => {
    await setDoc(doc(db, "users", user.uid), { positions }, { merge: true });
    alert("Portefeuille sauvegardé !");
  };

  const addPosition = () => {
    if (!ticker || !qty) return;
    setPositions(p => ({ ...p, [ticker.toUpperCase()]: (p[ticker.toUpperCase()] || 0) + Number(qty) }));
    setTicker(""); setQty("");
  };

  const loadPerformance = async () => {
    const idToken = await user.getIdToken();
    const res = await fetch(`${API_URL}/portfolio/equity`, {
      headers: { Authorization: `Bearer ${idToken}`, "Content-Type": "application/json" },
      method: "POST",
      body: JSON.stringify({ positions })
    });
    const data = await res.json();
    setEquity(data);
    alert("Performance chargée ! Voir console pour l’instant");
    console.log("Equity curve →", data);
  };

  if (!user) return <button onClick={login} className="bg-blue-600 text-white px-6 py-3 rounded">Connexion Google</button>;

  return (
    <div className="max-w-4xl mx-auto p-8 bg-white rounded shadow">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl">Portefeuille de {user.displayName}</h1>
        <button onClick={logout} className="text-red-600">Déconnexion</button>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <input placeholder="Ticker (ex: AAPL)" value={ticker} onChange={e=>setTicker(e.target.value)} className="border p-2"/>
        <input type="number" placeholder="Quantité" value={qty} onChange={e=>setQty(e.target.value)} className="border p-2"/>
        <button onClick={addPosition} className="bg-green-600 text-white">Ajouter</button>
      </div>

      <div className="mb-4">
        {Object.entries(positions).map(([t, q]) => (
          <div key={t} className="flex justify-between border-b py-2">
            <span>{t}</span>
            <span>{q} actions</span>
          </div>
        ))}
      </div>

      <div className="space-x-4">
        <button onClick={savePortfolio} className="bg-blue-600 text-white px-4 py-2">Sauvegarder</button>
        <button onClick={loadPerformance} className="bg-purple-600 text-white px-4 py-2">Voir performance</button>
      </div>
    </div>
  );
}

ReactDOM.render(<App />, document.getElementById("root"));
