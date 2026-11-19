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

  if (session && profile) return <main><header><h1>FlashBid</h1><button onClick={logout}>Sign out</button></header><p>Signed in as {profile.displayName}</p><section><h2>Wallet</h2><p>Available: {profile.wallet.availableCredits} credits</p><p>Reserved: {profile.wallet.reservedCredits} credits</p><h3>Recent movements</h3>{movements.length ? <ul>{movements.map((movement) => <li key={movement.createdAt}>{movement.type}: {movement.amount}</li>)}</ul> : <p>No movements yet.</p>}</section><MyActivity api={apiBaseUrl} token={session.accessToken} /><Wins api={apiBaseUrl} token={session.accessToken} /><AuctionCatalog api={apiBaseUrl} token={session.accessToken} uid={profile.uid} onWalletChange={() => { fetch(`${apiBaseUrl}/me`, { headers: { Authorization: `Bearer ${session.accessToken}` } }).then((r) => r.ok ? r.json() : Promise.reject()).then(setProfile).catch(() => setError("No se pudo actualizar la billetera.")); fetch(`${apiBaseUrl}/me/wallet/movements`, { headers: { Authorization: `Bearer ${session.accessToken}` } }).then((r) => r.ok ? r.json() : Promise.reject()).then((data) => setMovements(data.items)).catch(() => setError("No se pudieron actualizar los movimientos.")); }} /><section><h2>Publish a fictional product</h2><form onSubmit={createAuction}><label>Title<input required name="title" minLength={3} maxLength={120} /></label><label>Description<textarea required name="description" maxLength={2000} /></label><label>Category<input required name="category" minLength={2} maxLength={50} /></label><label>Image URL<input required name="imageUrl" type="url" /></label><label>Initial price<input required name="initialPrice" type="number" min="1" step="1" /></label><button type="submit">Publish auction</button></form>{auction && <article><img src={auction.imageUrl} alt={auction.title} onError={(event) => { event.currentTarget.src = "/placeholder.svg"; event.currentTarget.alt = "Image unavailable"; }} /><h3>{auction.title}</h3><p>Status: {auction.status}</p><p>Initial price: {auction.initialPrice}</p>{auction.status === "ACTIVE_NO_BIDS" && <button onClick={cancelAuction}>Cancel auction</button>}</article>}{error && <p role="alert">{error}</p>}</section></main>;

  return <main><h1>FlashBid</h1><p>{health ? `Core services: ${health.estado}. DynamoDB: ${health.dynamodb.estado}. Redis: ${health.redis.estado}.` : healthError || "Checking core service health..."}</p><section><h2>{mode === "login" ? "Sign in" : "Create account"}</h2><form onSubmit={submit}>{mode === "register" && <label>Display name<input required name="displayName" minLength={2} maxLength={60} /></label>}<label>Email<input required name="email" type="email" /></label><label>Password<input required name="password" type="password" minLength={8} /></label><button type="submit">{mode === "login" ? "Sign in" : "Register"}</button></form>{error && <p role="alert">{error}</p>}<button className="link" onClick={() => setMode(mode === "login" ? "register" : "login")}>{mode === "login" ? "Create an account" : "I already have an account"}</button></section></main>;
}

createRoot(document.getElementById("root")!).render(<App />);
