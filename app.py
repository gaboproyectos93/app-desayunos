import streamlit as st
import pandas as pd
import datetime
from zoneinfo import ZoneInfo
import db_desayunos as db 

st.set_page_config(page_title="Desayunos Caseros", page_icon="🥪", layout="centered")

def obtener_hora_chile():
    try: return datetime.datetime.now(ZoneInfo("America/Santiago"))
    except: return datetime.datetime.utcnow() - datetime.timedelta(hours=4)

def inyectar_css():
    estilo = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&family=Oswald:wght@500&display=swap');
    .titulo-nuestro {{ font-family: 'Dancing Script', cursive; font-size: 4.5rem; text-align: center; margin-bottom: -30px; }}
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

def agregar_al_carrito(id_prod, nombre, tamano, precio_num, cantidad):
    for item in st.session_state.carrito:
        if item["id_prod"] == id_prod and item["tamano"] == tamano:
            item["cantidad"] += cantidad
            return
    st.session_state.carrito.append({
        "id_prod": id_prod, "nombre": nombre, "tamano": tamano, 
        "cantidad": cantidad, "precio_texto": f"{tamano} (${precio_num})"
    })

def obtener_ranking_limpio(mes, anio):
    """Calcula el ranking mensual y aplica desempate por cantidad de productos"""
    df_ped_mes = db.get_pedidos_mes(anio, mes)
    df_productos = db.get_productos()
    
    if df_ped_mes.empty or df_productos.empty:
        return pd.DataFrame()
        
    df_ped_mes['producto_id'] = df_ped_mes['producto_id'].astype(str)
    df_productos['id'] = df_productos['id'].astype(str)
    df_join = pd.merge(df_ped_mes, df_productos, left_on='producto_id', right_on='id', how='left')
    df_join['Monto'] = df_join.apply(lambda row: parse_price(row['precio_normal']) * int(row['cantidad']) if str(row['tamano']).strip() == 'Normal' else parse_price(row['precio_xl']) * int(row['cantidad']), axis=1)

    # Excluir a Gabo
    df_join = df_join[~df_join['cliente_nombre'].str.strip().str.lower().isin(['gabo'])]

    # Sumar Monto y Cantidad por cliente
    ranking = df_join.groupby('cliente_nombre').agg({'Monto': 'sum', 'cantidad': 'sum'}).reset_index()
    # ORDENAR: 1° Por Dinero (Descendente), 2° Por Cantidad (Descendente) en caso de empate
    return ranking.sort_values(by=['Monto', 'cantidad'], ascending=[False, False]).reset_index(drop=True)

