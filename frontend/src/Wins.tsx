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
  return <section><h2>Mis subastas ganadas</h2><button type="button" disabled={loading} onClick={() => void load()}>Actualizar victorias</button>
    {loading && <p role="status">Cargando...</p>}{error && <p role="alert">{error}</p>}
    {!loading && !error && items.length === 0 && <p>Aún no has ganado subastas.</p>}
    <div className="auction-grid">{items.map((item) => <article key={item.auctionId}><img src={item.imageUrl} alt={item.title} onError={(e) => { e.currentTarget.src = "/placeholder.svg"; }} /><h3>{item.title}</h3><p>Monto ganador: {item.winningAmount} créditos</p><p>Subasta ganada</p></article>)}</div>
    {cursor && <button type="button" onClick={() => void load(cursor)}>Cargar más</button>}</section>;
}
