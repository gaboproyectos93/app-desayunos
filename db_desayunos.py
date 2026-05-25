import streamlit as st
import gspread
import pandas as pd
import json
import uuid

def conectar_sheets():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        gc = gspread.service_account_from_dict(creds_dict)
        return gc.open("Base_Desayunos") 
    except Exception as e:
        st.error(f"Error conectando a Google Sheets. Detalle técnico: {e}")
        st.stop()

def get_productos():
    sh = conectar_sheets()
    ws = sh.worksheet("productos")
    data = ws.get_all_records()
    if not data:
        return pd.DataFrame(columns=["id", "nombre", "precio_normal", "precio_xl"])
    return pd.DataFrame(data)

def get_pedidos(fecha_str=None):
    sh = conectar_sheets()
    ws = sh.worksheet("pedidos")
    data = ws.get_all_records()
    
    # Agregamos 'entregado' a la estructura base
    if not data:
        return pd.DataFrame(columns=["id", "cliente_nombre", "producto_id", "tamano", "cantidad", "fecha_entrega", "pagado", "entregado"])
    
    df = pd.DataFrame(data)
    # Por si hay pedidos antiguos que no tenían esta columna
    if 'entregado' not in df.columns:
        df['entregado'] = 0
        
    if fecha_str:
        df = df[df["fecha_entrega"] == str(fecha_str)]
    return df

def agregar_pedido(cliente_nombre, producto_id, tamano, cantidad, fecha_entrega):
    sh = conectar_sheets()
    ws = sh.worksheet("pedidos")
    nuevo_id = str(uuid.uuid4())[:8]
    # Agregamos un segundo 0 al final para el estado de 'entregado'
    ws.append_row([nuevo_id, cliente_nombre, str(producto_id), tamano, cantidad, str(fecha_entrega), 0, 0])

def actualizar_estados_lote(cambios_pagos, cambios_retiros):
    """Actualiza la columna 7 (pagado) y la columna 8 (entregado) de golpe"""
    if not cambios_pagos and not cambios_retiros: return
    sh = conectar_sheets()
    ws = sh.worksheet("pedidos")
    records = ws.get_all_records()
    
    celdas_a_actualizar = []
    for i, row in enumerate(records):
        pid = str(row['id'])
        if pid in cambios_pagos:
            celdas_a_actualizar.append(gspread.Cell(row=i+2, col=7, value=int(cambios_pagos[pid])))
        if pid in cambios_retiros:
            celdas_a_actualizar.append(gspread.Cell(row=i+2, col=8, value=int(cambios_retiros[pid])))
            
    if celdas_a_actualizar:
        ws.update_cells(celdas_a_actualizar)

def anular_pedido(pedido_id):
    sh = conectar_sheets()
    ws = sh.worksheet("pedidos")
    cell = ws.find(str(pedido_id), in_column=1)
    if cell:
        ws.delete_rows(cell.row)

def agregar_producto(nombre, p_normal, p_xl):
    sh = conectar_sheets()
    ws = sh.worksheet("productos")
    nuevo_id = str(uuid.uuid4())[:8]
    ws.append_row([nuevo_id, nombre, p_normal if p_normal > 0 else "", p_xl if p_xl > 0 else ""])

def eliminar_producto(producto_id):
    sh = conectar_sheets()
    ws_prod = sh.worksheet("productos")
    ws_ped = sh.worksheet("pedidos")
    registros_pedidos = ws_ped.get_all_records()
    tiene_historial = any(str(r.get('producto_id')) == str(producto_id) for r in registros_pedidos)
    if tiene_historial:
        return False
    else:
        cell = ws_prod.find(str(producto_id), in_column=1)
        if cell:
            ws_prod.delete_rows(cell.row)
        return True

def get_estado_sistema():
    try:
        sh = conectar_sheets()
        ws = sh.worksheet("config")
        return ws.cell(2, 2).value 
    except:
        try:
            sh = conectar_sheets()
            ws = sh.add_worksheet(title="config", rows="10", cols="2")
            ws.append_row(["clave", "valor"])
            ws.append_row(["estado_pedidos", "Abierto"])
            return "Abierto"
        except:
            return "Abierto"

def guardar_estado_sistema(nuevo_estado):
    sh = conectar_sheets()
    ws = sh.worksheet("config")
    ws.update_cell(2, 2, nuevo_estado)
