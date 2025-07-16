import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageTk
import requests
from io import BytesIO
import webbrowser
import threading

import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

db = firestore.client()

# --- FUNCIONES DEL FLUJO DE PAGO ---

def abrir_pantalla_pago(root, obras_a_pagar):
    """Abre la ventana que muestra el resumen y el total a pagar."""
    if not obras_a_pagar:
        messagebox.showinfo("Nada que pagar", "Actualmente no eres el ganador en ninguna subasta.")
        return

    ventana_pago = tk.Toplevel(root)
    ventana_pago.title("Resumen de Pago")
    ventana_pago.geometry("500x500")
    ventana_pago.configure(bg="#d0e7f9")
    fuente_titulo = ("Arial", 16, "bold")
    fuente_normal = ("Arial", 13)

    total = sum(obra['ofertas']['historial_ofertas'][-1]['monto'] for obra in obras_a_pagar)

    tk.Label(ventana_pago, text="Resumen de Obras Ganadas", font=fuente_titulo, bg="#d0e7f9").pack(pady=10)

    for obra in obras_a_pagar:
        monto = obra['ofertas']['historial_ofertas'][-1]['monto']
        tk.Label(ventana_pago, text=f"- {obra['nombre']}: ${monto:,}", font=fuente_normal, bg="#d0e7f9").pack(anchor="w", padx=20)
    
    ttk.Separator(ventana_pago, orient='horizontal').pack(fill='x', pady=10, padx=20)
    tk.Label(ventana_pago, text=f"Total a Pagar: ${total:,}", font=fuente_titulo, bg="#d0e7f9").pack(pady=10)

    tk.Label(ventana_pago, text="Selecciona medio de pago:", font=fuente_normal, bg="#d0e7f9").pack(pady=10)
    medio_var = tk.StringVar()
    medios = ["Tarjeta de crédito", "Tarjeta débito (PSE)"]
    combo_medios = ttk.Combobox(ventana_pago, textvariable=medio_var, values=medios, font=fuente_normal, state="readonly", width=25)
    combo_medios.pack(pady=5)
    combo_medios.set(medios[0])

    def siguiente():
        ventana_pago.destroy()
        abrir_bancos(root)

    tk.Button(ventana_pago, text="Siguiente", font=fuente_normal, bg="#99ccff", command=siguiente).pack(pady=20)


def abrir_bancos(root):
    """Abre la ventana para seleccionar el banco y redirigir."""
    ventana_banco = tk.Toplevel(root)
    ventana_banco.title("Selecciona tu banco")
    ventana_banco.geometry("400x300")
    ventana_banco.configure(bg="#d0e7f9")
    fuente_normal = ("Arial", 13)

    bancos = {
        "Bancolombia": "https://www.bancolombia.com/personas",
        "Davivienda": "https://www.davivienda.com",
        "Banco de Bogotá": "https://www.bancodebogota.com",
        "BBVA": "https://www.bbva.com.co",
        "Nequi": "https://www.nequi.com.co"
    }

    tk.Label(ventana_banco, text="Selecciona tu banco:", font=fuente_normal, bg="#d0e7f9").pack(pady=20)
    banco_var = tk.StringVar()
    combo_bancos = ttk.Combobox(ventana_banco, textvariable=banco_var, values=list(bancos.keys()), font=fuente_normal, state="readonly", width=25)
    combo_bancos.pack(pady=10)
    combo_bancos.set(list(bancos.keys())[0])

    def pagar():
        banco_seleccionado = banco_var.get()
        if not banco_seleccionado:
            messagebox.showwarning("Atención", "Por favor, selecciona un banco.", parent=ventana_banco)
            return
            
        url_banco = bancos[banco_seleccionado]
        messagebox.showinfo("Redirigiendo", f"Serás redirigido a la página de {banco_seleccionado} para completar tu pago.", parent=ventana_banco)
        webbrowser.open(url_banco, new=2)
        ventana_banco.destroy()

    tk.Button(ventana_banco, text="Pagar", font=fuente_normal, bg="#a2f5a2", command=pagar).pack(pady=20)

# --- OTRAS FUNCIONES AUXILIARES ---

