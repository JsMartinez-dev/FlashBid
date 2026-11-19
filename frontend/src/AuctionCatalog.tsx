import { useCallback, useEffect, useRef, useState } from "react";
import { Bids } from "./Bids";

type Auction = { auctionId: string; title: string; description?: string; category?: string; imageUrl: string; initialPrice: number; highestBid?: number; leaderAlias?: string; leaderId?: string; sellerId?: string; sellerAlias?: string; winnerUserId?: string; winnerAlias?: string; winningAmount?: number; expiresAt: number; status: string; version: number; serverNow?: number };
type Page = { items: Auction[]; nextCursor: string | null; serverNow: number };
const money = (n: number) => new Intl.NumberFormat("es-CO").format(n);
const clock = (seconds: number) => `${String(Math.floor(seconds / 3600)).padStart(2, "0")}:${String(Math.floor((seconds % 3600) / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;

function AuctionResult({ auction, isWinner, onClose }: { auction: Auction; isWinner: boolean; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { dialog.current?.showModal(); }, []);
  return <dialog ref={dialog} className={`result-dialog ${isWinner ? "result-dialog-winner" : "result-dialog-seller"}`} onCancel={(event) => { event.preventDefault(); onClose(); }} aria-labelledby="result-title" aria-describedby="result-description">
    {isWinner && <div className="result-confetti" aria-hidden="true">{Array.from({ length: 12 }, (_, i) => <i key={i} />)}</div>}
    <button className="result-close" onClick={onClose} aria-label="Cerrar aviso">×</button>
    <div className="result-icon" aria-hidden="true"><span className="material-symbols-outlined">{isWinner ? "emoji_events" : "gavel"}</span></div>
    <p className="eyebrow">{isWinner ? "Una victoria para celebrar" : "Tu subasta ha finalizado"}</p>
    <h2 id="result-title">{isWinner ? "¡Felicidades, ganaste!" : "¡Subasta finalizada!"}</h2>
    <p id="result-description">{isWinner ? <>Tu puja ganó la subasta de <strong>{auction.title}</strong>. Encontrarás esta pieza en tus subastas ganadas.</> : <>La subasta de <strong>{auction.title}</strong> terminó. El ganador fue <strong>{auction.winnerAlias || "el comprador"}</strong> con una puja de <strong>{money(auction.winningAmount ?? 0)} créditos</strong>.</>}</p>
    <button className="result-confirm" onClick={onClose}>Continuar</button>
  </dialog>;
}

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
  const [position, setPosition] = useState(0);
  const [dismissedResult, setDismissedResult] = useState<string | null>(null);
  const touchStart = useRef<number | null>(null);
  const versionRef = useRef(0);
  const walletRefresh = useRef(onWalletChange);
  walletRefresh.current = onWalletChange;

  const load = useCallback(async (next?: string) => {
    setLoading(true); setError("");
    try {
      const query = next ? `?cursor=${encodeURIComponent(next)}` : "";
      const response = await fetch(`${api}/auctions${query}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error("No pudimos cargar las subastas. Inténtalo de nuevo.");
      const page: Page = await response.json();
      setOffset(page.serverNow - Date.now());
      setItems((previous) => next ? [...previous, ...page.items.filter((item) => !previous.some((old) => old.auctionId === item.auctionId))] : page.items);
      setCursor(page.nextCursor);
    } catch (err) { setError(err instanceof Error ? err.message : "No pudimos cargar las subastas."); }
    finally { setLoading(false); }
  }, [api, token]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { const timer = window.setInterval(() => setNow(Date.now()), 1000); return () => window.clearInterval(timer); }, []);
  useEffect(() => {
    if (!detail?.auctionId) return;
    const id = detail.auctionId;
    let stopped = false, attempt = 0, sequence = 0;
    let retry: number | undefined;
    let socket: WebSocket | undefined;
    versionRef.current = detail.version;
    const sync = async () => {
      const request = ++sequence;
      try {
        const response = await fetch(`${api}/auctions/${encodeURIComponent(id)}`, { headers: { Authorization: `Bearer ${token}` } });
        if (stopped || request !== sequence) return;
        if (response.status === 404) { setDetail(null); setDetailError("Esta subasta ya no está disponible."); void load(); return; }
        if (!response.ok) throw new Error();
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
      const url = new URL(import.meta.env.VITE_WS_BASE_URL || api, window.location.href);
      url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
      url.pathname = `${url.pathname.replace(/\/$/, "")}/ws/auctions/${encodeURIComponent(id)}`;
      socket = new WebSocket(url.toString());
      socket.onopen = () => socket?.send(JSON.stringify({ token }));
      socket.onmessage = (message) => {
        try {
          const event = JSON.parse(message.data);
          if (event.auctionId !== id) return;
          if (event.type === "subscribed") { attempt = 0; setConnection("En vivo"); void sync(); return; }
          if (typeof event.version === "number" && event.version > versionRef.current) void sync();
        } catch { void sync(); }
      };
      socket.onclose = (event) => {
        if (stopped) return;
        if (event.code === 1008) { setConnection("Sesión o suscripción no válida. Vuelve a iniciar sesión."); return; }
        setConnection("Conexión interrumpida. La subasta continúa en el servidor; reconectando…");
        retry = window.setTimeout(connect, Math.min(1000 * 2 ** attempt++, 30000));
      };
      socket.onerror = () => socket?.close();
    };
    connect();
    const poll = window.setInterval(() => void sync(), 15000);
    const focus = () => void sync();
    window.addEventListener("focus", focus);
    return () => { stopped = true; sequence++; window.clearInterval(poll); window.clearTimeout(retry); window.removeEventListener("focus", focus); socket?.close(); };
  }, [api, token, detail?.auctionId, load]);

  const remaining = (expiresAt: number) => Math.max(0, Math.ceil((expiresAt - (now + offset)) / 1000));
  const visible = items.filter((item) => remaining(item.expiresAt) > 0);
  const selected = visible.length ? ((position % visible.length) + visible.length) % visible.length : 0;
  const shift = (delta: number) => setPosition((current) => current + delta);

  async function showDetail(id: string) {
    setDetailLoading(true); setDetailError("");
    try {
      const response = await fetch(`${api}/auctions/${encodeURIComponent(id)}`, { headers: { Authorization: `Bearer ${token}` } });
      if (response.status === 404) throw new Error("Esta subasta ya no está disponible.");
      if (!response.ok) throw new Error("No pudimos cargar el detalle.");
      const item: Auction = await response.json();
      if (item.serverNow !== undefined) setOffset(item.serverNow - Date.now());
      setDetail(item); window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) { setDetailError(err instanceof Error ? err.message : "Error al consultar la subasta."); }
    finally { setDetailLoading(false); }
  }

  const picture = (item: Auction) => <img src={item.imageUrl} alt={item.title} loading="lazy" onError={(event) => { event.currentTarget.onerror = null; event.currentTarget.src = "/placeholder.svg"; }} />;
  const card = (item: Auction, variant: string) => <article className={`lot-card ${variant}`}>
    <div className="lot-image">{picture(item)}<span className="lot-time">{clock(remaining(item.expiresAt))}</span></div>
    <div className="lot-info"><h3>{item.title}</h3><div className="lot-bottom"><div><span className="eyebrow">{item.highestBid ? "Puja actual" : "Precio inicial"}</span><strong className="mono">{money(item.highestBid ?? item.initialPrice)} <small>PTS</small></strong></div><button className="dark-button" onClick={() => void showDetail(item.auctionId)}>Ver subasta <span className="material-symbols-outlined" aria-hidden="true">arrow_outward</span></button></div></div>
  </article>;

  if (detail) return <div className="detail-page page-shell">{detail.status === "FINISHED" && (detail.winnerUserId === uid || detail.sellerId === uid) && dismissedResult !== detail.auctionId && <AuctionResult auction={detail} isWinner={detail.winnerUserId === uid} onClose={() => setDismissedResult(detail.auctionId)} />}<button className="back-link" onClick={() => { setDetail(null); setDetailError(""); }}><span className="material-symbols-outlined" aria-hidden="true">arrow_back</span> Volver a explorar</button>
    <div className="detail-heading"><div><p className="eyebrow">Colección / {detail.category || "Subasta"}</p><h1>{detail.title}</h1></div><span className="connection" role="status"><i />{connection || "Conectando…"}</span></div>
    {detailError && <p role="alert" className="error-message">{detailError}</p>}
    <div className="detail-layout"><div className="detail-photo">{picture(detail)}</div><aside className="detail-panel"><div className="detail-panel-top"><span className="eyebrow">Subasta en tiempo real</span><span className="lot-number mono">LOTE / {detail.auctionId.slice(0, 8).toUpperCase()}</span></div>
      <div className="detail-value"><span className="eyebrow">{detail.highestBid ? "Puja actual" : "Precio inicial"}</span><p className="mono">{money(detail.highestBid ?? detail.initialPrice)} <small>PTS</small></p></div>
      <div className="detail-stat-row"><div><span className="eyebrow">Tiempo restante</span><strong className="mono">{detail.status === "FINISHED" ? "FINALIZADA" : remaining(detail.expiresAt) ? clock(remaining(detail.expiresAt)) : "FINALIZANDO"}</strong></div><div><span className="eyebrow">Líder actual</span><strong>{detail.leaderAlias || "Sin pujas"}</strong></div></div>
      <div className="detail-seller"><span className="eyebrow">Publicado por</span><strong>{detail.sellerAlias || "Vendedor"}</strong></div>
      {detail.status === "FINISHED" && <p className="result-note" role="status">{detail.winnerUserId === uid ? "¡Felicidades! Ganaste la subasta." : detail.sellerId === uid ? `Tu subasta finalizó con ${money(detail.winningAmount ?? 0)} créditos. Ganador: ${detail.winnerAlias}.` : `Subasta finalizada. El ganador fue ${detail.winnerAlias}.`}</p>}
      {detail.status !== "FINISHED" && remaining(detail.expiresAt) > 0 && <Bids key={detail.auctionId} api={api} token={token} auctionId={detail.auctionId} sellerId={detail.sellerId} leaderId={detail.leaderId} uid={uid} onAccepted={() => { onWalletChange(); void showDetail(detail.auctionId); void load(); }} />}
      </aside></div><section className="detail-description"><span className="eyebrow">Sobre este lote</span><h2>Los detalles importan.</h2><p>{detail.description || "Sin descripción adicional."}</p><button className="text-button" onClick={() => void showDetail(detail.auctionId)} disabled={detailLoading}>Actualizar detalle <span className="material-symbols-outlined" aria-hidden="true">arrow_outward</span></button></section></div>;

  return <div className="explore-page"><section className="brand-banner"><img src="/Logo%20FlashBid%20con%20Pujas%20Ascendentes.png" alt="FlashBid" /><p>Subastas rápidas en tiempo real con créditos virtuales</p></section>
    <section className="featured-section"><div className="section-heading page-shell"><div><h1>El tiempo está corriendo<span className="gold-dot">.</span></h1></div><div className="arrow-group"><button aria-label="Subasta anterior" onClick={() => shift(-1)} disabled={visible.length < 2}><span className="material-symbols-outlined" aria-hidden="true">arrow_back</span></button><button aria-label="Siguiente subasta" onClick={() => shift(1)} disabled={visible.length < 2}><span className="material-symbols-outlined" aria-hidden="true">arrow_forward</span></button></div></div>
      {loading && !items.length && <p className="empty-state page-shell" role="status">Buscando subastas disponibles…</p>}{error && <p className="empty-state page-shell" role="alert">{error} <button className="text-button" onClick={() => void load()}>Reintentar</button></p>}{!loading && !error && !visible.length && <p className="empty-state page-shell">Todavía no hay subastas activas. Vuelve pronto.</p>}
      {visible.length > 0 && <div className="carousel-wrap" role="region" aria-label="Subastas destacadas, usa las flechas para navegar" tabIndex={0} onKeyDown={(event) => { if (event.key === "ArrowLeft") { event.preventDefault(); shift(-1); } if (event.key === "ArrowRight") { event.preventDefault(); shift(1); } }} onTouchStart={(event) => { touchStart.current = event.touches[0].clientX; }} onTouchEnd={(event) => { if (touchStart.current !== null) { const delta = event.changedTouches[0].clientX - touchStart.current; if (Math.abs(delta) > 40) shift(delta < 0 ? 1 : -1); touchStart.current = null; } }}><div className={`featured-track ${visible.length === 1 ? "single" : ""}`}>
        {visible.length > 1 && <div className="carousel-side" key={`previous-${visible[(selected - 1 + visible.length) % visible.length].auctionId}`}>{card(visible[(selected - 1 + visible.length) % visible.length], "featured-card")}</div>}
        <div className="carousel-center" key={`active-${visible[selected].auctionId}`}>{card(visible[selected], "featured-card")}</div>
        {visible.length > 1 && <div className="carousel-side" key={`next-${visible[(selected + 1) % visible.length].auctionId}`}>{card(visible[(selected + 1) % visible.length], "featured-card")}</div>}
      </div><div className="carousel-meta"><span className="mono">{String(selected + 1).padStart(2, "0")} / {String(visible.length).padStart(2, "0")}</span><div className="carousel-dots">{visible.map((item, i) => <button key={item.auctionId} aria-label={`Ir a ${item.title}`} aria-current={i === selected ? "true" : undefined} className={i === selected ? "active" : ""} onClick={() => setPosition(i)} />)}</div><span className="eyebrow">Desliza para explorar</span></div></div>}
    </section>
    <section className="catalog-section page-shell" id="catalogo"><div className="section-heading"><div><span className="eyebrow gold-text">La colección</span><h2>Subastas disponibles</h2><p>Encuentra algo que valga la pena esperar.</p></div><button className="text-button" onClick={() => void load()} disabled={loading}>Actualizar catálogo <span className="material-symbols-outlined" aria-hidden="true">refresh</span></button></div>
      {detailError && <p className="error-message" role="alert">{detailError}</p>}{detailLoading && <p role="status">Abriendo subasta…</p>}
      <div className="catalog-grid">{visible.map((item) => <div key={item.auctionId}>{card(item, "catalog-card")}</div>)}</div>
      {cursor && <div className="load-more"><button className="outline-button" onClick={() => void load(cursor)} disabled={loading}>{loading ? "Cargando…" : "Ver más subastas"}</button></div>}
    </section></div>;
}
