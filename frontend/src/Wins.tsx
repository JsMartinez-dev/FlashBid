import { useCallback, useEffect, useState } from "react";
type Win = { auctionId: string; title: string; imageUrl: string; winningAmount: number; finishedAt: string };
export function Wins({ api, token }: { api: string; token: string }) {
  const [items, setItems] = useState<Win[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const load = useCallback(async (next?: string) => {
    setLoading(true); setError("");
    try {
      const response = await fetch(`${api}/me/wins${next ? `?cursor=${encodeURIComponent(next)}` : ""}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error("No se pudieron cargar tus subastas ganadas.");
      const data = await response.json();
      setItems((previous) => next ? [...previous, ...data.items] : data.items); setCursor(data.nextCursor);
    } catch (err) { setError(err instanceof Error ? err.message : "Error de conexión"); }
    finally { setLoading(false); }
  }, [api, token]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const refresh = () => void load();
    window.addEventListener("flashbid:refresh-wins", refresh);
    return () => window.removeEventListener("flashbid:refresh-wins", refresh);
  }, [load]);
  return <section className="wins-section"><div className="subsection-heading"><div><p className="eyebrow">Tu colección</p><h2>Mis subastas ganadas</h2></div><button className="outline-button" type="button" disabled={loading} onClick={() => void load()}>Actualizar victorias</button></div>
    {loading && <p role="status">Cargando...</p>}{error && <p role="alert">{error}</p>}
    {!loading && !error && items.length === 0 && <p className="secondary-empty">Aún no has ganado subastas. Tus victorias aparecerán aquí.</p>}
    <div className="auction-grid">{items.map((item) => <article key={item.auctionId}><img src={item.imageUrl} alt={item.title} onError={(e) => { e.currentTarget.src = "/placeholder.svg"; }} /><div className="activity-card-body"><p className="eyebrow gold-text">Subasta ganada</p><h3>{item.title}</h3><p>Monto ganador <strong>{item.winningAmount} créditos</strong></p></div></article>)}</div>
    {cursor && <button type="button" onClick={() => void load(cursor)}>Cargar más</button>}</section>;
}
