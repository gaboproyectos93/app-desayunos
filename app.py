import streamlit as st
import pandas as pd
import datetime
from zoneinfo import ZoneInfo
import db_desayunos as db 

st.set_page_config(page_title="Menú Desayunos", page_icon="🥪", layout="centered")

def obtener_hora_chile():
    try: return datetime.datetime.now(ZoneInfo("America/Santiago"))
    except: return datetime.datetime.utcnow() - datetime.timedelta(hours=4)

def inyectar_css():
    estilo = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&family=Oswald:wght@500&display=swap');
    .titulo-nuestro {{ font-family: 'Dancing Script', cursive; font-size: 4rem; text-align: center; margin-bottom: -30px; }}
    .titulo-menu {{ font-family: 'Oswald', sans-serif; font-size: 4.5rem; text-align: center; letter-spacing: 6px; margin-bottom: 20px; }}
    @media (prefers-color-scheme: light) {{ .titulo-nuestro {{ color: #2C3E50; }} .titulo-menu {{ color: #D35400; }} }}
    @media (prefers-color-scheme: dark) {{ .titulo-nuestro {{ color: #ffffff; }} .titulo-menu {{ color: #F39C12; }} }}
    
    button[kind="primary"] {{ background-color: #F39C12 !important; color: #000000 !important; border: 1px solid #F39C12 !important; transition: all 0.3s ease !important; }}
    button[kind="primary"]:hover {{ background-color: #D35400 !important; border-color: #D35400 !important; }}
    button[kind="secondary"] {{ background-color: transparent !important; color: #F39C12 !important; border: 1px solid #F39C12 !important; transition: all 0.3s ease !important; }}
    button[kind="secondary"]:hover {{ background-color: rgba(243, 156, 18, 0.1) !important; border-color: #F39C12 !important; }}
    </style>
    """
    st.markdown(estilo, unsafe_allow_html=True)

if "paso_wizard" not in st.session_state: st.session_state.paso_wizard = 1
if "nombre_cliente" not in st.session_state: st.session_state.nombre_cliente = ""
if "carrito" not in st.session_state: st.session_state.carrito = []

def parse_price(val):
    try: return int(val)
    except: return 0

def agregar_al_carrito(id_prod, nombre, tamano, precio_num):
    for item in st.session_state.carrito:
        if item["id_prod"] == id_prod and item["tamano"] == tamano:
            item["cantidad"] += 1
            return
    st.session_state.carrito.append({
        "id_prod": id_prod, "nombre": nombre, "tamano": tamano, 
        "cantidad": 1, "precio_texto": f"{tamano} (${precio_num})"
    })

# ==========================================
# VISTA CLIENTE
# ==========================================
def vista_cliente():
    st.markdown("<div class='titulo-nuestro'>Nuestro</div>", unsafe_allow_html=True)
    st.markdown("<div class='titulo-menu'>MENÚ</div>", unsafe_allow_html=True)
    
    estado_sistema = db.get_estado_sistema()
    if estado_sistema == "Cerrado":
        st.error("⏳ **La cocina está cerrada.** No estamos recibiendo pedidos en este momento. ¡Avisaremos cuando abramos!")
        return

    ahora = obtener_hora_chile()
    fecha_entrega = (ahora + datetime.timedelta(days=1)).date() if ahora.hour < 20 else (ahora + datetime.timedelta(days=2)).date()
    st.info(f"📅 Pedidos para la mañana del: **{fecha_entrega.strftime('%d-%m-%Y')}**")

    if st.session_state.paso_wizard == 1:
        with st.container(border=True):
            st.subheader("👋 ¡Hola! ¿Para quién es el pedido?")
            nombre = st.text_input("Ingresa tu Nombre y Apellido", value=st.session_state.nombre_cliente)
            
            if st.button("Continuar al Menú ➔", type="primary", use_container_width=True):
                if not nombre.strip(): st.error("Por favor, dinos tu nombre para poder entregarte el pan.")
                else:
                    st.session_state.nombre_cliente = nombre.strip()
                    st.session_state.paso_wizard = 2
                    st.rerun()

    elif st.session_state.paso_wizard == 2:
        df_productos = db.get_productos()
        col_izq, col_der = st.columns([3, 1])
        col_izq.subheader(f"🛒 ¿Qué se te antoja, {st.session_state.nombre_cliente.split()[0]}?")
        
        if st.session_state.carrito:
            if col_der.button(f"🛒 Ver pedido ({sum(i['cantidad'] for i in st.session_state.carrito)})", type="primary", use_container_width=True):
                st.session_state.paso_wizard = 3
                st.rerun()
        else:
            if col_der.button("Volver", use_container_width=True):
                st.session_state.paso_wizard = 1
                st.rerun()

        for index, prod_data in df_productos.iterrows():
            precio_n, precio_xl = parse_price(prod_data['precio_normal']), parse_price(prod_data['precio_xl'])
            with st.container(border=True):
                st.markdown(f"#### 🥪 {prod_data['nombre']}")
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if precio_n > 0 and st.button(f"➕ Normal (${precio_n})", key=f"btn_n_{prod_data['id']}", use_container_width=True):
                        agregar_al_carrito(str(prod_data['id']), prod_data['nombre'], "Normal", precio_n)
                        st.session_state.paso_wizard = 3
                        st.rerun()
                with c_btn2:
                    if precio_xl > 0 and st.button(f"➕ XL (${precio_xl})", type="primary", key=f"btn_xl_{prod_data['id']}", use_container_width=True):
                        agregar_al_carrito(str(prod_data['id']), prod_data['nombre'], "XL", precio_xl)
                        st.session_state.paso_wizard = 3
                        st.rerun()

    elif st.session_state.paso_wizard == 3:
        with st.container(border=True):
            st.subheader("🧾 Resumen de tu Pedido")
            for i, item in enumerate(st.session_state.carrito):
                c_txt, c_del = st.columns([5, 1])
                c_txt.markdown(f"✅ **{item['cantidad']}x** {item['nombre']} _({item['precio_texto']})_")
                if c_del.button("❌", key=f"del_{i}", help="Quitar este pan"):
                    st.session_state.carrito.pop(i)
                    if not st.session_state.carrito: st.session_state.paso_wizard = 2
                    st.rerun()
            st.divider()
            c_add, c_env = st.columns(2)
            if c_add.button("➕ Añadir otro pan", use_container_width=True):
                st.session_state.paso_wizard = 2
                st.rerun()
                
            if c_env.button("🚀 Enviar a Cocina", type="primary", use_container_width=True):
                for item in st.session_state.carrito:
                    db.agregar_pedido(st.session_state.nombre_cliente, item["id_prod"], item["tamano"], item["cantidad"], fecha_entrega)
                st.session_state.carrito = []
                st.session_state.paso_wizard = 1 
                st.session_state.nombre_cliente = ""
                st.success("¡Tu pedido fue agendado exitosamente! Ya puedes cerrar esta pantalla.")
                st.balloons()

# ==========================================
# VISTA ADMINISTRADOR
# ==========================================
def vista_admin():
    st.markdown("## Panel de Administración")
    estado_actual = db.get_estado_sistema()
    
    with st.container(border=True):
        col_txt, col_btn = st.columns([3, 1])
        if estado_actual == "Abierto":
            col_txt.success("🟢 **SISTEMA ABIERTO**")
            if col_btn.button("🔒 Cerrar", use_container_width=True):
                db.guardar_estado_sistema("Cerrado")
                st.rerun()
        else:
            col_txt.error("🔴 **SISTEMA CERRADO**")
            if col_btn.button("🔓 Abrir", type="primary", use_container_width=True):
                db.guardar_estado_sistema("Abierto")
                st.rerun()

    ahora = obtener_hora_chile()
    manana = ahora.date() + datetime.timedelta(days=1)
    fecha_filtro = st.date_input("🗓️ Filtrar fecha:", value=manana)
    
    # Renombrado de pestaña a "Logística y Pagos"
    tab_cocina, tab_pagos, tab_cancelar, tab_menu = st.tabs(["👨‍🍳 Producción", "📋 Logística y Pagos", "🗑️ Anular", "⚙️ Menú"])
    
    df_pedidos = db.get_pedidos(fecha_filtro)
    df_productos = db.get_productos()
    hay_datos = not df_pedidos.empty and not df_productos.empty
    
    if hay_datos:
        df_pedidos['producto_id'] = df_pedidos['producto_id'].astype(str)
        df_productos['id'] = df_productos['id'].astype(str)
        df_join = pd.merge(df_pedidos, df_productos, left_on='producto_id', right_on='id', how='left')
        df_join['Monto'] = df_join.apply(lambda row: parse_price(row['precio_normal']) * int(row['cantidad']) if str(row['tamano']).strip() == 'Normal' else parse_price(row['precio_xl']) * int(row['cantidad']), axis=1)

    # --- PRODUCCIÓN ---
    with tab_cocina:
        if not hay_datos: st.info("Sin pedidos.")
        else:
            c1, c2 = st.columns(2)
            df_resumen = df_join.groupby(['nombre', 'tamano'])['cantidad'].sum().reset_index()
            c1.dataframe(df_resumen.rename(columns={'nombre':'Producto', 'tamano':'Tam.', 'cantidad':'Cant.'}), hide_index=True)
            df_detalle = df_join[['cliente_nombre', 'cantidad', 'nombre', 'tamano']]
            c2.dataframe(df_detalle.rename(columns={'cliente_nombre':'Cliente', 'cantidad':'#'}), hide_index=True)

    # --- LOGÍSTICA Y PAGOS EXPRESS ---
    with tab_pagos:
        if not hay_datos:
            st.info("Sin pedidos registrados.")
        else:
            st.write("Gestiona retiros y pagos como en un Excel. Presiona **Sincronizar** para guardar los cambios.")
            
            # Aseguramos extraer la columna entregado y limpiar celdas vacías viejas
            df_edit = df_join[['id_x', 'cliente_nombre', 'cantidad', 'nombre', 'tamano', 'Monto', 'entregado', 'pagado']].copy()
            df_edit['entregado'] = df_edit['entregado'].astype(str).replace('', '0') == '1'
            df_edit['pagado'] = df_edit['pagado'].astype(str).replace('', '0') == '1'
            
            edited_df = st.data_editor(
                df_edit,
                column_config={
                    "id_x": None,
                    "cliente_nombre": st.column_config.TextColumn("Cliente", disabled=True),
                    "cantidad": st.column_config.NumberColumn("Cant.", disabled=True),
                    "nombre": st.column_config.TextColumn("Producto", disabled=True),
                    "tamano": st.column_config.TextColumn("Tam.", disabled=True),
                    "Monto": st.column_config.NumberColumn("Valor ($)", disabled=True),
                    "entregado": st.column_config.CheckboxColumn("¿Retiró?"),
                    "pagado": st.column_config.CheckboxColumn("¿Pagó?")
                },
                hide_index=True,
                use_container_width=True,
                key="editor_pagos"
            )
            
            if st.button("💾 Sincronizar Cambios en la Nube", type="primary", use_container_width=True):
                cambios_pagos = {}
                cambios_retiros = {}
                
                for idx, row in df_edit.iterrows():
                    # Detectar cambios en pagos
                    if row['pagado'] != edited_df.iloc[idx]['pagado']:
                        cambios_pagos[row['id_x']] = edited_df.iloc[idx]['pagado']
                    # Detectar cambios en retiros
                    if row['entregado'] != edited_df.iloc[idx]['entregado']:
                        cambios_retiros[row['id_x']] = edited_df.iloc[idx]['entregado']
                
                if cambios_pagos or cambios_retiros:
                    with st.spinner("Guardando en Google Sheets..."):
                        db.actualizar_estados_lote(cambios_pagos, cambios_retiros)
                    st.success(f"¡Sincronización exitosa!")
                    st.rerun()
                else:
                    st.info("No detecté ningún cambio.")

    # --- ANULAR ---
    with tab_cancelar:
        if hay_datos:
            opciones = {f"{r['cliente_nombre']} ({r['nombre']})": r['id_x'] for _, r in df_join.iterrows()}
            borrar = st.selectbox("Buscar pedido:", list(opciones.keys()))
            if st.button("🗑️ Anular"):
                db.anular_pedido(opciones[borrar])
                st.rerun()

    # --- MENÚ ---
    with tab_menu:
        if not df_productos.empty:
            st.dataframe(df_productos.drop(columns=['id']), hide_index=True, use_container_width=True)
            prod_eliminar = st.selectbox("Eliminar:", df_productos['nombre'].tolist())
            if st.button("Dar de baja"):
                id_eliminar = df_productos[df_productos['nombre'] == prod_eliminar]['id'].iloc[0]
                db.eliminar_producto(id_eliminar)
                st.rerun()

# ==========================================
# MOTOR PRINCIPAL
# ==========================================
inyectar_css()

with st.sidebar:
    st.write("### Acceso Interno")
    clave = st.text_input("Contraseña", type="password")
    
if clave == "gabo2026": 
    vista_admin()
else:
    vista_cliente()
