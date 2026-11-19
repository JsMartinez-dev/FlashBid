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
const movementLabels: Record<string, string> = {
  INITIAL_CREDIT: "Crédito inicial",
  RESERVE: "Reserva de créditos",
  RELEASE: "Liberación de créditos",
  PURCHASE: "Compra",
  SALE: "Venta",
};

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
  const [imageUrl, setImageUrl] = useState("");
  const [imageStatus, setImageStatus] = useState<"loading" | "loaded" | "error">("loading");
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
    setAuction(null);
    setImageUrl("");
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
      if (target === "publish" && view !== "publish") { setAuction(null); setImageUrl(""); }
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
        {view === "wallet" && <div className="page-shell secondary-page wallet-page"><section><div className="secondary-heading"><div><p className="eyebrow">Tu cuenta</p><h1>Tu billetera<span className="gold-dot">.</span></h1><p>Un vistazo a tus créditos y movimientos.</p></div><button className="outline-button" onClick={refreshWallet}>Actualizar billetera</button></div><div className="wallet-cards"><article className="wallet-primary"><span className="eyebrow">Saldo disponible</span><strong>{new Intl.NumberFormat("es-CO").format(profile.wallet.availableCredits)} <small>créditos</small></strong><p>Disponible para participar en nuevas subastas.</p></article><article><span className="eyebrow">Saldo reservado</span><strong>{new Intl.NumberFormat("es-CO").format(profile.wallet.reservedCredits)} <small>créditos</small></strong><p>Créditos asociados a tus pujas activas.</p></article></div><div className="subsection-heading"><div><p className="eyebrow">Historial</p><h2>Movimientos recientes</h2></div></div>{movements.length ? <div className="movement-list">{movements.map((movement, index) => <article className="movement-row" key={`${movement.createdAt}-${index}`}><div><strong>{movementLabels[movement.type] ?? movement.type.replaceAll("_", " ")}</strong><p>{new Date(movement.createdAt).toLocaleString("es-CO")}</p></div><strong className="mono">{new Intl.NumberFormat("es-CO").format(movement.amount)} créditos</strong></article>)}</div> : <p className="secondary-empty">Aún no tienes movimientos en tu billetera.</p>}</section></div>}
        {view === "publish" && <div className="page-shell secondary-page publish-page"><section><div className="secondary-heading"><div><p className="eyebrow">Comparte una pieza</p><h1>Publicar subasta<span className="gold-dot">.</span></h1><p>Cuéntanos sobre el artículo que quieres subastar.</p></div></div><div className="publish-layout"><form className="editorial-form" onSubmit={createAuction} onChange={() => setAuction(null)}><div className="form-heading"><span className="mono">01 / DETALLES DEL ARTÍCULO</span><p>Completa la información que verán los compradores.</p></div><label>Título del artículo<input required name="title" minLength={3} maxLength={120} placeholder="Ej. Cámara analógica vintage" /></label><label>Descripción<textarea required name="description" maxLength={2000} rows={5} placeholder="Describe tu artículo y sus características" /></label><label>Categoría<select required name="category" defaultValue=""><option value="" disabled>Selecciona una categoría</option><option>Arte y antigüedades</option><option>Coleccionables</option><option>Deportes</option><option>Electrodomésticos</option><option>Electrónica</option><option>Fotografía</option><option>Hogar y muebles</option><option>Joyería y relojes</option><option>Libros</option><option>Moda y accesorios</option><option>Música</option><option>Vehículos</option><option>Otra categoría</option></select></label><label>URL de la imagen<input required name="imageUrl" type="url" placeholder="https://..." value={imageUrl} onChange={(event) => { setImageUrl(event.target.value); setImageStatus("loading"); }} /><span className="field-help">Añade un enlace directo a una fotografía del artículo.</span></label><div className="form-heading"><span className="mono">02 / PRECIO INICIAL</span><p>Define el punto de partida de las pujas.</p></div><label>Precio inicial en créditos<input required name="initialPrice" type="number" min="1" step="1" placeholder="0" /></label><button className="dark-button" type="submit">Publicar subasta <span aria-hidden="true">↗</span></button></form><aside className="publish-aside"><span className="material-symbols-outlined" aria-hidden="true">photo_camera</span><p className="eyebrow">Una buena presentación</p><h2>Cada pieza tiene una historia<span className="gold-dot">.</span></h2><p>Una descripción clara y una buena fotografía ayudan a que otros conozcan tu artículo.</p>{imageUrl.trim() && !auction && <div className="image-preview"><p className="eyebrow">Vista previa de la imagen</p>{imageStatus === "error" && <p className="image-preview-error" role="status">No se pudo cargar la imagen. Revisa que el enlace sea directo y público.</p>}<img key={imageUrl} src={imageUrl.trim()} alt="Vista previa del artículo" onLoad={() => setImageStatus("loaded")} onError={() => setImageStatus("error")} hidden={imageStatus === "error"} />{imageStatus === "loading" && <p className="field-help">Cargando imagen…</p>}</div>}{auction && <article className="published-card"><img src={auction.imageUrl} alt={auction.title} onError={(event) => { event.currentTarget.src = "/placeholder.svg"; event.currentTarget.alt = "Imagen no disponible"; }} /><p className="eyebrow gold-text">Subasta publicada</p><h3>{auction.title}</h3><p>Precio inicial: {auction.initialPrice} créditos</p><button className="text-button" type="button" onClick={() => navigate("activity", "mis-subastas")}>Ir a mis subastas ↗</button>{auction.status === "ACTIVE_NO_BIDS" && <button className="text-button" type="button" onClick={cancelAuction}>Cancelar subasta</button>}</article>}</aside></div></section></div>}
        {error && <p className="page-shell error-message" role="alert">{error}</p>}</main><footer className="site-footer"><div className="page-shell"><strong>FLASHBID</strong><span>Subastas en tiempo real con créditos virtuales.</span><button className="text-button" onClick={() => navigate("explore")}>Volver a explorar ↑</button></div></footer></div>;
  }

  return <main className="auth-layout"><aside className="auth-intro"><img src="/Logo FlashBid con Pujas Ascendentes.png" alt="FlashBid" /><div><p className="eyebrow">Una nueva forma de descubrir</p><h1>Encuentra algo extraordinario<span className="gold-dot">.</span></h1><p>Descubre artículos, sigue cada puja y encuentra tu próxima pieza favorita.</p></div><span className="auth-intro-footer">FLASHBID &nbsp; / &nbsp; SUBASTAS EN TIEMPO REAL</span></aside><div className="auth-main"><section className="auth-screen"><p className="eyebrow">Bienvenido a FlashBid</p><h2>{mode === "login" ? "Inicia sesión" : "Crea tu cuenta"}<span className="gold-dot">.</span></h2><p className="auth-description">{mode === "login" ? "Continúa explorando y participando en tus subastas favoritas." : "Únete para descubrir artículos y participar en las subastas."}</p><form onSubmit={submit}>{mode === "register" && <label>Nombre de usuario<input required name="displayName" minLength={2} maxLength={60} autoComplete="nickname" placeholder="Cómo quieres que te llamen" /></label>}<label>Correo electrónico<input required name="email" type="email" autoComplete="email" placeholder="tu@correo.com" /></label><label>Contraseña<input required name="password" type="password" minLength={8} autoComplete={mode === "login" ? "current-password" : "new-password"} placeholder="Mínimo 8 caracteres" /></label><button type="submit">{mode === "login" ? "Iniciar sesión" : "Crear cuenta"} <span aria-hidden="true">↗</span></button></form>{error && <p role="alert">{error}</p>}<p className="auth-switch">{mode === "login" ? "¿Aún no tienes cuenta?" : "¿Ya tienes una cuenta?"} <button className="link" onClick={() => { setError(""); setMode(mode === "login" ? "register" : "login"); }}>{mode === "login" ? "Regístrate" : "Inicia sesión"}</button></p><p className="auth-health">{health ? `Servicios: ${health.estado} · DynamoDB: ${health.dynamodb.estado} · Redis: ${health.redis.estado}` : healthError ? "No se pudo consultar el estado de los servicios." : "Consultando servicios..."}</p></section></div></main>;
}

createRoot(document.getElementById("root")!).render(<App />);