# ==========================================
# VISTA CLIENTE
# ==========================================
def vista_cliente():
    st.markdown("<div class='titulo-nuestro'>Desayunos</div>", unsafe_allow_html=True)
    st.markdown("<div class='titulo-menu'>CASEROS</div>", unsafe_allow_html=True)
    
    ahora = obtener_hora_chile()
    
    # 1. VERIFICAR CIERRE MANUAL DE EMERGENCIA
    estado_manual = db.get_config("estado_pedidos", "Abierto")
    if estado_manual == "Cerrado":
        st.error("🔒 **La cocina está cerrada.** (Cierre temporal administrativo).")
        return

    # 2. VERIFICAR HORARIO AUTOMÁTICO
    dias_str = db.get_config("dias_abierto", "0,1,2,3,4")
    dias_permitidos = [int(x) for x in dias_str.split(",")] if dias_str else []
    hora_i = db.get_config("hora_inicio", "08:00")
    hora_f = db.get_config("hora_fin", "20:00")
    hora_actual = ahora.strftime("%H:%M")
    
    if ahora.weekday() not in dias_permitidos or not (hora_i <= hora_actual <= hora_f):
        st.error(f"⏳ **Fuera de horario.** Atendemos dentro del horario configurado ({hora_i} a {hora_f}).")
        return

    fecha_entrega = (ahora + datetime.timedelta(days=1)).date() if ahora.hour < 20 else (ahora + datetime.timedelta(days=2)).date()
    st.info(f"📅 Recibiendo pedidos para el: **{fecha_entrega.strftime('%d-%m-%Y')}**")

    # --- PASO 1: IDENTIFICACIÓN Y PODIO TOP 5 ---
    if st.session_state.paso_wizard == 1:
        
        mostrar_ranking = db.get_config("mostrar_ranking", "Si")
        if mostrar_ranking == "Si":
            with st.container(border=True):
                st.subheader("🏆 Rey del Desayuno")
                st.markdown("🎁 **¡El #1 del mes se lleva un pedido GRATIS (tope $2.500)!**")
                st.caption("*(En caso de empate, gana quien haya comprado mayor cantidad de producto en el mes)*")
                
                ranking_df = obtener_ranking_limpio(ahora.month, ahora.year)
                
                if not ranking_df.empty:
                    top_5 = ranking_df.head(5)
                    for i, row in top_5.iterrows():
                        pos = i + 1
                        # Se ha ocultado el recuento de panes en la vista pública
                        if pos == 1: st.success(f"🥇 **1° {row['cliente_nombre'].title()}**")
                        elif pos == 2: st.warning(f"🥈 **2° {row['cliente_nombre'].title()}**")
                        elif pos == 3: st.info(f"🥉 **3° {row['cliente_nombre'].title()}**")
                        else: st.markdown(f"🏅 **{pos}° {row['cliente_nombre'].title()}**")
                else:
                    st.write("Aún no hay pedidos este mes. ¡Anímate a ser el primero!")
            st.write("") 

        with st.container(border=True):
            st.subheader("👋 ¡Hola! ¿Para quién es el pedido?")
            nombre = st.text_input("Ingresa tu Nombre y Apellido", value=st.session_state.nombre_cliente)
            if st.button("Continuar al Menú ➔", type="primary", use_container_width=True):
                if not nombre.strip(): st.error("Por favor, dinos tu nombre.")
                else:
                    st.session_state.nombre_cliente = nombre.strip()
                    st.session_state.paso_wizard = 2
                    st.rerun()

    # --- PASO 2: MENÚ COLECTIVO ---
    elif st.session_state.paso_wizard == 2:
        df_productos = db.get_productos()
        col_izq, col_der = st.columns([2, 1])
        col_izq.subheader(f"🛒 Menú para {st.session_state.nombre_cliente.split()[0]}")
        
        if st.session_state.carrito:
            total_items = sum(i['cantidad'] for i in st.session_state.carrito)
            if col_der.button(f"🧾 Revisar ({total_items}) ➔", type="primary", use_container_width=True):
                st.session_state.paso_wizard = 3
                st.rerun()
        else:
            if col_der.button("➔ Volver", use_container_width=True):
                st.session_state.paso_wizard = 1
                st.rerun()

        for index, prod_data in df_productos.iterrows():
            precio_n = parse_price(prod_data['precio_normal'])
            precio_xl = parse_price(prod_data['precio_xl'])
            
            with st.container(border=True):
                col_tit, col_qty = st.columns([3, 1])
                col_tit.markdown(f"#### 🥪 {prod_data['nombre']}")
                cantidad = col_qty.number_input("Cant.", min_value=1, max_value=20, value=1, key=f"qty_{prod_data['id']}", step=1)
                
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if precio_n > 0 and st.button(f"Añadir Normal (${precio_n})", key=f"btn_n_{prod_data['id']}", use_container_width=True):
                        agregar_al_carrito(str(prod_data['id']), prod_data['nombre'], "Normal", precio_n, cantidad)
                        st.toast(f"Añadido: {cantidad}x {prod_data['nombre']}", icon="🛒")
                        st.rerun()
                with c_btn2:
                    if precio_xl > 0 and st.button(f"Añadir XL (${precio_xl})", type="primary", key=f"btn_xl_{prod_data['id']}", use_container_width=True):
                        agregar_al_carrito(str(prod_data['id']), prod_data['nombre'], "XL", precio_xl, cantidad)
                        st.toast(f"Añadido: {cantidad}x {prod_data['nombre']}", icon="🛒")
                        st.rerun()

    # --- PASO 3: CONFIRMACIÓN Y CIERRE ---
    elif st.session_state.paso_wizard == 3:
        with st.container(border=True):
            st.subheader("🧾 Resumen de tu Pedido")
            for i, item in enumerate(st.session_state.carrito):
                c_txt, c_del = st.columns([5, 1])
                c_txt.markdown(f"✅ **{item['cantidad']}x** {item['nombre']} _({item['precio_texto']})_")
                if c_del.button("❌", key=f"del_{i}"):
                    st.session_state.carrito.pop(i)
                    if not st.session_state.carrito: st.session_state.paso_wizard = 2
                    st.rerun()
            st.divider()
            c_add, c_env = st.columns(2)
            if c_add.button("➕ Agregar más variedad", use_container_width=True):
                st.session_state.paso_wizard = 2
                st.rerun()
                
            if c_env.button("🚀 Confirmar y Enviar", type="primary", use_container_width=True):
                for item in st.session_state.carrito:
                    db.agregar_pedido(st.session_state.nombre_cliente, item["id_prod"], item["tamano"], item["cantidad"], fecha_entrega)
                st.session_state.carrito = []
                st.session_state.paso_wizard = 1 
                st.session_state.nombre_cliente = ""
                st.success("¡Pedido enviado con éxito!")
                st.balloons()