def cargar_imagen_async(url, label_imagen, tamano=(250, 250)):
    """Descarga una imagen en un hilo separado para no bloquear la UI."""
    def _trabajo_de_hilo():
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            img_data = BytesIO(response.content)
            img = Image.open(img_data)
            img.thumbnail(tamano, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            label_imagen.config(image=photo, text="", width=0, height=0)
            label_imagen.image = photo
        except Exception as e:
            print(f"Error al descargar imagen (hilo): {e}")
            label_imagen.config(text="Img Error")
    threading.Thread(target=_trabajo_de_hilo, daemon=True).start()

def abrir_galeria_de_imagenes(nombre_obra, image_urls):
    """Abre una ventana para mostrar todas las imágenes de una obra."""
    ventana_galeria = tk.Toplevel()
    ventana_galeria.title(f"Imágenes de: {nombre_obra}")
    ventana_galeria.geometry("800x600")
    ventana_galeria.configure(bg="#e9f5ff")

    canvas = tk.Canvas(ventana_galeria, bg="#e9f5ff")
    scrollbar = tk.Scrollbar(ventana_galeria, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg="#e9f5ff")
    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    if not image_urls:
        tk.Label(scroll_frame, text="No hay imágenes adicionales para esta obra.", font=("Arial", 14), bg="#e9f5ff").pack(padx=10, pady=10)
    else:
        for url in image_urls:
            placeholder = tk.Label(scroll_frame, text="Cargando...", font=("Arial", 12), bg="#e0e0e0", width=50, height=20)
            placeholder.pack(padx=10, pady=10)
            cargar_imagen_async(url, placeholder, (700, 500))

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")


def abrir_ventana_historial_usuario(historial, nombre_obra):
    """Abre una ventana para mostrar el historial de ofertas de una obra."""
    ventana_historial = tk.Toplevel()
    ventana_historial.title(f"Historial de Ofertas - {nombre_obra}")
    ventana_historial.geometry("500x400")
    ventana_historial.configure(bg="#e9f5ff")
    
    fuente_titulo = ("Arial", 16, "bold")
    fuente_item = ("Arial", 13)

    tk.Label(ventana_historial, text=f"Historial para: {nombre_obra}", font=fuente_titulo, bg="#e9f5ff").pack(pady=10)

    canvas = tk.Canvas(ventana_historial, bg="#e9f5ff", highlightthickness=0)
    scrollbar = tk.Scrollbar(ventana_historial, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg="#e9f5ff")
    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    if not historial:
        tk.Label(scroll_frame, text="No se han realizado ofertas para esta obra.", font=fuente_item, bg="#e9f5ff").pack(padx=10, pady=10)
    else:
        for i, oferta in enumerate(reversed(historial)):
            monto_formateado = f"${oferta.get('monto', 0):,}"
            texto_oferta = f"{i+1}. {oferta.get('nombre', 'N/A')} ofreció: {monto_formateado}"
            tk.Label(scroll_frame, text=texto_oferta, font=fuente_item, bg="#e9f5ff").pack(anchor="w", padx=10, pady=2)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")


def crear_funcion_ofertar(id_obra, entrada, datos_usuario, callback_refrescar, precio_actual):
    """Crea una función de oferta específica para una obra, validando el monto."""
    def funcion_real():
        monto_str = entrada.get()
        if not monto_str.isdigit() or int(monto_str) <= 0:
            messagebox.showerror("Error", "Ingresa un monto numérico válido y positivo.")
            return
        
        monto_int = int(monto_str)
        
        if monto_int <= precio_actual:
            messagebox.showerror("Oferta Baja", f"Tu oferta debe ser mayor al precio actual de ${precio_actual:,}.")
            return
        
        nueva_oferta = {
            "nombre": datos_usuario.get('nombre'),
            "monto": monto_int,
            "timestamp": datetime.now()
        }
        
        try:
            obra_ref = db.collection('obras_subasta').document(id_obra)
            obra_ref.update({'historial_ofertas': firestore.ArrayUnion([nueva_oferta])})
            messagebox.showinfo("¡Oferta realizada!", "Tu oferta ha sido registrada.")
            entrada.delete(0, tk.END)
            callback_refrescar()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo registrar la oferta: {e}")
            
    return funcion_real


def crear_widget_obra(parent, obra_id, obra_data, estado_subasta, datos_usuario, callback_refrescar):
    """Crea y configura el widget para una sola obra."""
    contenedor = tk.Frame(parent, bd=2, relief="groove", bg="#e9f5ff", padx=20, pady=20)
    contenedor.pack(pady=10, padx=10, fill="x")
    contenedor.columnconfigure(1, weight=1)

    label_img = tk.Label(contenedor, text="Cargando...", width=30, height=15, bg="#e0e0e0")
    label_img.grid(row=0, column=0, rowspan=3, padx=20)

    image_urls = obra_data.get('image_urls', [])
    if image_urls:
        cargar_imagen_async(image_urls[0], label_img, (250, 250))
    
    if len(image_urls) > 1:
        tk.Button(contenedor, text=f"Ver más imágenes ({len(image_urls)})", font=("Arial", 11),
                  command=lambda nom=obra_data.get('nombre'), urls=image_urls: abrir_galeria_de_imagenes(nom, urls)).grid(row=3, column=0, pady=5)
    
    info_frame = tk.Frame(contenedor, bg="#e9f5ff")
    info_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=10)
    
    fuente_titulo = ("Arial", 20, "bold")
    fuente_normal = ("Arial", 14)
    
    tk.Label(info_frame, text=f"{obra_data.get('nombre', 'Desconocido')}", font=fuente_titulo, bg="#e9f5ff", justify="left").pack(anchor="w")
    tk.Label(info_frame, text=f"por {obra_data.get('autor', 'Desconocido')} ({obra_data.get('fecha', 'N/A')})", font=("Arial", 14, "italic"), bg="#e9f5ff", justify="left").pack(anchor="w")
    tk.Label(info_frame, text=f"{obra_data.get('descripcion', '')}", font=("Arial", 13), bg="#e9f5ff", wraplength=600, justify="left").pack(anchor="w", pady=15)

    historial = obra_data.get("historial_ofertas", [])
    precio_actual = obra_data.get('ofertas', {}).get('precio_base', 0)
    if historial:
        precio_actual = historial[-1]['monto']

    tk.Label(info_frame, text="Precio Actual:", font=("Arial", 13, "bold"), bg="#e9f5ff").pack(anchor="w", pady=(10,0))
    tk.Label(info_frame, text=f"${precio_actual:,}", font=("Arial", 18, "bold"), fg="#005a9c", bg="#e9f5ff").pack(anchor="w")
    
    ofertas_frame = tk.Frame(contenedor, bg="#e9f5ff")
    ofertas_frame.grid(row=2, column=1, sticky="sew", padx=10, pady=10)
    
    texto_oferta_label = "Sé el primero en ofertar."
    if historial:
        ultima_oferta = historial[-1]
        texto_oferta_label = f"Última oferta: {ultima_oferta['nombre']} por ${ultima_oferta['monto']:,}"

    label_ultima_oferta = tk.Label(ofertas_frame, text=texto_oferta_label, font=fuente_normal, bg="#e9f5ff")
    label_ultima_oferta.pack(side="left", anchor="w")
    
    estado_oferta_btn = tk.NORMAL if estado_subasta == "ACTIVA" else tk.DISABLED

    entry_oferta = tk.Entry(ofertas_frame, font=fuente_normal, width=10, state=estado_oferta_btn)
    entry_oferta.pack(side="left", padx=10)

    tk.Button(ofertas_frame, text="Ofertar", font=fuente_normal, bg="#a2f5a2", state=estado_oferta_btn,
              command=crear_funcion_ofertar(obra_id, entry_oferta, datos_usuario, callback_refrescar, precio_actual)).pack(side="left")

    tk.Button(ofertas_frame, text="Ver Historial", font=("Arial", 12),
              command=lambda h=historial, n=obra_data.get('nombre'): abrir_ventana_historial_usuario(h, n)).pack(side="left", padx=10)

