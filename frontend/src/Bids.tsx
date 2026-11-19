import { FormEvent, useCallback, useEffect, useState } from "react";

type Bid = { bidId: string; amount: number; publicAlias: string; acceptedAt: string };
type Pending = { auctionId: string; amount: number; requestId: string };

export function Bids({ api, token, auctionId, sellerId, leaderId, uid, onAccepted }: {
  api: string; token: string; auctionId: string; sellerId?: string; leaderId?: string; uid: string; onAccepted: () => void;
}) {
  const [bids, setBids] = useState<Bid[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const storageKey = `flashbid.pendingBid.${uid}.${auctionId}`;
  const [pending, setPending] = useState<Pending | null>(() => {
    try { return JSON.parse(sessionStorage.getItem(storageKey) || "null"); } catch { return null; }
  });
  const [loading, setLoading] = useState(false);
  const load = useCallback(async (next?: string) => {
    setLoading(true);
    try {
      const query = next ? `?cursor=${encodeURIComponent(next)}` : "";
      const response = await fetch(`${api}/auctions/${encodeURIComponent(auctionId)}/bids${query}`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error?.message ?? data.detail ?? "No se pudo cargar el historial.");
      setBids((previous) => next ? [...previous, ...data.items] : data.items);
      setCursor(data.nextCursor);
    } catch (err) { setError(err instanceof Error ? err.message : "Error de conexión"); }
    finally { setLoading(false); }
  }, [api, auctionId, token]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const refresh = (event: Event) => {
      if ((event as CustomEvent).detail?.auctionId === auctionId) void load();
    };
    window.addEventListener("flashbid:auction-update", refresh);
    return () => window.removeEventListener("flashbid:auction-update", refresh);
  }, [auctionId, load]);

  async function send(event: FormEvent) {
    event.preventDefault();
    setError(""); setNotice("");
    const value = pending?.amount ?? Number(amount);
    if (!Number.isSafeInteger(value) || value <= 0) { setError("Ingresa un entero positivo."); return; }
    const operation = pending ?? { auctionId, amount: value, requestId: crypto.randomUUID() };
    sessionStorage.setItem(storageKey, JSON.stringify(operation)); setPending(operation); setBusy(true);
    try {
      const response = await fetch(`${api}/auctions/${encodeURIComponent(auctionId)}/bids`, {
        method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ amount: operation.amount, requestId: operation.requestId }),
      });
      const data = await response.json();
      if (!response.ok) {
        // A 5xx may follow a successful commit, so keep the same requestId.
        if (response.status < 500) { sessionStorage.removeItem(storageKey); setPending(null); }
        throw new Error(data.error?.message ?? data.detail ?? "No se pudo procesar la puja.");
      }
      sessionStorage.removeItem(storageKey); setPending(null); setAmount(""); setNotice("Puja aceptada.");
      await load(); onAccepted();
    } catch (err) { setError(err instanceof Error ? err.message : "Error de conexión"); }
    finally { setBusy(false); }
  }

  return <section className="bids-history" aria-label="Pujas"><h4>Historial de pujas</h4>
    {loading && <p role="status">Cargando historial...</p>}
    {!loading && bids.length === 0 && <p>Aún no hay pujas.</p>}
    <ul className="bids-history-list">{bids.map((bid, index) => <li key={bid.bidId} className="bids-history-row"><span className={`bid-avatar ${index === 0 ? "bid-avatar-leader" : ""}`} aria-hidden="true">{bid.publicAlias.trim().charAt(0).toUpperCase() || "?"}</span><div className="bid-history-person"><strong>{bid.publicAlias}</strong>{index === 0 && <span className="bid-leader-label">Puja líder</span>}<time dateTime={bid.acceptedAt}>{new Date(bid.acceptedAt).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" })}</time></div><strong className="bid-history-amount">{new Intl.NumberFormat("es-CO").format(bid.amount)} <small>créditos</small></strong></li>)}</ul>
    {cursor && <button type="button" disabled={loading} onClick={() => void load(cursor)}>Cargar más pujas</button>}
    {sellerId === uid ? <p>No puedes pujar en tu propia subasta.</p> : leaderId === uid && !pending ? <p>Ya eres el líder de la subasta.</p> :
      <form onSubmit={send}><label>Tu puja en créditos<input type="number" min="1" step="1" value={pending ? pending.amount : amount} onChange={(event) => setAmount(event.target.value)} disabled={!!pending || busy} required /></label>
        {pending && <p>Hay una puja pendiente de confirmación. Reinténtala con el mismo identificador.</p>}
        <button type="submit" disabled={busy}>{busy ? "Enviando..." : pending ? "Reintentar puja" : "Pujar"}</button></form>}
    {notice && <p role="status">{notice}</p>}{error && <p role="alert">{error}</p>}
  </section>;
}
