import { useCallback, useEffect, useState } from "react";

type Auction = { auctionId: string; title: string; description?: string; category?: string; imageUrl: string; initialPrice: number; highestBid?: number; leaderAlias?: string; sellerAlias?: string; expiresAt: number; status: string; serverNow?: number };
type Page = { items: Auction[]; nextCursor: string | null; serverNow: number };

export function AuctionCatalog({ api, token }: { api: string; token: string }) {
  const [items, setItems] = useState<Auction[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [detail, setDetail] = useState<Auction | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [offset, setOffset] = useState(0);
  const [now, setNow] = useState(Date.now());

  const load = useCallback(async (next?: string) => {
    setLoading(true);
    setError("");
    try {
      const query = next ? `?cursor=${encodeURIComponent(next)}` : "";
      const response = await fetch(`${api}/auctions${query}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error("No se pudo cargar el catálogo.");
      const page: Page = await response.json();
      setOffset(page.serverNow - Date.now());
      setItems((previous) => next ? [...previous, ...page.items] : page.items);
      setCursor(page.nextCursor);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar el catálogo.");
    } finally { setLoading(false); }
  }, [api, token]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const remaining = (expiresAt: number) => Math.max(0, Math.ceil((expiresAt - (now + offset)) / 1000));

  async function showDetail(id: string) {
    setDetailLoading(true);
    setDetailError("");
    setDetail(null);
    try {
      const response = await fetch(`${api}/auctions/${encodeURIComponent(id)}`, { headers: { Authorization: `Bearer ${token}` } });
      if (response.status === 404) throw new Error("La subasta ya no está disponible.");
      if (!response.ok) throw new Error("No se pudo cargar el detalle.");
      const item: Auction = await response.json();
      if (item.serverNow !== undefined) setOffset(item.serverNow - Date.now());
      setDetail(item);
    } catch (err) { setDetailError(err instanceof Error ? err.message : "Error al consultar la subasta."); }
    finally { setDetailLoading(false); }
  }

  const visible = items.filter((item) => remaining(item.expiresAt) > 0);
  return <section aria-labelledby="catalog-title">
    <h2 id="catalog-title">Subastas activas</h2>
    <button type="button" onClick={() => void load()} disabled={loading}>Actualizar catálogo</button>
    {loading && <p role="status">Cargando subastas...</p>}
    {error && <p role="alert">{error}</p>}
    {!loading && !error && visible.length === 0 && <p>No hay subastas activas en esta página.</p>}
    <div className="auction-grid">{visible.map((item) => <article key={item.auctionId}>
      <img src={item.imageUrl} alt={item.title} onError={(event) => { event.currentTarget.src = "/placeholder.svg"; }} />
      <h3>{item.title}</h3><p>Precio inicial: {item.initialPrice} créditos</p>
      <p>Mayor puja: {item.highestBid ?? "Sin pujas"}</p>
      {item.leaderAlias && <p>Líder: {item.leaderAlias}</p>}
      <p>Tiempo restante: {remaining(item.expiresAt)} s</p>
      <button type="button" onClick={() => void showDetail(item.auctionId)}>Ver detalle</button>
    </article>)}</div>
    {cursor && <button type="button" disabled={loading} onClick={() => void load(cursor)}>Cargar más</button>}
    {detailLoading && <p role="status">Cargando detalle...</p>}
    {detailError && <p role="alert">{detailError}</p>}
    {detail && <article aria-label="Detalle de subasta">
      <h3>{detail.title}</h3><img src={detail.imageUrl} alt={detail.title} onError={(event) => { event.currentTarget.src = "/placeholder.svg"; }} />
      <p>{detail.description}</p><p>Categoría: {detail.category}</p><p>Vendedor: {detail.sellerAlias}</p>
      <p>Precio inicial: {detail.initialPrice} créditos</p><p>Mayor puja: {detail.highestBid ?? "Sin pujas"}</p>
      {detail.leaderAlias && <p>Líder: {detail.leaderAlias}</p>}
      <p>{remaining(detail.expiresAt) > 0 ? `Tiempo restante: ${remaining(detail.expiresAt)} s` : "Esta subasta venció."}</p>
      <button type="button" onClick={() => void showDetail(detail.auctionId)}>Actualizar detalle</button>
    </article>}
  </section>;
}
