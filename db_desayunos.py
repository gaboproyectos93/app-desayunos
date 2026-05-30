import streamlit as st
from supabase import create_client, Client
import pandas as pd
import uuid
import calendar

def conectar_supabase() -> Client:
    try:
        url: str = st.secrets["supabase"]["url"]
        key: str = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Error de conexión con Supabase: {e}")
        st.stop()

# --- NUEVAS FUNCIONES DE CONFIGURACIÓN UNIVERSAL ---
def get_config(clave, default=""):
    """Busca un ajuste en la base de datos. Si no existe, lo crea con el valor por defecto."""
    try:
        supabase = conectar_supabase()
        res = supabase.table("config").select("valor").eq("clave", clave).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]["valor"]
        else:
            supabase.table("config").upsert({"clave": clave, "valor": str(default)}).execute()
            return str(default)
    except:
        return str(default)

def set_config(clave, valor):
    """Guarda o actualiza un ajuste en la base de datos."""
    supabase = conectar_supabase()
    supabase.table("config").upsert({"clave": clave, "valor": str(valor)}).execute()

def get_productos():
    supabase = conectar_supabase()
    res = supabase.table("productos").select("*").execute()
    if not res.data: return pd.DataFrame(columns=["id", "nombre", "precio_normal", "precio_xl"])
    return pd.DataFrame(res.data)

def get_pedidos(fecha_str=None):
    supabase = conectar_supabase()
    query = supabase.table("pedidos").select("*")
    if fecha_str: query = query.eq("fecha_entrega", str(fecha_str))
    res = query.execute()
    if not res.data: return pd.DataFrame(columns=["id", "cliente_nombre", "producto_id", "tamano", "cantidad", "fecha_entrega", "pagado", "entregado"])
    return pd.DataFrame(res.data)

def get_pedidos_mes(anio, mes):
    supabase = conectar_supabase()
    _, ultimo_dia = calendar.monthrange(anio, mes)
    fecha_inicio = f"{anio}-{mes:02d}-01"
    fecha_fin = f"{anio}-{mes:02d}-{ultimo_dia}"
    res = supabase.table("pedidos").select("*").gte("fecha_entrega", fecha_inicio).lte("fecha_entrega", fecha_fin).execute()
    if not res.data: return pd.DataFrame(columns=["id", "cliente_nombre", "producto_id", "tamano", "cantidad", "fecha_entrega", "pagado", "entregado"])
    return pd.DataFrame(res.data)

def agregar_pedido(cliente_nombre, producto_id, tamano, cantidad, fecha_entrega):
    supabase = conectar_supabase()
    nuevo_id = str(uuid.uuid4())[:8]
    supabase.table("pedidos").insert({
        "id": nuevo_id, "cliente_nombre": cliente_nombre, "producto_id": str(producto_id),
        "tamano": tamano, "cantidad": int(cantidad), "fecha_entrega": str(fecha_entrega),
        "pagado": False, "entregado": False
    }).execute()

def actualizar_estados_lote(cambios_pagos, cambios_retiros):
    supabase = conectar_supabase()
    for pid, valor in cambios_pagos.items(): supabase.table("pedidos").update({"pagado": bool(valor)}).eq("id", pid).execute()
    for pid, valor in cambios_retiros.items(): supabase.table("pedidos").update({"entregado": bool(valor)}).eq("id", pid).execute()

def anular_pedido(pedido_id):
    supabase = conectar_supabase()
    supabase.table("pedidos").delete().eq("id", pedido_id).execute()

def agregar_producto(nombre, p_normal, p_xl):
    supabase = conectar_supabase()
    nuevo_id = str(uuid.uuid4())[:8]
    supabase.table("productos").insert({"id": nuevo_id, "nombre": nombre, "precio_normal": p_normal if p_normal > 0 else None, "precio_xl": p_xl if p_xl > 0 else None}).execute()

def eliminar_producto(producto_id):
    supabase = conectar_supabase()
    historial = supabase.table("pedidos").select("id").eq("producto_id", producto_id).limit(1).execute()
    if historial.data: return False
    supabase.table("productos").delete().eq("id", producto_id).execute()
    return True
