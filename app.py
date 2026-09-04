"""
Analizador de frecuencia de números
------------------------------------
Aplicación Streamlit que calcula y grafica la frecuencia de aparición de
números a partir de un conjunto de listas.

Flujo:
    1. Carga un conjunto inicial de listas (transcritas desde la foto).
    2. Permite agregar nuevas listas, que se persisten en `data.json`.
    3. Recalcula y grafica la frecuencia (conteo y proporción) en tiempo real.

Ejecución local:
    streamlit run app.py

Despliegue en Streamlit Community Cloud: ver README.md
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
DATA_FILE = Path(__file__).parent / "data.json"

# Dominio esperado de los números (1..25 según la foto). Se usa solo para la
# opción "mostrar rango completo"; el análisis normal detecta el universo real.
UNIVERSE_MIN, UNIVERSE_MAX = 1, 25

# Listas iniciales transcritas desde la foto (cuaderno ESCUDO).
# Cada sublista es una observación. Se ordenan y deduplican al cargar.
INITIAL_LISTS: list[list[int]] = [
    [4, 6, 9, 10, 16, 17, 18, 23, 24],
    [1, 3, 4, 5, 17, 18, 22, 23, 25],
    [1, 4, 5, 9, 10, 17, 18, 23, 24, 25],
    [3, 4, 5, 16, 17, 18, 22, 23, 24, 25],
    [1, 3, 5, 6, 9, 17, 18, 23, 24],
    [1, 3, 5, 9, 16, 17, 18, 22, 23],
    [4, 6, 16, 17, 18, 22, 23, 24, 25],
    [3, 4, 5, 9, 17, 18, 22, 23, 24, 25],
    [1, 3, 4, 5, 6, 9, 18, 22, 23],
    [1, 3, 5, 6, 9, 16, 17, 22, 25],
    [1, 3, 4, 5, 6, 16, 17, 18, 22, 23, 24],
    [1, 3, 6, 9, 14, 17, 18, 22, 25],
    [3, 4, 5, 6, 14, 17, 18, 23, 25],
    [3, 4, 5, 9, 18, 22, 23, 24, 25],
    [1, 6, 9, 16, 18, 22, 23, 24, 25],
    [1, 4, 16, 18, 21, 22, 23, 24, 25],
]


# ---------------------------------------------------------------------------
# Lógica de datos (sin dependencia de Streamlit)
# ---------------------------------------------------------------------------
def normalize_list(numbers: list[int]) -> list[int]:
    """Ordena ascendentemente y elimina duplicados de una lista de enteros."""
    return sorted({int(n) for n in numbers})


def parse_input(text: str) -> list[int]:
    """Convierte texto libre en una lista de enteros normalizada.

    Acepta separadores arbitrarios (comas, espacios, saltos de línea) e ignora
    cualquier caracter no numérico, como la estrella (✪) de la foto.

    Raises:
        ValueError: si no se encuentra ningún número válido.
    """
    tokens = re.split(r"[^\d]+", text.strip())
    numbers = [int(t) for t in tokens if t]
    if not numbers:
        raise ValueError("No se encontraron números válidos en la entrada.")
    return normalize_list(numbers)


def save_data(lists: list[list[int]]) -> None:
    """Persiste las listas en disco como JSON."""
    DATA_FILE.write_text(
        json.dumps(lists, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_data() -> list[list[int]]:
    """Carga las listas desde `data.json`.

    Si el archivo no existe o está corrupto, siembra con `INITIAL_LISTS` y lo
    persiste.
    """
    if DATA_FILE.exists():
        try:
            raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            return [normalize_list(sub) for sub in raw]
        except (json.JSONDecodeError, ValueError, TypeError):
            pass  # Archivo corrupto: se reinicia con las listas iniciales.

    seed = [normalize_list(sub) for sub in INITIAL_LISTS]
    save_data(seed)
    return seed


def compute_frequencies(
    lists: list[list[int]], universe: list[int] | None = None
) -> pd.DataFrame:
    """Calcula apariciones y proporción por número.

    Args:
        lists: colección de listas (observaciones).
        universe: números a incluir. Si es None, se usan solo los observados.

    Returns:
        DataFrame con columnas: número, apariciones, proporción.
    """
    counter: Counter[int] = Counter()
    for sub in lists:
        counter.update(set(sub))  # set() evita contar duplicados dentro de una lista.

    total = len(lists)
    numbers = universe if universe is not None else sorted(counter.keys())

    rows = [
        {
            "número": n,
            "apariciones": counter.get(n, 0),
            "proporción": counter.get(n, 0) / total if total else 0.0,
        }
        for n in numbers
    ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Interfaz
# ---------------------------------------------------------------------------
def render_sidebar() -> tuple[bool, int]:
    """Dibuja la barra lateral (agregar listas, opciones, export/reset).

    Returns:
        (show_full_range, min_apariciones) para controlar la vista principal.
    """
    with st.sidebar:
        st.header("➕ Agregar lista")
        new_text = st.text_area(
            "Números (coma, espacio o salto de línea)",
            placeholder="1, 3, 5, 9, 16, 17, 18, 22, 23",
            height=100,
        )
        if st.button("Agregar y guardar", type="primary", use_container_width=True):
            try:
                parsed = parse_input(new_text)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state.lists.append(parsed)
                save_data(st.session_state.lists)
                st.success(f"Lista agregada: {parsed}")
                st.rerun()

        st.divider()
        st.subheader("Opciones de vista")
        show_full_range = st.checkbox(
            f"Mostrar rango completo {UNIVERSE_MIN}–{UNIVERSE_MAX}",
            value=False,
            help="Incluye números que nunca aparecen (apariciones = 0).",
        )
        max_slider = max(1, len(st.session_state.lists))
        min_apariciones = st.slider(
            "Mínimo de apariciones", 0, max_slider, 0
        )

        st.divider()
        st.download_button(
            "⬇️ Descargar data.json",
            data=json.dumps(st.session_state.lists, ensure_ascii=False, indent=2),
            file_name="data.json",
            mime="application/json",
            use_container_width=True,
            help="Respaldo de las listas. Útil por el almacenamiento efímero de la nube.",
        )
        if st.button("♻️ Restaurar listas iniciales", use_container_width=True):
            st.session_state.lists = [normalize_list(s) for s in INITIAL_LISTS]
            save_data(st.session_state.lists)
            st.rerun()

    return show_full_range, min_apariciones


def render_metrics(df: pd.DataFrame, total: int) -> None:
    """Muestra métricas resumen en tres columnas."""
    c1, c2, c3 = st.columns(3)
    c1.metric("Listas totales", total)
    if not df.empty and df["apariciones"].max() > 0:
        top = df.loc[df["apariciones"].idxmax()]
        c2.metric(
            "Más frecuente",
            int(top["número"]),
            f"{int(top['apariciones'])}/{total}",
        )
    c3.metric("Números distintos", int((df["apariciones"] > 0).sum()))


def render_chart(df: pd.DataFrame) -> None:
    """Grafica la frecuencia por número con Altair."""
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("número:O", title="Número", sort="ascending"),
            y=alt.Y("apariciones:Q", title="Apariciones"),
            color=alt.Color(
                "apariciones:Q", scale=alt.Scale(scheme="blues"), legend=None
            ),
            tooltip=[
                alt.Tooltip("número:O", title="Número"),
                alt.Tooltip("apariciones:Q", title="Apariciones"),
                alt.Tooltip("proporción:Q", title="Proporción", format=".0%"),
            ],
        )
        .properties(height=420)
    )
    st.altair_chart(chart, use_container_width=True)


def render_table(df: pd.DataFrame) -> None:
    """Tabla de frecuencias ordenada de mayor a menor."""
    tabla = df.sort_values("apariciones", ascending=False).reset_index(drop=True)
    tabla["proporción"] = (tabla["proporción"] * 100).round(1).astype(str) + "%"
    st.dataframe(tabla, use_container_width=True, hide_index=True)


def render_list_manager(lists: list[list[int]]) -> None:
    """Lista las observaciones cargadas y permite eliminarlas."""
    for i, sub in enumerate(lists):
        c1, c2 = st.columns([0.9, 0.1])
        c1.write(f"**{i + 1}.** {', '.join(map(str, sub))}")
        if c2.button("🗑️", key=f"del_{i}", help="Eliminar esta lista"):
            st.session_state.lists.pop(i)
            save_data(st.session_state.lists)
            st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="Frecuencia de números", page_icon="📊", layout="wide"
    )

    if "lists" not in st.session_state:
        st.session_state.lists = load_data()

    st.title("📊 Frecuencia de aparición de números")
    st.caption(
        "Datos iniciales transcritos desde la foto. Agrega nuevas listas "
        "en la barra lateral para actualizar el análisis en tiempo real."
    )

    show_full_range, min_apariciones = render_sidebar()

    lists = st.session_state.lists
    total = len(lists)
    if total == 0:
        st.info("No hay listas cargadas. Agrega una desde la barra lateral.")
        return

    universe = (
        list(range(UNIVERSE_MIN, UNIVERSE_MAX + 1)) if show_full_range else None
    )
    df = compute_frequencies(lists, universe=universe)
    df = df[df["apariciones"] >= min_apariciones]

    render_metrics(df, total)

    st.subheader("Frecuencia por número")
    if df.empty:
        st.warning("Ningún número cumple el filtro seleccionado.")
    else:
        render_chart(df)

    with st.expander("Ver tabla de frecuencias"):
        if df.empty:
            st.write("Sin datos para mostrar.")
        else:
            render_table(df)

    with st.expander(f"Ver / eliminar listas ({total})"):
        render_list_manager(lists)


if __name__ == "__main__":
    main()
