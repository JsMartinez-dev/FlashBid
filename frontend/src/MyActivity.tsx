import { useCallback, useEffect, useState } from "react";

type Auction = { auctionId: string; title: string; description?: string; category?: string; imageUrl: string; initialPrice: number; status: string; expiresAt: number; winnerAlias?: string; winningAmount?: number };
type Bid = { auctionId: string; bidId: string; amount: number; acceptedAt: string; auction: null | { title?: string; status: string; isLeader: boolean; isWinner: boolean } };
type Page<T> = { items: T[]; nextCursor: string | null; serverNow?: number };
const labels: Record<string, string> = { ACTIVE_NO_BIDS: "Activa sin pujas", ACTIVE_BIDDING: "En curso", FINALIZING: "Finalizando", FINISHED: "Finalizada", CANCELLED: "Cancelada", EXPIRED_NO_BIDS: "Vencida sin pujas" };

export function MyActivity({ api, token }: { api: string; token: string }) {
  const [auctions, setAuctions] = useState<Auction[]>([]);
  const [bids, setBids] = useState<Bid[]>([]);
  const [auctionCursor, setAuctionCursor] = useState<string | null>(null);
  const [bidCursor, setBidCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Auction | null>(null);
  const [offset, setOffset] = useState(0);
  const [now, setNow] = useState(Date.now());

  const get = useCallback(async <T,>(path: string): Promise<Page<T>> => {
    const response = await fetch(`${api}${path}`, { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) throw new Error("No se pudo cargar tu actividad.");
    return response.json();
  }, [api, token]);
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [a, b] = await Promise.all([get<Auction>("/me/auctions"), get<Bid>("/me/bids")]);
      setAuctions(a.items); setAuctionCursor(a.nextCursor); setBids(b.items); setBidCursor(b.nextCursor);
      if (a.serverNow !== undefined) setOffset(a.serverNow - Date.now());
    } catch (err) { setError(err instanceof Error ? err.message : "Error de conexión."); }
    finally { setLoading(false); }
  }, [get]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => { const timer = window.setInterval(() => setNow(Date.now()), 1000); return () => window.clearInterval(timer); }, []);
  useEffect(() => { const refresh = () => void load(); window.addEventListener("flashbid:auction-update", refresh); return () => window.removeEventListener("flashbid:auction-update", refresh); }, [load]);
  async function more(kind: "auctions" | "bids", cursor: string) {
    setError(""); setLoading(true);
    try {
      if (kind === "auctions") { const page = await get<Auction>(`/me/auctions?cursor=${encodeURIComponent(cursor)}`); setAuctions((old) => [...old, ...page.items]); setAuctionCursor(page.nextCursor); }
      else { const page = await get<Bid>(`/me/bids?cursor=${encodeURIComponent(cursor)}`); setBids((old) => [...old, ...page.items]); setBidCursor(page.nextCursor); }
    } catch (err) { setError(err instanceof Error ? err.message : "Error de conexión."); }
    finally { setLoading(false); }
  }
  async function openBidAuction(id: string) {
    setError(""); setLoading(true);
    try {
      const response = await fetch(`${api}/auctions/${encodeURIComponent(id)}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error("La subasta ya no está disponible.");
      const item: Auction = await response.json();
      setSelected(item);
    } catch (err) { setError(err instanceof Error ? err.message : "Error de conexión."); }
    finally { setLoading(false); }
  }
  async function cancel(id: string) {
    setError(""); setLoading(true);
    try {
      const response = await fetch(`${api}/auctions/${encodeURIComponent(id)}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error?.message ?? data.detail ?? "No se pudo cancelar la subasta.");
      setSelected(data); await load();
    } catch (err) { setError(err instanceof Error ? err.message : "Error de conexión."); }
    finally { setLoading(false); }
  }
  return <section><h2>Mi actividad</h2><button type="button" disabled={loading} onClick={() => void load()}>Actualizar actividad</button>
    {loading && <p role="status">Cargando actividad...</p>}{error && <p role="alert">{error}</p>}
    <h3>Mis subastas</h3>{!loading && !error && auctions.length === 0 && <p>No hay subastas en esta página.</p>}
    <div className="auction-grid">{auctions.map((item) => {
      const state = item.status === "ACTIVE_NO_BIDS" && item.expiresAt <= now + offset ? "EXPIRED_NO_BIDS" : item.status === "ACTIVE_BIDDING" && item.expiresAt <= now + offset ? "FINALIZING" : item.status;
      return <article key={item.auctionId}><img src={item.imageUrl} alt={item.title} onError={(e) => { e.currentTarget.src = "/placeholder.svg"; }} /><h4>{item.title}</h4><p>{labels[state] ?? state}</p><button type="button" onClick={() => setSelected({ ...item, status: state })}>Ver información</button>{state === "ACTIVE_NO_BIDS" && <button type="button" disabled={loading} onClick={() => void cancel(item.auctionId)}>Cancelar subasta</button>}</article>;
    })}</div>
    {auctionCursor && <button type="button" disabled={loading} onClick={() => void more("auctions", auctionCursor)}>Más subastas</button>}
    {selected && <article aria-label="Información de mi subasta"><h4>{selected.title}</h4><p>{selected.description}</p><p>Categoría: {selected.category}</p><p>Precio inicial: {selected.initialPrice} créditos</p><p>Estado: {labels[selected.status] ?? selected.status}</p>{selected.winnerAlias && <p>Ganador: {selected.winnerAlias} — {selected.winningAmount} créditos</p>}<button type="button" onClick={() => setSelected(null)}>Cerrar información</button></article>}
    <h3>Mis pujas</h3>{!loading && !error && bids.length === 0 && <p>No hay pujas en esta página.</p>}
    <ul>{bids.map((bid) => <li key={bid.bidId}>{bid.auction?.title ?? "Subasta no disponible"}: {bid.amount} créditos — {new Date(bid.acceptedAt).toLocaleString()} — {bid.auction ? bid.auction.isWinner ? "Ganaste" : bid.auction.isLeader ? "Vas liderando" : labels[bid.auction.status] ?? bid.auction.status : "No disponible"} {bid.auction && <button type="button" disabled={loading} onClick={() => void openBidAuction(bid.auctionId)}>Ver subasta</button>}</li>)}</ul>
    {bidCursor && <button type="button" disabled={loading} onClick={() => void more("bids", bidCursor)}>Más pujas</button>}
  </section>;
}
