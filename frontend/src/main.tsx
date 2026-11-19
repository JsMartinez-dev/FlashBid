import { FormEvent, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import { AuctionCatalog } from "./AuctionCatalog";
import { Wins } from "./Wins";
import { MyActivity } from "./MyActivity";

type Session = { accessToken: string; expiresIn: number };
type Wallet = { availableCredits: number; reservedCredits: number };
type Profile = { uid: string; email: string; displayName: string; createdAt: string; wallet: Wallet };
type Auction = {
  auctionId: string;
  title: string;
  status: string;
  expiresAt: number;
  initialPrice: number;
  imageUrl: string;
};
type Health = { estado: string; dynamodb: { estado: string }; redis: { estado: string } };

const authBaseUrl = (import.meta.env.VITE_AUTH_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:4566").replace(/\/$/, "");

function App() {
  const [session, setSession] = useState<Session | null>(() => {
    const saved = localStorage.getItem("flashbid.session");
    return saved ? JSON.parse(saved) : null;
  });
  const [profile, setProfile] = useState<Profile | null>(null);
  const [view, setView] = useState<"explore" | "activity" | "wallet" | "publish">("explore");
  const [menuOpen, setMenuOpen] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState("");
  const [error, setError] = useState("");
  const [auction, setAuction] = useState<Auction | null>(null);
  const [movements, setMovements] = useState<{ type: string; amount: number; createdAt: string }[]>([]);

  useEffect(() => {
    fetch(`${apiBaseUrl}/health`)
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error("Core services are unavailable");
        return data;
      })
      .then(setHealth)
      .catch((reason: Error) => setHealthError(reason.message));
  }, []);

  useEffect(() => {
    if (!session) return;
    fetch(`${apiBaseUrl}/me`, { headers: { Authorization: `Bearer ${session.accessToken}` } })
      .then(async (response) => {
        if (!response.ok) throw new Error("Your session has expired. Please sign in again.");
        return response.json();
      })
      .then(setProfile)
      .catch((reason: Error) => {
        setError(reason.message);
        logout();
      });
  }, [session]);

  useEffect(() => {
    if (!session) return;
    fetch(`${apiBaseUrl}/me/wallet/movements`, { headers: { Authorization: `Bearer ${session.accessToken}` } })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("Unable to load movements")))
      .then((data) => setMovements(data.items))
      .catch((reason: Error) => setError(reason.message));
  }, [session]);

  function logout() {
    localStorage.removeItem("flashbid.session");
    setSession(null);
    setProfile(null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    const payload = {
      email: String(form.get("email")),
      password: String(form.get("password")),
      ...(mode === "register" ? { display_name: String(form.get("displayName")) } : {}),
    };
    try {
      const response = await fetch(`${authBaseUrl}/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Unable to authenticate");
      localStorage.setItem("flashbid.session", JSON.stringify(data.session));
      setSession(data.session);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to authenticate");
    }
  }

  async function createAuction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;
    setError("");
    const form = new FormData(event.currentTarget);
    const payload = {
      title: String(form.get("title")), description: String(form.get("description")),
      category: String(form.get("category")), imageUrl: String(form.get("imageUrl")),
      initialPrice: Number(form.get("initialPrice")),
    };
    try {
      const response = await fetch(`${apiBaseUrl}/auctions`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.accessToken}` }, body: JSON.stringify(payload) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error?.message ?? "Unable to publish auction");
      setAuction(data);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to publish auction");
    }
  }

  async function cancelAuction() {
    if (!session || !auction) return;
    const response = await fetch(`${apiBaseUrl}/auctions/${auction.auctionId}`, { method: "DELETE", headers: { Authorization: `Bearer ${session.accessToken}` } });
    const data = await response.json();
    if (!response.ok) {
      setError(data.error?.message ?? "Unable to cancel auction");
      return;
    }
    setAuction(data);
  }

  if (session && profile) {
    const navigate = (target: "explore" | "activity" | "wallet" | "publish", anchor?: string) => {
      setView(target); setMenuOpen(false);
      window.setTimeout(() => anchor ? document.getElementById(anchor)?.scrollIntoView({ behavior: "smooth" }) : window.scrollTo({ top: 0, behavior: "smooth" }), 50);
    };
    const refreshWallet = () => {
      fetch(`${apiBaseUrl}/me`, { headers: { Authorization: `Bearer ${session.accessToken}` } }).then((r) => r.ok ? r.json() : Promise.reject()).then(setProfile).catch(() => setError("No se pudo actualizar la billetera."));
      fetch(`${apiBaseUrl}/me/wallet/movements`, { headers: { Authorization: `Bearer ${session.accessToken}` } }).then((r) => r.ok ? r.json() : Promise.reject()).then((data) => setMovements(data.items)).catch(() => setError("No se pudieron actualizar los movimientos."));
    };
    return <div className="app-frame"><header className="site-header"><div className="header-inner"><div className="header-left"><button className="wordmark" onClick={() => navigate("explore")} aria-label="FlashBid, ir a explorar">FLASHBID</button>
      <nav className={`main-nav ${menuOpen ? "open" : ""}`} aria-label="Navegación principal"><button className={view === "explore" ? "active" : ""} onClick={() => navigate("explore")}>Explorar</button><button className={view === "activity" ? "active" : ""} onClick={() => navigate("activity", "mis-subastas")}>Mis subastas</button><button onClick={() => navigate("activity", "mis-pujas")}>Mis pujas</button><button className={view === "wallet" ? "active" : ""} onClick={() => navigate("wallet")}>Billetera</button></nav></div>
      <div className="header-actions"><button className="balance-pill mono" onClick={() => navigate("wallet")} aria-label={`Billetera, ${profile.wallet.availableCredits} créditos disponibles`}><span className="material-symbols-outlined" aria-hidden="true">toll</span>{new Intl.NumberFormat("es-CO").format(profile.wallet.availableCredits)} PTS</button><button className="publish-button" onClick={() => navigate("publish")}><span className="material-symbols-outlined" aria-hidden="true">add</span><span>Publicar subasta</span></button><span className="user-name">@{profile.displayName}</span><button className="avatar" onClick={logout} aria-label="Cerrar sesión" title="Cerrar sesión"><span className="material-symbols-outlined" aria-hidden="true">person</span></button><button className="menu-toggle" onClick={() => setMenuOpen(!menuOpen)} aria-label="Abrir navegación" aria-expanded={menuOpen}><span className="material-symbols-outlined" aria-hidden="true">menu</span></button></div></div></header>
      <main className="site-main">{view === "explore" && <AuctionCatalog api={apiBaseUrl} token={session.accessToken} uid={profile.uid} onWalletChange={refreshWallet} />}
        {view === "activity" && <div className="page-shell secondary-page"><MyActivity api={apiBaseUrl} token={session.accessToken} /><Wins api={apiBaseUrl} token={session.accessToken} /></div>}
        {view === "wallet" && <div className="page-shell secondary-page"><section><p className="eyebrow">Tu cuenta</p><h1>Billetera</h1><p>Disponible: {profile.wallet.availableCredits} créditos</p><p>Reservado: {profile.wallet.reservedCredits} créditos</p><h2>Movimientos recientes</h2>{movements.length ? <ul>{movements.map((movement) => <li key={movement.createdAt}>{movement.type}: {movement.amount}</li>)}</ul> : <p>Aún no hay movimientos.</p>}</section></div>}
        {view === "publish" && <div className="page-shell secondary-page"><section><p className="eyebrow">Un nuevo lote</p><h1>Publicar subasta</h1><form onSubmit={createAuction}><label>Título<input required name="title" minLength={3} maxLength={120} /></label><label>Descripción<textarea required name="description" maxLength={2000} /></label><label>Categoría<input required name="category" minLength={2} maxLength={50} /></label><label>URL de la imagen<input required name="imageUrl" type="url" /></label><label>Precio inicial<input required name="initialPrice" type="number" min="1" step="1" /></label><button className="dark-button" type="submit">Publicar subasta</button></form>{auction && <article><img src={auction.imageUrl} alt={auction.title} onError={(event) => { event.currentTarget.src = "/placeholder.svg"; event.currentTarget.alt = "Imagen no disponible"; }} /><h3>{auction.title}</h3><p>Estado: {auction.status}</p><p>Precio inicial: {auction.initialPrice}</p>{auction.status === "ACTIVE_NO_BIDS" && <button className="outline-button" onClick={cancelAuction}>Cancelar subasta</button>}</article>}</section></div>}
        {error && <p className="page-shell error-message" role="alert">{error}</p>}</main><footer className="site-footer"><div className="page-shell"><strong>FLASHBID</strong><span>Subastas en tiempo real con créditos virtuales.</span><button className="text-button" onClick={() => navigate("explore")}>Volver a explorar ↑</button></div></footer></div>;
  }

  return <main className="auth-screen"><h1>FlashBid</h1><p>{health ? `Core services: ${health.estado}. DynamoDB: ${health.dynamodb.estado}. Redis: ${health.redis.estado}.` : healthError || "Checking core service health..."}</p><section><h2>{mode === "login" ? "Sign in" : "Create account"}</h2><form onSubmit={submit}>{mode === "register" && <label>Display name<input required name="displayName" minLength={2} maxLength={60} /></label>}<label>Email<input required name="email" type="email" /></label><label>Password<input required name="password" type="password" minLength={8} /></label><button type="submit">{mode === "login" ? "Sign in" : "Register"}</button></form>{error && <p role="alert">{error}</p>}<button className="link" onClick={() => setMode(mode === "login" ? "register" : "login")}>{mode === "login" ? "Create an account" : "I already have an account"}</button></section></main>;
}

createRoot(document.getElementById("root")!).render(<App />);