# --- FUNCIÓN PRINCIPAL DE LA GALERÍA ---

def abrir_galeria(root, datos_usuario):
    """Abre la ventana principal de la galería, adaptándose al estado de la subasta."""
    root.withdraw()
    
    ventana = tk.Toplevel(root)
    ventana.title("Galería de Arte - Rastro de Luz")
    ventana.geometry("1200x800")
    ventana.configure(bg="#d0e7f9")

    def cerrar_sesion():
        if hasattr(ventana, 'after_id'):
            ventana.after_cancel(ventana.after_id)
        root.deiconify()
        ventana.destroy()
    ventana.protocol("WM_DELETE_WINDOW", cerrar_sesion)
    
    tk.Label(ventana, text=f"Bienvenido, {datos_usuario.get('nombre', 'Usuario')}", font=("Arial", 22, "bold"), bg="#d0e7f9").pack(pady=10)
    tk.Button(ventana, text="Cerrar Sesión", font=("Arial", 13), command=cerrar_sesion).place(relx=0.98, rely=0.01, anchor="ne")

    estado_label = tk.Label(ventana, text="Cargando configuración...", font=("Arial", 16, "bold"), bg="#d0e7f9", fg="blue")
    estado_label.pack()

    main_content_frame = tk.Frame(ventana, bg="#d0e7f9")
    main_content_frame.pack(expand=True, fill="both")

    canvas = tk.Canvas(main_content_frame, bg="#d0e7f9", highlightthickness=0)
    scrollbar = tk.Scrollbar(main_content_frame, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg="#d0e7f9")
    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    boton_pago = tk.Button(main_content_frame, text="💳 Proceder al Pago de Obras Ganadas", font=("Arial", 16), bg="#add8e6")
    
    def actualizar_cronometro(fecha_fin):
        ahora = datetime.now(timezone.utc)
        restante = fecha_fin - ahora
        if restante.total_seconds() > 0:
            dias = restante.days
            horas, resto = divmod(int(restante.seconds), 3600)
            minutos, segundos = divmod(resto, 60)
            estado_label.config(text=f"La subasta cierra en: {dias}d {horas:02d}h {minutos:02d}m {segundos:02d}s", fg="red")
            ventana.after_id = ventana.after(1000, lambda: actualizar_cronometro(fecha_fin))
        else:
            cargar_configuracion_y_obras()

    def cargar_configuracion_y_obras():
        for widget in scroll_frame.winfo_children():
            widget.destroy()

        obras_ganadas = []
        
        try:
            config_doc = db.collection('configuracion').document('subasta').get()
            if not config_doc.exists:
                estado_label.config(text="La subasta no ha sido configurada.", fg="red")
                return

            config_data = config_doc.to_dict()
            fecha_inicio = config_data.get('fecha_inicio')
            fecha_fin = config_data.get('fecha_fin')
            ahora = datetime.now(timezone.utc)
            
            estado_actual = ""
            if ahora < fecha_inicio:
                estado_actual = "PENDIENTE"
                estado_label.config(text=f"La subasta comenzará el {fecha_inicio.astimezone().strftime('%Y-%m-%d a las %H:%M')}", fg="blue")
            elif fecha_inicio <= ahora < fecha_fin:
                estado_actual = "ACTIVA"
                actualizar_cronometro(fecha_fin)
            else:
                estado_actual = "CERRADA"
                estado_label.config(text="La subasta ha finalizado. ¡Revisa si eres uno de los ganadores!", fg="black")

            obras_ref = db.collection('obras_subasta').order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
            for obra_doc in obras_ref:
                obra_id = obra_doc.id
                obra_data = obra_doc.to_dict()
                crear_widget_obra(scroll_frame, obra_id, obra_data, estado_actual, datos_usuario, lambda: cargar_configuracion_y_obras())

                historial = obra_data.get("historial_ofertas", [])
                if estado_actual == "CERRADA" and historial:
                    ganador = historial[-1]['nombre']
                    if ganador == datos_usuario.get('nombre'):
                        obra_ganada = obra_data.copy()
                        obra_ganada['ofertas']['historial_ofertas'] = [historial[-1]]
                        obras_ganadas.append(obra_ganada)
            
            if estado_actual == "CERRADA" and obras_ganadas:
                boton_pago.pack(side="bottom", pady=20)
                boton_pago.config(command=lambda: abrir_pantalla_pago(ventana, obras_ganadas))
            else:
                boton_pago.pack_forget()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la configuración de la subasta: {e}", parent=ventana)

    cargar_configuracion_y_obras()