# ==========================================
# VISTA ADMINISTRADOR
# ==========================================
def vista_admin():
    st.markdown("## Panel de Administración")
    
    estado_actual = db.get_config("estado_pedidos", "Abierto")
    with st.container(border=True):
        col_txt, col_btn = st.columns([3, 1])
        if estado_actual == "Abierto":
            col_txt.success("🟢 **BOTÓN DE PÁNICO APAGADO:** El sistema está respetando el horario automático.")
            if col_btn.button("🔒 Forzar Cierre General", use_container_width=True):
                db.set_config("estado_pedidos", "Cerrado")
                st.rerun()
        else:
            col_txt.error("🔴 **BOTÓN DE PÁNICO ACTIVADO:** La tienda está cerrada para los clientes.")
            if col_btn.button("🔓 Quitar Bloqueo", type="primary", use_container_width=True):
                db.set_config("estado_pedidos", "Abierto")
                st.rerun()

    ahora = obtener_hora_chile()
    manana = ahora.date() + datetime.timedelta(days=1)
    
    tab_cocina, tab_pagos, tab_ranking, tab_cancelar, tab_ajustes = st.tabs(["👨‍🍳 Producción", "📋 Pagos", "🏆 Ranking Admin", "🗑️ Anular", "⚙️ Ajustes"])
    df_productos = db.get_productos()

    with tab_cocina:
        fecha_filtro_prod = st.date_input("🗓️ Fecha de producción:", value=manana, key="d1")
        df_pedidos_diario = db.get_pedidos(fecha_filtro_prod)
        if not df_pedidos_diario.empty and not df_productos.empty:
            df_pedidos_diario['producto_id'] = df_pedidos_diario['producto_id'].astype(str)
            df_join_d = pd.merge(df_pedidos_diario, df_productos, left_on='producto_id', right_on='id', how='left')
            c1, c2 = st.columns(2)
            df_resumen = df_join_d.groupby(['nombre', 'tamano'])['cantidad'].sum().reset_index()
            c1.dataframe(df_resumen.rename(columns={'nombre':'Producto', 'tamano':'Tam.', 'cantidad':'Cant.'}), hide_index=True)
            df_detalle = df_join_d[['cliente_nombre', 'cantidad', 'nombre', 'tamano']]
            c2.dataframe(df_detalle.rename(columns={'cliente_nombre':'Cliente', 'cantidad':'#'}), hide_index=True)
        else:
            st.info("Sin pedidos para esta fecha.")

    with tab_pagos:
        fecha_filtro_pagos = st.date_input("🗓️ Fecha de logística:", value=manana, key="d2")
        df_pedidos_pagos = db.get_pedidos(fecha_filtro_pagos)
        if not df_pedidos_pagos.empty and not df_productos.empty:
            df_pedidos_pagos['producto_id'] = df_pedidos_pagos['producto_id'].astype(str)
            df_join_p = pd.merge(df_pedidos_pagos, df_productos, left_on='producto_id', right_on='id', how='left')
            df_join_p['Monto'] = df_join_p.apply(lambda row: parse_price(row['precio_normal']) * int(row['cantidad']) if str(row['tamano']).strip() == 'Normal' else parse_price(row['precio_xl']) * int(row['cantidad']), axis=1)
            
            df_edit = df_join_p[['id_x', 'cliente_nombre', 'cantidad', 'nombre', 'tamano', 'Monto', 'entregado', 'pagado']].copy()
            df_edit['entregado'] = df_edit['entregado'] == True
            df_edit['pagado'] = df_edit['pagado'] == True
            
            edited_df = st.data_editor(
                df_edit,
                column_config={"id_x": None, "cliente_nombre": st.column_config.TextColumn("Cliente", disabled=True), "cantidad": st.column_config.NumberColumn("Cant.", disabled=True), "nombre": st.column_config.TextColumn("Producto", disabled=True), "tamano": st.column_config.TextColumn("Tam.", disabled=True), "Monto": st.column_config.NumberColumn("Valor ($)", disabled=True), "entregado": st.column_config.CheckboxColumn("¿Retiró?"), "pagado": st.column_config.CheckboxColumn("¿Pagó?")},
                hide_index=True, use_container_width=True, key="editor_pagos"
            )
            
            if st.button("💾 Sincronizar Cambios", type="primary", use_container_width=True):
                cambios_pagos = {}
                cambios_retiros = {}
                for idx, row in df_edit.iterrows():
                    if row['pagado'] != edited_df.iloc[idx]['pagado']: cambios_pagos[row['id_x']] = edited_df.iloc[idx]['pagado']
                    if row['entregado'] != edited_df.iloc[idx]['entregado']: cambios_retiros[row['id_x']] = edited_df.iloc[idx]['entregado']
                if cambios_pagos or cambios_retiros:
                    db.actualizar_estados_lote(cambios_pagos, cambios_retiros)
                    st.rerun()
        else:
            st.info("Sin pedidos registrados.")

    with tab_ranking:
        st.subheader("👑 Tabla General Mensual (Privado)")
        c_mes, c_anio = st.columns(2)
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes_seleccionado = c_mes.selectbox("Mes:", range(len(meses)), index=ahora.month-1, format_func=lambda x: meses[x])
        anio_seleccionado = c_anio.number_input("Año:", value=ahora.year, step=1)
        
        ranking = obtener_ranking_limpio(mes_seleccionado + 1, anio_seleccionado)
        
        if ranking.empty:
            st.info("Aún no hay compras registradas en este mes.")
        else:
            ranking.index = ranking.index + 1 
            ganador = ranking.iloc[0]
            st.success(f"🏆 **{ganador['cliente_nombre'].upper()}** va liderando con **${ganador['Monto']:,.0f}** ({ganador['cantidad']} productos)!")
            
            ranking.rename(columns={'cliente_nombre': 'Cliente', 'Monto': 'Dinero Gastado ($)', 'cantidad': 'Cant. Productos'}, inplace=True)
            st.dataframe(ranking, column_config={"Dinero Gastado ($)": st.column_config.NumberColumn(format="$%d")}, use_container_width=True)

    with tab_cancelar:
        fecha_filtro_canc = st.date_input("🗓️ Fecha a buscar:", value=manana, key="d3")
        df_ped_canc = db.get_pedidos(fecha_filtro_canc)
        if not df_ped_canc.empty and not df_productos.empty:
            df_ped_canc['producto_id'] = df_ped_canc['producto_id'].astype(str)
            df_join_c = pd.merge(df_ped_canc, df_productos, left_on='producto_id', right_on='id', how='left')
            opciones = {f"{r['cliente_nombre']} ({r['cantidad']}x {r['nombre']})": r['id_x'] for _, r in df_join_c.iterrows()}
            borrar = st.selectbox("Buscar pedido:", list(opciones.keys()))
            if st.button("🗑️ Anular"):
                db.anular_pedido(opciones[borrar])
                st.rerun()

    with tab_ajustes:
        st.subheader("🗓️ Horario Automático de Pedidos")
        st.write("Selecciona en qué horario los clientes pueden pedir desde sus celulares:")
        c_dias, c_horas = st.columns([2, 1])
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        
        dias_guardados = db.get_config("dias_abierto", "0,1,2,3,4")
        dias_indices = [int(x) for x in dias_guardados.split(",")] if dias_guardados else []
        dias_default = [dias_semana[i] for i in dias_indices if i < 7]
        dias_seleccionados = c_dias.multiselect("Días habilitados:", dias_semana, default=dias_default)
        
        hora_i = db.get_config("hora_inicio", "08:00")
        hora_f = db.get_config("hora_fin", "20:00")
        
        c_h1, c_h2 = c_horas.columns(2)
        nueva_h_i = c_h1.time_input("Apertura:", value=datetime.datetime.strptime(hora_i, "%H:%M").time())
        nueva_h_f = c_h2.time_input("Cierre:", value=datetime.datetime.strptime(hora_f, "%H:%M").time())
        
        st.divider()
        st.subheader("🏆 Configuración del Ranking")
        mostrar_r = db.get_config("mostrar_ranking", "Si")
        nuevo_mostrar = st.radio("¿Mostrar el Podio Top 5 a los clientes?", ["Si", "No"], index=0 if mostrar_r == "Si" else 1, horizontal=True)
        
        if st.button("💾 Guardar Ajustes Generales", type="primary"):
            indices_str = ",".join([str(dias_semana.index(d)) for d in dias_seleccionados])
            db.set_config("dias_abierto", indices_str)
            db.set_config("hora_inicio", nueva_h_i.strftime("%H:%M"))
            db.set_config("hora_fin", nueva_h_f.strftime("%H:%M"))
            db.set_config("mostrar_ranking", nuevo_mostrar)
            st.success("Ajustes guardados correctamente.")
            st.rerun()
            
        st.divider()
        st.subheader("🍔 Gestión del Menú")
        if not df_productos.empty:
            st.dataframe(df_productos.drop(columns=['id']), hide_index=True, use_container_width=True)
        
        col_add, col_del = st.columns(2)
        with col_add:
            nuevo_nombre = st.text_input("Agregar Nombre Pan")
            c1, c2 = st.columns(2)
            with c1: nuevo_normal = st.number_input("Precio Normal ($)", min_value=0, step=100)
            with c2: nuevo_xl = st.number_input("Precio XL ($)", min_value=0, step=100)
            if st.button("Guardar Producto", type="primary"):
                if nuevo_nombre.strip():
                    db.agregar_producto(nuevo_nombre.strip(), nuevo_normal, nuevo_xl)
                    st.rerun()
        with col_del:
            if not df_productos.empty:
                prod_eliminar = st.selectbox("Eliminar Producto:", df_productos['nombre'].tolist())
                if st.button("Dar de baja"):
                    id_eliminar = df_productos[df_productos['nombre'] == prod_eliminar]['id'].iloc[0]
                    db.eliminar_producto(id_eliminar)
                    st.rerun()

# ==========================================
# EXECUTION
# ==========================================
inyectar_css()

with st.sidebar:
    st.write("### Acceso Interno")
    clave = st.text_input("Contraseña", type="password")
    
if clave == "gabo2026": 
    vista_admin()
else:
    vista_cliente()
