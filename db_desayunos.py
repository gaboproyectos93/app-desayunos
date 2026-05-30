import streamlit as st
from supabase import create_client, Client
import pandas as pd
import uuid

def conectar_supabase() -> Client:
    """Establece la conexión directa con el cliente de Supabase"""
    try:
        url: str = st.secrets["supabase"]["url"]
        key: str = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Error de conexión con Supabase: {e}")
        st.stop()

def get_productos():
    supabase = conectar_supabase()
    res = supabase.table("productos").select("*").execute()
    if not res.data:
        return pd.DataFrame(columns=["id", "nombre", "precio_normal", "precio_xl"])
    return pd.DataFrame(res.data)

def get_pedidos(fecha_str=None):
    supabase = conectar_supabase()
    query = supabase.table("pedidos").select("*")
    if fecha_str:
        query = query.eq("fecha_entrega", str(fecha_str))
    res = query.execute()
    if not res.data:
        return pd.DataFrame(columns=["id", "cliente_nombre", "producto_id", "tamano", "cantidad", "fecha_entrega", "pagado", "entregado"])
    return pd.DataFrame(res.data)

def agregar_pedido(cliente_nombre, producto_id, tamano, cantidad, fecha_entrega):
    supabase = conectar_supabase()
    nuevo_id = str(uuid.uuid4())[:8]
    supabase.table("pedidos").insert({
        "id": nuevo_id,
        "cliente_nombre": cliente_nombre,
        "producto_id": str(producto_id),
        "tamano": tamano,
        "cantidad": int(cantidad),
        "fecha_entrega": str(fecha_entrega),
        "pagado": False,
        "entregado": False
    }).execute()

def actualizar_estados_lote(cambios_pagos, cambios_retiros):
    """Actualiza filas de forma asíncrona en Supabase (toma milisegundos)"""
    supabase = conectar_supabase()
    for pid, valor in cambios_pagos.items():
        supabase.table("pedidos").update({"pagado": bool(valor)}).eq("id", pid).execute()
    for pid, valor in cambios_retiros.items():
        supabase.table("pedidos").update({"entregado": bool(valor)}).eq("id", pid).execute()

def anular_pedido(pedido_id):
    supabase = conectar_supabase()
    supabase.table("pedidos").delete().eq("id", pedido_id).execute()

def agregar_producto(nombre, p_normal, p_xl):
    supabase = conectar_supabase()
    nuevo_id = str(uuid.uuid4())[:8]
    supabase.table("productos").insert({
        "id": nuevo_id,
        "nombre": nombre,
        "precio_normal": p_normal if p_normal > 0 else None,
        "precio_xl": p_xl if p_xl > 0 else None
    }).execute()

def eliminar_producto(producto_id):
    supabase = conectar_supabase()
    historial = supabase.table("pedidos").select("id").eq("producto_id", producto_id).limit(1).execute()
    if historial.data:
        return False
    supabase.table("productos").delete().eq("id", producto_id).execute()
    return True

def get_estado_sistema():
    try:
        supabase = conectar_supabase()
        res = supabase.table("config").select("valor").eq("clave", "estado_pedidos").single().execute()
        return res.data["valor"]
    except:
        return "Abierto"

def guardar_estado_sistema(nuevo_estado):
    supabase = conectar_supabase()
    supabase.table("config").upsert({"clave": "estado_pedidos", "valor": nuevo_estado}).execute()
