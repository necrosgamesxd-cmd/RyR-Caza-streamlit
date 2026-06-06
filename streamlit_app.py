"""
📊 R&R Caza - Dashboard Streamlit
===================================
Dashboard interactivo para buscar ofertas, ver seguimientos
y recibir alertas en tiempo real.

Uso:
    streamlit run streamlit_app.py --server.port 8501
    (Asegúrate de que la API FastAPI esté corriendo en puerto 8000)
"""

import json
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
from sseclient import SSEClient

# ─── Configuración ───────────────────────────────────────────────────

PAGE_TITLE = "R&R Caza 🎯"
API_BASE = st.secrets.get("API_URL", "http://localhost:8000")
ICONO = "🎯"

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=ICONO,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Estilos CSS ─────────────────────────────────────────────────────

st.markdown("""
<style>
    .stApp { background-color: #0f0f1a; }
    .main-header { text-align: center; padding: 1rem 0; }
    .main-header h1 { font-size: 2.5rem; background: linear-gradient(135deg, #ff6b6b, #ffd93d);
                      -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .oferta-card { background: linear-gradient(135deg, #1a1a2e, #16213e);
                   border: 1px solid rgba(255,107,107,0.3); border-radius: 12px;
                   padding: 1rem; margin: 0.5rem 0; transition: transform 0.2s; }
    .oferta-card:hover { transform: translateY(-2px); border-color: #ff6b6b; }
    .precio-actual { color: #2ecc71; font-size: 1.5rem; font-weight: bold; }
    .precio-lista { color: #95a5a6; text-decoration: line-through; font-size: 0.9rem; }
    .descuento-badge { background: linear-gradient(135deg, #e74c3c, #c0392b);
                       color: white; padding: 2px 10px; border-radius: 20px;
                       font-size: 0.8rem; font-weight: bold; }
    .imperdible { border-color: #ffd700 !important;
                  box-shadow: 0 0 15px rgba(255,215,0,0.3); }
    .excelente { border-color: #2ecc71 !important; }
    .stMetric label { color: #95a5a6 !important; }
    .tienda-tag { background: rgba(255,255,255,0.1); padding: 2px 8px;
                  border-radius: 12px; font-size: 0.75rem; }
    div[data-testid="stSidebarNav"] { display: none; }
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

# ─── Estado de sesión ───────────────────────────────────────────────

if "alertas" not in st.session_state:
    st.session_state.alertas = []
if "buscando" not in st.session_state:
    st.session_state.buscando = False
if "resultados_busqueda" not in st.session_state:
    st.session_state.resultados_busqueda = {}
if "busqueda_completada" not in st.session_state:
    st.session_state.busqueda_completada = False


# ─── Helpers ────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def obtener_alertas(limit=50, solo_no_leidas=False):
    """Obtiene notificaciones desde la API"""
    try:
        params = {"limit": limit, "solo_no_leidas": solo_no_leidas}
        resp = requests.get(f"{API_BASE}/api/alertas", params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("notificaciones", [])
    except Exception:
        return []
    return []


@st.cache_data(ttl=30)
def obtener_seguimientos():
    """Obtiene productos en seguimiento"""
    try:
        resp = requests.get(f"{API_BASE}/api/seguimiento", timeout=10)
        if resp.status_code == 200:
            return resp.json().get("seguimientos", [])
    except Exception:
        return []
    return []


def marcar_leida(id_notif):
    try:
        requests.post(f"{API_BASE}/api/alertas/{id_notif}/leer", timeout=5)
        st.cache_data.clear()
        st.rerun()
    except Exception:
        pass


def marcar_todas_leidas():
    try:
        requests.post(f"{API_BASE}/api/alertas/leer-todas", timeout=5)
        st.cache_data.clear()
        st.rerun()
    except Exception:
        pass


def eliminar_seguimiento(sku, tienda):
    try:
        requests.delete(f"{API_BASE}/api/seguimiento/{sku}",
                        params={"tienda": tienda}, timeout=5)
        st.cache_data.clear()
        st.rerun()
    except Exception:
        pass


def formatear_moneda(precio, moneda="CLP"):
    if moneda == "USD":
        return f"${precio:,.2f} USD"
    return f"${precio:,.0f}"


def etiqueta_score(score):
    if score >= 9:
        return "🔥 IMPERDIBLE", "#ffd700"
    if score >= 7:
        return "✅ EXCELENTE", "#2ecc71"
    if score >= 5:
        return "👍 BUENA", "#3498db"
    return "👀 REGULAR", "#95a5a6"


def _consumir_sse(url, params):
    """
    Consume TODOS los eventos SSE y devuelve los resultados acumulados.
    NO llama a st.rerun() dentro del loop — acumula todo primero.
    """
    resultados = {}
    resp = requests.get(url, params=params, stream=True, timeout=120)
    resp.raise_for_status()
    try:
        client = SSEClient(resp)
        for event in client:
            if not event.data:
                continue
            data = json.loads(event.data)
            fuente = data.get("fuente", "")
            if fuente == "__done__":
                break
            if fuente == "__ia__":
                resultados["__ia__"] = data.get("grupos", [])
            else:
                prods = data.get("productos", [])
                if prods:
                    resultados[fuente] = prods
    finally:
        resp.close()
    return resultados


# ─── Sidebar ────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3621/3621435.png", width=60)
    st.markdown("## 🎯 R&R Caza")
    st.markdown("---")
    pagina = st.radio(
        "Navegación",
        ["🔍 Buscar Ofertas", "📈 Seguimiento", "🔔 Alertas", "📊 Estadísticas"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption(f"API: {API_BASE}")
    st.caption(f"🕒 {datetime.now().strftime('%H:%M:%S')}")


# ─── PÁGINA 1: Buscar Ofertas ──────────────────────────────────────

def pagina_buscar():
    st.markdown('<div class="main-header"><h1>🔍 Buscar Ofertas</h1></div>',
                unsafe_allow_html=True)

    # ── Si hay una búsqueda en progreso, mostrar spinner ──────
    if st.session_state.buscando:
        with st.spinner("Buscando en todas las tiendas..."):
            try:
                url = f"{API_BASE}/api/search"
                params = {"q": st.session_state.query_actual, "min_discount": st.session_state.min_dto_actual / 100}
                st.session_state.resultados_busqueda = _consumir_sse(url, params)
            except requests.exceptions.ConnectionError:
                st.error("❌ No se pudo conectar con la API. ¿Está corriendo FastAPI?")
            except Exception as e:
                st.error(f"Error en la búsqueda: {e}")
            finally:
                st.session_state.buscando = False
                st.session_state.busqueda_completada = True
                st.rerun()
        st.stop()

    # ── Formulario de búsqueda ───────────────────────────────
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        query = st.text_input("¿Qué buscas?", placeholder="ej: teclado mecánico, audífonos...",
                              label_visibility="collapsed")
    with col2:
        min_dto = st.number_input("Dto. mínimo %", min_value=0, max_value=100,
                                  value=50, step=5)
    with col3:
        buscar = st.button("🎯 Buscar", type="primary", use_container_width=True)

    if buscar and query:
        st.session_state.buscando = True
        st.session_state.busqueda_completada = False
        st.session_state.resultados_busqueda = {}
        st.session_state.query_actual = query
        st.session_state.min_dto_actual = min_dto
        st.rerun()
        st.stop()

    # ── Mostrar resultados ───────────────────────────────────
    resultados = st.session_state.resultados_busqueda

    if not resultados:
        if st.session_state.busqueda_completada:
            st.warning("😕 No se encontraron ofertas con esos criterios.")
        else:
            st.info("💡 Ingresa un producto y presiona **Buscar** para empezar.")
        return

    # Métricas generales
    total_productos = sum(len(p) for f, p in resultados.items() if f != "__ia__")
    total_tiendas = sum(1 for f in resultados if f != "__ia__" and len(resultados[f]) > 0)
    total_grupos = len(resultados.get("__ia__", []))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🛒 Productos", total_productos)
    col2.metric("🏪 Tiendas", total_tiendas)
    col3.metric("📦 Grupos IA", total_grupos)
    col4.metric("⏱️ Estado", "✅ Completo")

    st.markdown("---")

    # ── Grupos IA ──────────────────────────────────────────────
    grupos_ia = resultados.get("__ia__", [])
    if grupos_ia:
        with st.expander(f"🤖 Agrupación IA ({len(grupos_ia)} grupos)", expanded=True):
            for idx, grupo in enumerate(grupos_ia):
                with st.container():
                    cols = st.columns([3, 1])
                    with cols[0]:
                        st.markdown(f"**Grupo {idx + 1}** — {len(grupo)} productos")
                    with cols[1]:
                        if grupo[0].get("score_ia"):
                            score = grupo[0]["score_ia"]
                            etiq, color = etiqueta_score(score)
                            st.markdown(f"<span style='color:{color}'>{etiq} ({score}/10)</span>",
                                        unsafe_allow_html=True)

                    for p in grupo:
                        st.markdown(
                            f"""<div style='padding:0.3rem 1rem;margin:0.2rem 0;
                            background:rgba(255,255,255,0.03);border-radius:8px'>
                            <span class='tienda-tag'>{p['tienda']}</span>
                            <strong>{p['nombre'][:60]}</strong>
                            <span class='precio-actual'>${p['precio_actual']:,.0f}</span>
                            </div>""",
                            unsafe_allow_html=True
                        )
                    st.markdown("---")

    # ── Por tienda ──────────────────────────────────────────────
    tiendas_con_productos = {f: p for f, p in resultados.items()
                            if f != "__ia__" and p}

    if tiendas_con_productos:
        tab_labels = list(tiendas_con_productos.keys())
        tabs = st.tabs(tab_labels)

        for i, (fuente, productos) in enumerate(tiendas_con_productos.items()):
            with tabs[i]:
                st.caption(f"{len(productos)} productos encontrados")
                for p in productos:
                    desc = p.get("descuento_real", p.get("descuento_publicitado", 0))
                    with st.container():
                        cols = st.columns([1, 3, 1, 1])
                        with cols[0]:
                            img = p.get("imagen_url")
                            if img:
                                st.image(img, width=80)
                        with cols[1]:
                            st.markdown(f"**{p['nombre'][:80]}**")
                            st.caption(f"📦 SKU: {p.get('sku', '')[:20]}")
                        with cols[2]:
                            st.markdown(
                                f"<span class='precio-actual'>{formatear_moneda(p.get('precio_actual', 0), p.get('moneda', 'CLP'))}</span>",
                                unsafe_allow_html=True)
                            if p.get("precio_lista", 0) > p.get("precio_actual", 0):
                                st.markdown(
                                    f"<span class='precio-lista'>{formatear_moneda(p.get('precio_lista', 0), p.get('moneda', 'CLP'))}</span>",
                                    unsafe_allow_html=True)
                        with cols[3]:
                            st.markdown(
                                f"<span class='descuento-badge'>-{desc:.0f}%</span>",
                                unsafe_allow_html=True)


# ─── PÁGINA 2: Seguimiento ─────────────────────────────────────────

def pagina_seguimiento():
    st.markdown('<div class="main-header"><h1>📈 Productos en Seguimiento</h1></div>',
                unsafe_allow_html=True)

    seguimientos = obtener_seguimientos()

    if not seguimientos:
        st.info("📭 No hay productos en seguimiento. Busca productos y se agregarán automáticamente.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("📦 En seguimiento", len(seguimientos))
    activos = sum(1 for s in seguimientos if s.get("activo", 1))
    col2.metric("✅ Activos", activos)
    col3.metric("⏰ Pendientes", sum(1 for s in seguimientos if not s.get("ultima_revision")))

    for s in seguimientos:
        with st.container():
            cols = st.columns([4, 1, 1, 0.5])
            with cols[0]:
                st.markdown(f"**{s['nombre'][:60]}**")
                st.caption(f"🏪 {s.get('tienda', 'Amazon')} | 📦 {s.get('sku', '')[:20]}")
            with cols[1]:
                ultima = s.get("ultima_revision")
                if ultima:
                    st.caption(f"🕐 {ultima[:10]}")
                else:
                    st.caption("🕐 Pendiente")
            with cols[2]:
                if s.get("url"):
                    st.markdown(f"[🔗 Ver]({s['url']})")
            with cols[3]:
                if st.button("🗑️", key=f"del_{s['sku']}_{s.get('tienda', 'Amazon')}",
                             help="Eliminar seguimiento"):
                    eliminar_seguimiento(s["sku"], s.get("tienda", "Amazon"))
            st.markdown("---")


# ─── PÁGINA 3: Alertas ─────────────────────────────────────────────

def pagina_alertas():
    st.markdown('<div class="main-header"><h1>🔔 Alertas de Ofertas</h1></div>',
                unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        solo_no_leidas = st.checkbox("Solo no leídas", value=True)
    with col2:
        if st.button("📖 Marcar todas leídas", type="secondary"):
            marcar_todas_leidas()
    with col3:
        st.caption("Las alertas se actualizan cada 30s")

    alertas = obtener_alertas(solo_no_leidas=solo_no_leidas)

    if not alertas:
        st.info("🔕 No hay alertas nuevas. Las ofertas aparecerán aquí automáticamente.")
        return

    col1, col2 = st.columns(2)
    col1.metric("🔔 Alertas", len(alertas))
    no_leidas = sum(1 for a in alertas if not a.get("leido"))
    col2.metric("📩 Sin leer", no_leidas)

    st.markdown("---")

    for a in alertas:
        desc = a.get("descuento_real", 0)
        score = a.get("score_ia")
        clase_adicional = ""
        if score and score >= 9:
            clase_adicional = "imperdible"
        elif score and score >= 7:
            clase_adicional = "excelente"

        with st.container():
            st.markdown(f'<div class="oferta-card {clase_adicional}">',
                        unsafe_allow_html=True)
            cols = st.columns([1, 3, 1, 1, 0.5])

            with cols[0]:
                img = a.get("imagen_url")
                if img:
                    st.image(img, width=70)
            with cols[1]:
                st.markdown(f"**{a.get('nombre_producto', '')[:80]}**")
                st.caption(f"🏪 {a.get('tienda', '')} | 📅 {a.get('fecha_detectado', '')[:10]}")
                mensaje_ia = a.get("mensaje_ia")
                if mensaje_ia:
                    st.caption(f"💬 {mensaje_ia}")
            with cols[2]:
                st.markdown(
                    f"<span class='precio-actual'>{formatear_moneda(a.get('precio_actual', 0), a.get('moneda', 'USD'))}</span>",
                    unsafe_allow_html=True)
                if a.get("precio_referencia"):
                    st.markdown(
                        f"<span class='precio-lista'>{formatear_moneda(a.get('precio_referencia', 0), a.get('moneda', 'USD'))}</span>",
                        unsafe_allow_html=True)
            with cols[3]:
                st.markdown(f"<span class='descuento-badge'>-{desc:.0f}%</span>",
                            unsafe_allow_html=True)
                if score:
                    etiq, color = etiqueta_score(score)
                    st.markdown(f"<span style='color:{color};font-size:0.75rem'>{etiq}</span>",
                                unsafe_allow_html=True)
                if a.get("precio_chile"):
                    st.caption(f"🇨🇱 Mejor Chile: ${a['precio_chile']:,.0f}")
            with cols[4]:
                if not a.get("leido"):
                    if st.button("✅", key=f"read_{a['id']}", help="Marcar leída"):
                        marcar_leida(a["id"])

            st.markdown('</div>', unsafe_allow_html=True)


# ─── PÁGINA 4: Estadísticas ────────────────────────────────────────

def pagina_estadisticas():
    st.markdown('<div class="main-header"><h1>📊 Estadísticas</h1></div>',
                unsafe_allow_html=True)

    alertas = obtener_alertas(limit=200)

    if not alertas:
        st.info("📊 No hay suficientes datos aún. Vuelve cuando tengas alertas acumuladas.")
        return

    df = pd.DataFrame(alertas)
    if "descuento_real" in df.columns:
        df["descuento_real"] = pd.to_numeric(df["descuento_real"], errors="coerce")

    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Total Alertas", len(df))
    if "descuento_real" in df.columns:
        col2.metric("🏆 Mejor Descuento", f"{df['descuento_real'].max():.0f}%")
        col3.metric("📐 Promedio Descuento", f"{df['descuento_real'].mean():.0f}%")

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📈 Descuentos", "🏪 Por Tienda", "🔥 Top Ofertas"])

    with tab1:
        if "descuento_real" in df.columns:
            st.subheader("Distribución de Descuentos")
            bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
            labels = [f"{b}-{b+10}%" for b in bins[:-1]]
            df["rango"] = pd.cut(df["descuento_real"], bins=bins, labels=labels, right=False)
            counts = df["rango"].value_counts().sort_index()
            st.bar_chart(counts)

    with tab2:
        if "tienda" in df.columns:
            st.subheader("Ofertas por Tienda")
            tiendas_counts = df["tienda"].value_counts()
            st.bar_chart(tiendas_counts)
            st.dataframe(tiendas_counts.rename("Cantidad"))

    with tab3:
        if "descuento_real" in df.columns:
            st.subheader("🔥 Top 10 Mejores Descuentos")
            top = df.nlargest(10, "descuento_real")[
                ["nombre_producto", "tienda", "descuento_real", "precio_actual"]
            ].copy()
            top["descuento_real"] = top["descuento_real"].round(1).astype(str) + "%"
            top.columns = ["Producto", "Tienda", "Descuento", "Precio"]
            st.dataframe(top, use_container_width=True, hide_index=True)


# ─── Router ─────────────────────────────────────────────────────────

if pagina == "🔍 Buscar Ofertas":
    pagina_buscar()
elif pagina == "📈 Seguimiento":
    pagina_seguimiento()
elif pagina == "🔔 Alertas":
    pagina_alertas()
elif pagina == "📊 Estadísticas":
    pagina_estadisticas()

# ─── Footer ─────────────────────────────────────────────────────────

st.markdown("---")
cols = st.columns(3)
with cols[1]:
    st.caption("🔄 Auto-refresh cada 30s | Hecho con ❤️ por R&R Caza")
