import { useCallback, useEffect, useRef, useState } from "react";
import { Bids } from "./Bids";

type Auction = { auctionId: string; title: string; description?: string; category?: string; imageUrl: string; initialPrice: number; highestBid?: number; leaderAlias?: string; leaderId?: string; sellerId?: string; sellerAlias?: string; winnerUserId?: string; winnerAlias?: string; winningAmount?: number; expiresAt: number; status: string; version: number; serverNow?: number };
type Page = { items: Auction[]; nextCursor: string | null; serverNow: number };

export function AuctionCatalog({ api, token, uid, onWalletChange }: { api: string; token: string; uid: string; onWalletChange: () => void }) {
  const [items, setItems] = useState<Auction[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [detail, setDetail] = useState<Auction | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [offset, setOffset] = useState(0);
  const [now, setNow] = useState(Date.now());
  const [connection, setConnection] = useState("");
  const versionRef = useRef(0);
  const walletRefresh = useRef(onWalletChange);
  walletRefresh.current = onWalletChange;

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
  useEffect(() => {
    if (!detail?.auctionId) return;
    const id = detail.auctionId;
    let stopped = false;
    let attempt = 0;
    let retry: number | undefined;
    let socket: WebSocket | undefined;
    let requestSequence = 0;
    versionRef.current = detail.version;
    const sync = async () => {
      const sequence = ++requestSequence;
      try {
        const response = await fetch(`${api}/auctions/${encodeURIComponent(id)}`, { headers: { Authorization: `Bearer ${token}` } });
        if (stopped || sequence !== requestSequence) return;
        if (response.status === 404) {
          setDetail(null); setDetailError("La subasta ya no está disponible."); void load(); return;
        }
        if (!response.ok) throw new Error("No se pudo sincronizar la subasta.");
        const current: Auction = await response.json();
        if (current.version >= versionRef.current) {
          versionRef.current = current.version;
          setDetail((previous) => previous?.auctionId === id ? current : previous);
          if (current.serverNow !== undefined) setOffset(current.serverNow - Date.now());
        }
        walletRefresh.current();
        window.dispatchEvent(new CustomEvent("flashbid:auction-update", { detail: { auctionId: id } }));
        window.dispatchEvent(new Event("flashbid:refresh-wins"));
      } catch { if (!stopped) setConnection("No se pudo sincronizar; reintentando."); }
    };
    const connect = () => {
      if (stopped) return;
      const configured = import.meta.env.VITE_WS_BASE_URL || api;
      const url = new URL(configured, window.location.href);
      url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
      url.pathname = `${url.pathname.replace(/\/$/, "")}/ws/auctions/${encodeURIComponent(id)}`;
      socket = new WebSocket(url.toString());
      socket.onopen = () => { socket?.send(JSON.stringify({ token })); };
      socket.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data);
          if (event.auctionId !== id) return;
          if (event.type === "subscribed") { attempt = 0; setConnection("En vivo"); void sync(); return; }
          if (typeof event.version !== "number" || event.version <= versionRef.current) return;
          // La lectura HTTP es autoritativa y también recupera cambios intermedios.
          void sync();
        } catch { void sync(); }
      };
      socket.onclose = (event) => {
        if (stopped) return;
        if (event.code === 1008) { setConnection("Sesión o suscripción no válida. Vuelve a iniciar sesión."); return; }
        setConnection("Conexión en tiempo real interrumpida. La subasta continúa en el servidor; reconectando…");
        retry = window.setTimeout(connect, Math.min(1000 * 2 ** attempt++, 30000));
      };
      socket.onerror = () => socket?.close();
    };
    connect();
    const poll = window.setInterval(() => void sync(), 15000);
    const onFocus = () => void sync();
    window.addEventListener("focus", onFocus);
    return () => { stopped = true; requestSequence++; window.clearInterval(poll); window.clearTimeout(retry); window.removeEventListener("focus", onFocus); socket?.close(); };
  }, [api, token, detail?.auctionId, load]);
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
      <p role="status">{connection}</p>
      <h3>{detail.title}</h3><img src={detail.imageUrl} alt={detail.title} onError={(event) => { event.currentTarget.src = "/placeholder.svg"; }} />
      <p>{detail.description}</p><p>Categoría: {detail.category}</p><p>Vendedor: {detail.sellerAlias}</p>
      <p>Precio inicial: {detail.initialPrice} créditos</p><p>Mayor puja: {detail.highestBid ?? "Sin pujas"}</p>
      {detail.leaderAlias && <p>Líder: {detail.leaderAlias}</p>}
      <p>{detail.status === "FINISHED" ? "Finalizada" : remaining(detail.expiresAt) > 0 ? `Tiempo restante: ${remaining(detail.expiresAt)} s` : "Finalizando..."}</p>
      {detail.status === "FINISHED" && <p role="status">{detail.winnerUserId === uid ? "¡Felicidades! Ganaste la subasta." : detail.sellerId === uid ? `Tu subasta finalizó con ${detail.winningAmount} créditos. Ganador: ${detail.winnerAlias}.` : `Subasta finalizada. El ganador fue ${detail.winnerAlias}.`}</p>}
      <button type="button" onClick={() => void showDetail(detail.auctionId)}>Actualizar detalle</button>
      {detail.status !== "FINISHED" && remaining(detail.expiresAt) > 0 && <Bids key={detail.auctionId} api={api} token={token} auctionId={detail.auctionId} sellerId={detail.sellerId} leaderId={detail.leaderId} uid={uid} onAccepted={() => { onWalletChange(); void showDetail(detail.auctionId); void load(); }} />}
    </article>}
  </section>;
}
