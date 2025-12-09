// frontend/src/App.jsx
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

// Ta config Firebase (elle reste publique → c’est normal)
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

const API_URL = "https://portfolio-api-8o1e.onrender.com"; // Ton backend Render

export default function App() {
  const [user, setUser] = useState(null);
  const [positions, setPositions] = useState({});
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");
  const [loading, setLoading] = useState(false);
  const [chartData, setChartData] = useState(null);
  const [metrics, setMetrics] = useState(null);

  // Auth listener
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (u) => {
      setUser(u);
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

  const login = () => signInWithPopup(auth, new GoogleAuthProvider());
  const logout = () => signOut(auth);

  const addPosition = () => {
    if (!ticker || !quantity) return;
    const t = ticker.toUpperCase();
    setPositions((prev) => ({
      ...prev,
      [t]: (prev[t] || 0) + Number(quantity),
    }));
    setTicker("");
    setQuantity("");
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
    if (!user || Object.keys(positions).length === 0) return;

    setLoading(true);
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${API_URL}/portfolio/equity`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ positions }),
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
      alert("Erreur lors du calcul de la performance");
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
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto p-6">
        {/* Header */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
          <div className="flex justify-between items-center">
            <h1 className="text-4xl font-bold text-gray-800">
              Portefeuille de {user.displayName.split(" ")[0]}
            </h1>
            <button
              onClick={logout}
              className="text-red-600 hover:text-red-800 font-medium"
            >
              Déconnexion
            </button>
          </div>
        </div>

        {/* Ajouter une position */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-bold mb-6">Ajouter une position</h2>
          <div className="flex gap-4 flex-wrap">
            <input
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder="AAPL"
              className="px-6 py-4 border border-gray-300 rounded-xl text-lg flex-1 min-w-32"
            />
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="100"
              className="px-6 py-4 border border-gray-300 rounded-xl text-lg w-32"
            />
            <button
              onClick={addPosition}
              className="bg-green-600 hover:bg-green-700 text-white px-8 py-4 rounded-xl font-bold"
            >
              Ajouter
            </button>
            <button
              onClick={savePortfolio}
              className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-4 rounded-xl font-bold"
            >
              Sauvegarder
            </button>
            <button
              onClick={loadPerformance}
              disabled={loading || Object.keys(positions).length === 0}
              className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white px-8 py-4 rounded-xl font-bold"
            >
              {loading ? "Calcul..." : "Analyser"}
            </button>
          </div>
        </div>

        {/* Positions */}
        {Object.keys(positions).length > 0 && (
          <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
            <h2 className="text-2xl font-bold mb-6">Mes positions</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-6">
              {Object.entries(positions).map(([t, q]) => (
                <div
                  key={t}
                  className="bg-gradient-to-br from-indigo-500 to-purple-600 text-white p-6 rounded-xl text-center shadow-lg"
                >
                  <div className="text-3xl font-bold">{t}</div>
                  <div className="text-lg mt-2">{q} actions</div>
                  <button
                    onClick={() => removePosition(t)}
                    className="mt-3 text-xs bg-white/20 hover:bg-white/30 px-3 py-1 rounded"
                  >
                    Supprimer
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Métriques */}
        {metrics && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
            <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
              <h3 className="text-xl text-gray-600">Retour total</h3>
              <p className={`text-5xl font-bold mt-4 ${metrics.total_return_pct > 0 ? "text-green-600" : "text-red-600"}`}>
                {metrics.total_return_pct > 0 ? "+" : ""}{metrics.total_return_pct}%
              </p>
            </div>
            <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
              <h3 className="text-xl text-gray-600">Sharpe Ratio</h3>
              <p className="text-5xl font-bold text-blue-600 mt-4">
                {metrics.sharpe_ratio.toFixed(2)}
              </p>
            </div>
            <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
              <h3 className="text-xl text-gray-600">Max Drawdown</h3>
              <p className="text-5xl font-bold text-orange-600 mt-4">
                {metrics.max_drawdown_pct.toFixed(1)}%
              </p>
            </div>
          </div>
        )}

        {/* Graphique */}
        {chartData && (
          <div className="bg-white rounded-2xl shadow-lg p-8">
            <h2 className="text-3xl font-bold mb-6">Évolution du portefeuille</h2>
            <div className="h-96">
              <Line
                data={chartData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: { legend: { position: "top" } },
                }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
