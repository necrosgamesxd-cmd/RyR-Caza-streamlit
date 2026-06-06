# 📊 Dashboard Streamlit para R&R Caza

Guía para crear un dashboard interactivo en **Streamlit** que consuma la API de R&R Caza y muestre ofertas en tiempo real.

---

## 🎯 Objetivo

Crear una interfaz web alternativa (o complementaria) al frontend HTML estático actual. Streamlit permite crear dashboards interactivos con poco código, ideales para monitoreo de ofertas, análisis de precios y visualizaciones.

---

## 🧩 Arquitectura

```
┌──────────────────────────────────────┐
│         FastAPI (backend)            │
│  - API REST                          │
│  - SSE streaming                     │
│  - Base de datos SQLite              │
└──────────────┬───────────────────────┘
               │ HTTP / SSE
               ▼
┌──────────────────────────────────────┐
│    Streamlit (frontend alternativo)  │
│  - Dashboard de ofertas             │
│  - Búsqueda interactiva              │
│  - Gráficos de precios              │
│  - Alertas en tiempo real           │
└──────────────────────────────────────┘
```

---

## 🚀 Cómo Ejecutar

### 1. Instalar dependencias

```bash
pip install -r posibles_mejoras/streamlite/requirements.txt
```

### 2. Asegurar que FastAPI esté corriendo

```bash
uvicorn app.main:app --reload --port 8000
```

### 3. Iniciar Streamlit

```bash
streamlit run posibles_mejoras/streamlite/streamlit_app.py --server.port 8501
```

### 4. Abrir navegador

Visita `http://localhost:8501`

---

## 🖥️ Funcionalidades del Dashboard

### Pestaña 1: 🔍 Buscar Ofertas
- Buscador de productos con filtro de descuento mínimo
- Resultados en tarjetas visuales con imágenes
- Vista por tienda y agrupada por IA (productos similares)
- Métricas del mejor descuento encontrado

### Pestaña 2: 📈 Seguimiento
- Lista de productos en seguimiento
- Precio actual, último precio, descuento
- Botones para eliminar seguimiento
- Gráfico de evolución de precios (una vez integrado)

### Pestaña 3: 🔔 Alertas
- Notificaciones de ofertas detectadas
- Filtro: todas / no leídas
- Marcar como leídas individual o masivamente
- Notificaciones en tiempo real vía SSE

### Pestaña 4: 📊 Estadísticas
- Distribución de descuentos (histograma)
- Ofertas por tienda (gráfico de barras)
- Top ofertas del día
- Precio promedio por categoría

---

## 🔌 API Endpoints Utilizados

| Endpoint | Método | Uso en Streamlit |
|----------|--------|------------------|
| `/api/search?q=...` | SSE | Búsqueda en vivo con streaming |
| `/api/alertas` | GET | Listar notificaciones |
| `/api/alertas/{id}/leer` | POST | Marcar notif. como leída |
| `/api/alertas/leer-todas` | POST | Marcar todas leídas |
| `/api/alertas/eventos` | SSE | Alertas en tiempo real |
| `/api/seguimiento` | GET/POST | Gestionar seguimientos |

---

## 🎨 Personalización

### Estilos CSS
Streamlit permite inyectar CSS custom:
```python
st.markdown("""
<style>
    .oferta-card { border: 2px solid #ff6b6b; border-radius: 10px; padding: 15px; }
    .precio-actual { color: #2ecc71; font-size: 24px; font-weight: bold; }
    .descuento { color: #e74c3c; font-weight: bold; }
</style>
""", unsafe_allow_html=True)
```

### Layout
Usa `st.columns`, `st.tabs`, `st.expander`, `st.sidebar` para organizar la UI.

### Datos en tiempo real
Con `sseclient-py` puedes escuchar eventos SSE:
```python
import sseclient
import requests

response = requests.get('http://localhost:8000/api/alertas/eventos', stream=True)
client = sseclient.SSEClient(response)
for event in client:
    st.toast(f"🔥 Nueva oferta: {event.data}")
```

---

## 🐳 Despliegue

### Con Docker
```bash
docker build -t rr-caza-streamlit -f posibles_mejoras/streamlite/Dockerfile .
docker run -p 8501:8501 rr-caza-streamlit
```

### En Streamlit Community Cloud (ya configurado ✅)

Este dashboard está diseñado para funcionar con **Tailscale Funnel** apuntando a tu PC local.

**URL de la API (ya activa):**
```
https://letum.taild3612e.ts.net
```

#### Pasos para desplegar:

1. **Sube el proyecto a GitHub** (si no lo has hecho):
   ```bash
   cd /ruta/a/rr-caza
   git add .
   git commit -m "feat: Streamlit dashboard + Tailscale setup"
   git push
   ```

2. **Ve a [share.streamlit.io](https://share.streamlit.io)**
   - Inicia sesión con GitHub
   - Conecta tu repo
   - Apunta a: `posibles_mejoras/streamlite/streamlit_app.py`
   - Haz clic en **Deploy**

3. **Configura el Secret** en la app desplegada:
   - Settings → Secrets → Add secret
   - `API_URL = https://letum.taild3612e.ts.net`
   - La app se reinicia sola

4. **¡Listo!** Tu dashboard vive en:
   ```
   https://tu-app.streamlit.app
   ```
   Abrelo desde el celu, PC, donde sea. Tu PC local debe estar encendida con FastAPI y Tailscale Funnel activo.

> ⚠️ **Requisitos**: Tu PC debe estar encendida con:
> - FastAPI corriendo en puerto 8000
> - Tailscale Funnel activo (`sudo tailscale funnel --yes 8000`)

---

## 📈 Posibles Mejoras Futuras

- [ ] **Gráficos interactivos**: Plotly para evolución de precios
- [ ] **Comparación lado a lado**: Mismo producto en distintas tiendas
- [ ] **Historial de precios**: Gráfico temporal con mínimos históricos
- [ ] **Alertas configurables**: Umbral de descuento personalizado
- [ ] **Modo oscuro**: Tema oscuro nativo de Streamlit
- [ ] **Exportar datos**: CSV de ofertas encontradas
- [ ] **Multi-idioma**: Español/Inglés
