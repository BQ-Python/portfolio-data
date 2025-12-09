// frontend/src/App.jsx (version corrigée – erreur Firebase fixée + design pro)
import React, { useState, useEffect } from "react";
import { initializeApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signOut,
  onAuthStateChanged,
} from "firebase/auth";
import {
  getFirestore,
  doc,
  setDoc,
  getDoc,
  deleteField,
} from "firebase/firestore";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const firebaseConfig = {
  apiKey: "AIzaSyB7sRyQt1lNuXqpcesTvL6ktpCAurTcIdk",
  authDomain: "horizon-labs-3321a.firebaseapp.com",
  databaseURL: "https://horizon-labs-3321a-default-rtdb.europe-west1.firebasedatabase.app",
  projectId: "horizon-labs-3321a",
  storageBucket: "horizon-labs-3321a.appspot.com",
  messagingSenderId: "28359753916",
  appId: "1:28359753916:web:bf23bece9f6d1c094090b9",
  measurementId: "G-QJLJM4M3Z8",
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);
const API_URL = "https://portfolio-api-8o1e.onrender.com";

export default function App() {
  const [user, setUser] = useState(null);
  const [positions, setPositions] = useState({}); // {ticker: {weight: 0.25, qty: 10}}
  const [ticker, setTicker] = useState("");
  const [weight, setWeight] = useState("");
  const [loading, setLoading] = useState(false);
  const [chartData, setChartData] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [totalWeight, setTotalWeight] = useState(0);
  const [error, setError] = useState(null); // Pour fixer les erreurs popup

  // Calcul somme poids
  useEffect(() => {
    const sum = Object.values(positions).reduce((acc, p) => acc + p.weight, 0);
    setTotalWeight(sum);
  }, [positions]);

  // Auth listener avec fix erreur popup
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (u) => {
      setUser(u);
      setError(null); // Reset erreur
      if (u) {
        const snap = await getDoc(doc(db, "users", u.uid));
        if (snap.exists()) {
          setPositions(snap.data().positions || {});
        }
      } else {
        setPositions({});
        setChartData(null);
        setMetrics(null);
      }
    });
    return unsubscribe;
  }, []);

  const login = async () => {
    try {
      setError(null);
      await signInWithPopup(auth, new GoogleAuthProvider());
    } catch (err) {
      if (err.code === 'auth/popup-closed-by-user') {
        setError('Popup fermé – réessaye la connexion');
      } else {
        setError('Erreur connexion : ' + err.message);
      }
    }
  };

  const logout = () => signOut(auth);

  const addPosition = () => {
    if (!ticker || !weight || weight <= 0) {
      setError('Ticker et poids requis');
      return;
    }
    const t = ticker.toUpperCase();
    const w = Number(weight);
    if (totalWeight + w > 1) {
      setError('Somme des poids > 100%');
      return;
    }
    setPositions((prev) => ({
      ...prev,
      [t]: { weight: w, qty: 0 }, // qty = 0 pour l'instant, on peut ajouter plus tard
    }));
    setTicker("");
    setWeight("");
    setError(null);
  };

  const removePosition = (t) => {
    setPositions((prev) => {
      const newPos = { ...prev };
      delete newPos[t];
      return newPos;
    });
  };

  const savePortfolio = async () => {
    if (!user) return;
    await setDoc(doc(db, "users", user.uid), { positions }, { merge: true });
    alert("Portefeuille sauvegardé !");
  };

  const loadPerformance = async () => {
    if (!user || Object.keys(positions).length === 0) {
      setError('Ajoute des positions d\'abord');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${API_URL}/portfolio/equity`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ positions }), // Envoie les poids
      });

      if (!res.ok) throw new Error("Erreur API");

      const data = await res.json();

      setMetrics(data.metrics);

      setChartData({
        labels: data.dates,
        datasets: [
          {
            label: "Valeur du portefeuille (€)",
            data: data.values,
            borderColor: "#10b981",
            backgroundColor: "rgba(16, 185, 129, 0.1)",
            fill: true,
            tension: 0.3,
          },
        ],
      });
    } catch (err) {
      console.error(err);
      setError("Erreur calcul : " + err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-6xl font-bold text-white mb-8">Mon Portefeuille</h1>
          <button
            onClick={login}
            className="bg-white text-indigo-700 px-10 py-5 rounded-xl text-2xl font-bold shadow-2xl hover:shadow-indigo-500/50 transition"
          >
            Connexion avec Google
          </button>
          {error && <p className="text-red-300 mt-4">{error}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
          <div className="flex justify-between items-center">
            <h1 className="text-3xl font-bold text-gray-800">
              Portefeuille de {user.displayName.split(" ")[0]}
            </h1>
            <button onClick={logout} className="text-red-600 hover:text-red-800">
              Déconnexion
            </button>
          </div>
        </div>

        {/* Ajout position avec poids */}
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
          <h2 className="text-2xl font-bold mb-4">Ajouter une position (en %)</h2>
          <div className="flex gap-4 flex-wrap">
            <input
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder="Ticker (AAPL)"
              className="px-4 py-3 border border-gray-300 rounded-lg flex-1 min-w-32"
            />
            <input
              type="number"
              step="0.01"
              min="0"
              max="100"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
              placeholder="Poids % (ex: 25)"
              className="px-4 py-3 border border-gray-300 rounded-lg w-32"
            />
            <button onClick={addPosition} className="bg-green-600 text-white px-6 py-3 rounded-lg font-bold hover:bg-green-700">
              Ajouter
            </button>
            <button onClick={savePortfolio} className="bg-blue-600 text-white px-6 py-3 rounded-lg font-bold hover:bg-blue-700">
              Sauvegarder
            </button>
            <button
              onClick={loadPerformance}
              disabled={loading || totalWeight !== 1}
              className="bg-purple-600 text-white px-6 py-3 rounded-lg font-bold disabled:opacity-50 hover:bg-purple-700"
            >
              {loading ? "Calcul..." : "Analyser (somme 100%)"}
            </button>
          </div>
          <div className="mt-2 text-sm text-gray-600">
            Somme des poids : {Math.round(totalWeight * 100)}% {totalWeight !== 1 && <span className="text-red-500">(doit faire 100%)</span>}
          </div>
          {error && <p className="text-red-500 mt-2">{error}</p>}
        </div>

        {/* Positions */}
        {Object.keys(positions).length > 0 && (
          <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
            <h2 className="text-2xl font-bold mb-4">Mes positions</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {Object.entries(positions).map(([t, p]) => (
                <div key={t} className="bg-blue-50 p-4 rounded-lg">
                  <h3 className="font-bold">{t}</h3>
                  <p className="text-lg">{(p.weight * 100).toFixed(1)}%</p>
                  <p className="text-sm text-gray-600">Qty: {p.qty || 0}</p>
                  <button onClick={() => removePosition(t)} className="mt-2 text-red-500 text-sm">
                    Supprimer
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Métriques */}
        {metrics && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="bg-green-50 p-6 rounded-2xl text-center">
              <h3 className="text-xl text-gray-600">Retour total</h3>
              <p className="text-4xl font-bold text-green-600">{metrics.total_return_pct > 0 ? '+' : ''}{metrics.total_return_pct}%</p>
            </div>
            <div className="bg-blue-50 p-6 rounded-2xl text-center">
              <h3 className="text-xl text-gray-600">Sharpe Ratio</h3>
              <p className="text-4xl font-bold text-blue-600">{metrics.sharpe_ratio.toFixed(2)}</p>
            </div>
            <div className="bg-orange-50 p-6 rounded-2xl text-center">
              <h3 className="text-xl text-gray-600">Max Drawdown</h3>
              <p className="text-4xl font-bold text-orange-600">{metrics.max_drawdown_pct.toFixed(1)}%</p>
            </div>
          </div>
        )}

        {/* Graphique */}
        {chartData && (
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <h2 className="text-3xl font-bold mb-4">Évolution du portefeuille</h2>
            <div className="h-96">
              <Line data={chartData} options={{ responsive: true, maintainAspectRatio: false }} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
