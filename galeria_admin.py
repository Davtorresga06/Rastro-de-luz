import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from PIL import Image, ImageTk
import requests
from io import BytesIO
from datetime import datetime, timezone
import uuid
import os
from urllib.parse import unquote, urlparse
import threading

import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore_v1.base_query import FieldFilter
from auth import actualizar_usuario

db = firestore.client()
try:
    bucket = storage.bucket()
except Exception as e:
    print(f"ADVERTENCIA: Storage no configurado. Error: {e}")
    bucket = None

# --- FUNCIONES AUXILIARES (Definidas antes de ser usadas) ---

def cargar_imagen_async(url, label_imagen, tamano=(150, 150)):
    """Descarga una imagen en un hilo separado para no bloquear la UI."""
    def _trabajo_de_hilo():
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            # Aumentamos el tiempo de espera a 20 segundos
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            
            img_data = BytesIO(response.content)
            img = Image.open(img_data)
            img.thumbnail(tamano, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            # Actualizar la UI de forma segura desde el hilo principal
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
        tk.Label(scroll_frame, text="No hay imágenes para esta obra.", font=("Arial", 14), bg="#e9f5ff").pack(padx=10, pady=10)
    else:
        for url in image_urls:
            placeholder = tk.Label(scroll_frame, text="Cargando...", font=("Arial", 12), bg="#e0e0e0", width=50, height=20)
            placeholder.pack(padx=10, pady=10)
            # Reutilizamos la función de carga asíncrona, ajustando el tamaño
            cargar_imagen_async(url, placeholder, (500, 400))

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

# --- FUNCIONES DE LA VENTANA PRINCIPAL DEL ADMIN ---

def abrir_panel_admin(root, datos_usuario):
    """Abre el panel de administración principal con pestañas."""
    root.withdraw()
    
    ventana_admin = tk.Toplevel(root)
    ventana_admin.title("Panel de Administración - Rastro de Luz")
    ventana_admin.geometry("1200x700")
    ventana_admin.configure(bg="#d0e7f9")

    def cerrar_sesion():
        root.deiconify()
        ventana_admin.destroy()

    ventana_admin.protocol("WM_DELETE_WINDOW", cerrar_sesion)

    top_frame = tk.Frame(ventana_admin, bg="#d0e7f9")
    top_frame.pack(fill="x", pady=10, padx=10)
    tk.Label(top_frame, text=f"Administrador: {datos_usuario.get('nombre')}", font=("Arial", 18, "bold"), bg="#d0e7f9").pack(side="left")
    tk.Button(top_frame, text="Cerrar Sesión", font=("Arial", 13), command=cerrar_sesion).pack(side="right")

    notebook = ttk.Notebook(ventana_admin)
    notebook.pack(expand=True, fill="both", padx=10, pady=10)

    frame_obras = tk.Frame(notebook, bg="#d0e7f9")
    frame_usuarios = tk.Frame(notebook, bg="#d0e7f9")
    frame_config = tk.Frame(notebook, bg="#d0e7f9")

    notebook.add(frame_obras, text="Gestión de Obras")
    notebook.add(frame_usuarios, text="Gestión de Usuarios")
    notebook.add(frame_config, text="Configuración de Subasta")

    setup_obras_tab(frame_obras)
    setup_usuarios_tab(frame_usuarios)
    setup_configuracion_tab(frame_config)

# --- PESTAÑA DE GESTIÓN DE OBRAS ---

def setup_obras_tab(parent_frame):
    """Configura la interfaz de la pestaña de gestión de obras."""
    boton_frame = tk.Frame(parent_frame, bg="#d0e7f9")
    boton_frame.pack(pady=10)
    tk.Button(boton_frame, text="➕ Registrar Nueva Obra", font=("Arial", 15), bg="#a2f5a2",
              command=lambda: abrir_ventana_registro_obra(lambda: refrescar_obras(scroll_frame))).pack()
    
    canvas = tk.Canvas(parent_frame, bg="#d0e7f9", highlightthickness=0)
    scrollbar = tk.Scrollbar(parent_frame, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg="#d0e7f9")
    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    refrescar_obras(scroll_frame)


def refrescar_obras(scroll_frame):
    """Limpia y recarga la lista de obras desde Firestore."""
    for widget in scroll_frame.winfo_children():
        widget.destroy()
    try:
        obras_ref = db.collection('obras_subasta').order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
        for obra_doc in obras_ref:
            crear_widget_obra(scroll_frame, obra_doc)
    except Exception as e:
        tk.Label(scroll_frame, text=f"Error al cargar obras: {e}", fg="red").pack()


def crear_widget_obra(parent, obra_doc):
    """Crea el widget para una sola obra en la lista de admin."""
    obra_id = obra_doc.id
    obra_data = obra_doc.to_dict()
    
    contenedor = tk.Frame(parent, bd=2, relief="groove", bg="#e9f5ff", padx=15, pady=15)
    contenedor.pack(pady=10, padx=10, fill="x")

    label_img = tk.Label(contenedor, text="Cargando...", width=18, height=8, bg="#e0e0e0")
    label_img.pack(side="left", padx=10)

    image_urls = obra_data.get('image_urls', [])
    if image_urls:
        cargar_imagen_async(image_urls[0], label_img)

    info_frame = tk.Frame(contenedor, bg="#e9f5ff")
    info_frame.pack(side="left", expand=True, fill="x", padx=10)
    
    tk.Label(info_frame, text=f"{obra_data.get('nombre', 'N/A')}", font=("Arial", 16, "bold"), bg="#e9f5ff").pack(anchor="w")
    tk.Label(info_frame, text=f"Autor: {obra_data.get('autor', 'N/A')}", font=("Arial", 13), bg="#e9f5ff").pack(anchor="w")
    estado = "Activa" if obra_data.get('ofertas', {}).get('subasta_abierta') else "Cerrada"
    tk.Label(info_frame, text=f"Estado: {estado}", font=("Arial", 13), bg="#e9f5ff").pack(anchor="w")

    botones_frame = tk.Frame(contenedor, bg="#e9f5ff")
    botones_frame.pack(side="right", padx=10)
    
    tk.Button(botones_frame, text=f"Ver Imágenes ({len(image_urls)})", bg="#a9a9a9", font=("Arial", 11),
              command=lambda nom=obra_data.get('nombre'), urls=image_urls: abrir_galeria_de_imagenes(nom, urls)).pack(fill="x", pady=2)
    tk.Button(botones_frame, text="Ver Historial", bg="#d3d3d3", font=("Arial", 12),
              command=lambda hist=obra_data.get('historial_ofertas', []), nom=obra_data.get('nombre'): abrir_ventana_historial(hist, nom)).pack(fill="x", pady=2)
    tk.Button(botones_frame, text="Editar", bg="#add8e6", font=("Arial", 12),
              command=lambda id=obra_id, data=obra_data: abrir_ventana_edicion_obra(id, data, lambda: refrescar_obras(parent))).pack(fill="x", pady=2)
    tk.Button(botones_frame, text="Eliminar", bg="#f5a2a2", font=("Arial", 12),
              command=lambda id=obra_id, data=obra_data: eliminar_obra(id, data, lambda: refrescar_obras(parent))).pack(fill="x", pady=2)


def abrir_ventana_registro_obra(callback_refrescar):
    """Abre una ventana para registrar una nueva obra, permitiendo elegir el método de imagen."""
    ventana_reg = tk.Toplevel()
    ventana_reg.title("Registrar Nueva Obra")
    ventana_reg.geometry("600x650")
    ventana_reg.configure(bg="#d0e7f9")
    fuente = ("Arial", 12)

    campos_frame = tk.Frame(ventana_reg, bg="#d0e7f9")
    campos_frame.pack(pady=15, padx=20)

    campos_info = {}
    labels_texto = ["Nombre", "Autor", "Fecha", "Descripción", "Precio Base ($)"]
    for i, texto in enumerate(labels_texto):
        tk.Label(campos_frame, text=f"{texto}:", font=fuente, bg="#d0e7f9").grid(row=i, column=0, sticky="w", pady=3)
        entry = tk.Entry(campos_frame, font=fuente, width=50)
        entry.grid(row=i, column=1, sticky="w", pady=3)
        campos_info[texto] = entry

    metodo_frame = tk.Frame(ventana_reg, bg="#d0e7f9")
    metodo_frame.pack(pady=10, padx=20, anchor="w")
    tk.Label(metodo_frame, text="Método para añadir imágenes:", font=fuente, bg="#d0e7f9").pack(anchor="w", side="left")
    
    metodo_var = tk.StringVar(value="URL")

    subida_frame = tk.Frame(ventana_reg, bg="#d0e7f9")
    rutas_locales = []
    label_subida = tk.Label(subida_frame, text="Ningún archivo seleccionado.", bg="#d0e7f9")
    
    def seleccionar_archivos():
        nonlocal rutas_locales
        rutas = filedialog.askopenfilenames(title="Selecciona archivos de imagen", filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg")])
        if rutas:
            rutas_locales = list(rutas)
            label_subida.config(text=f"{len(rutas_locales)} archivo(s) seleccionado(s).")

    tk.Button(subida_frame, text="Seleccionar Archivos...", command=seleccionar_archivos).pack()
    label_subida.pack()

    url_frame = tk.Frame(ventana_reg, bg="#d0e7f9")
    tk.Label(url_frame, text="URLs de las Imágenes (una por línea):", font=fuente, bg="#d0e7f9").pack(anchor="w")
    urls_texto = tk.Text(url_frame, height=5, width=60, font=("Courier", 10))
    urls_texto.pack(pady=5)

    def toggle_metodo():
        if metodo_var.get() == "URL":
            subida_frame.pack_forget()
            url_frame.pack(pady=5, padx=20, fill="x")
        else:
            url_frame.pack_forget()
            subida_frame.pack(pady=5, padx=20, fill="x")

    tk.Radiobutton(metodo_frame, text="Pegar URL", variable=metodo_var, value="URL", bg="#d0e7f9", command=toggle_metodo).pack(anchor="w", side="left")
    tk.Radiobutton(metodo_frame, text="Subir Archivo", variable=metodo_var, value="SUBIR", bg="#d0e7f9", command=toggle_metodo).pack(anchor="w", side="left")
    toggle_metodo()

    def guardar_obra():
        lista_urls_final = []
        if metodo_var.get() == "URL":
            urls_raw = urls_texto.get("1.0", tk.END).strip()
            lista_urls_final = [url.strip() for url in urls_raw.split('\n') if url.strip()]
        else:
            if not bucket:
                messagebox.showerror("Error de Configuración", "Firebase Storage no está configurado.", parent=ventana_reg)
                return
            if not rutas_locales:
                messagebox.showerror("Error", "No has seleccionado ningún archivo para subir.", parent=ventana_reg)
                return
            try:
                for ruta in rutas_locales:
                    nombre_unico = f"obras/{uuid.uuid4()}{os.path.splitext(ruta)[1]}"
                    blob = bucket.blob(nombre_unico)
                    blob.upload_from_filename(ruta)
                    blob.make_public()
                    lista_urls_final.append(blob.public_url)
            except Exception as e:
                messagebox.showerror("Error de Subida", f"No se pudieron subir las imágenes: {e}", parent=ventana_reg)
                return

        if not lista_urls_final:
            messagebox.showerror("Error", "Debes proporcionar al menos una imagen.", parent=ventana_reg)
            return
            
        try:
            nombre = campos_info["Nombre"].get()
            autor = campos_info["Autor"].get()
            descripcion = campos_info["Descripción"].get()
            precio_base = float(campos_info["Precio Base ($)"].get())
            if not all([nombre, autor, descripcion]):
                messagebox.showerror("Error", "Todos los campos de texto son obligatorios.", parent=ventana_reg)
                return
            datos_obra = {"nombre": nombre, "autor": autor, "fecha": campos_info["Fecha"].get(), "descripcion": descripcion, "image_urls": lista_urls_final, "historial_ofertas": [], "ofertas": {"precio_base": precio_base, "subasta_abierta": True}, "timestamp": firestore.SERVER_TIMESTAMP}
            db.collection('obras_subasta').add(datos_obra)
            messagebox.showinfo("Éxito", "Obra registrada.", parent=ventana_reg)
            ventana_reg.destroy()
            callback_refrescar()
        except ValueError:
             messagebox.showerror("Error", "El precio base debe ser un número.", parent=ventana_reg)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la obra: {e}", parent=ventana_reg)
            
    tk.Button(ventana_reg, text="Guardar Obra", font=("Arial", 14), bg="#a2f5a2", command=guardar_obra).pack(pady=20)


def abrir_ventana_edicion_obra(obra_id, obra_data, callback_refrescar):
    ventana_edit = tk.Toplevel()
    ventana_edit.title(f"Editando: {obra_data.get('nombre')}")
    ventana_edit.geometry("600x550")
    ventana_edit.configure(bg="#d0e7f9")
    fuente = ("Arial", 12)
    campos_frame = tk.Frame(ventana_edit, bg="#d0e7f9")
    campos_frame.pack(pady=15, padx=20)
    campos_info = {}
    labels_texto = ["Nombre", "Autor", "Fecha", "Descripción", "Precio Base ($)"]
    for i, texto in enumerate(labels_texto):
        tk.Label(campos_frame, text=f"{texto}:", font=fuente, bg="#d0e7f9").grid(row=i, column=0, sticky="w", pady=3)
        entry = tk.Entry(campos_frame, font=fuente, width=50)
        entry.grid(row=i, column=1, sticky="w", pady=3)
        if texto == "Precio Base ($)":
            entry.insert(0, obra_data.get('ofertas', {}).get('precio_base', ''))
        else:
            clave = texto.lower().replace(" ", "_").replace("ó", "o")
            entry.insert(0, obra_data.get(clave, ''))
        campos_info[texto] = entry
    urls_frame = tk.Frame(ventana_edit, bg="#d0e7f9")
    urls_frame.pack(pady=10, padx=20, fill="x")
    tk.Label(urls_frame, text="URLs de las Imágenes (una por línea):", font=fuente, bg="#d0e7f9").pack(anchor="w")
    urls_texto = tk.Text(urls_frame, height=5, width=60, font=("Courier", 10))
    urls_texto.pack(pady=5)
    existing_urls = obra_data.get('image_urls', [])
    urls_texto.insert("1.0", "\n".join(existing_urls))
    def guardar_cambios():
        urls_raw = urls_texto.get("1.0", tk.END).strip()
        nueva_lista_urls = [url.strip() for url in urls_raw.split('\n') if url.strip()]
        if not nueva_lista_urls:
            messagebox.showerror("Error", "La obra debe tener al menos una URL.", parent=ventana_edit)
            return
        try:
            nuevos_datos = {"nombre": campos_info["Nombre"].get(), "autor": campos_info["Autor"].get(), "fecha": campos_info["Fecha"].get(), "descripcion": campos_info["Descripción"].get(), "image_urls": nueva_lista_urls, "ofertas.precio_base": float(campos_info["Precio Base ($)"].get())}
            db.collection('obras_subasta').document(obra_id).update(nuevos_datos)
            messagebox.showinfo("Éxito", "Obra actualizada.", parent=ventana_edit)
            ventana_edit.destroy()
            callback_refrescar()
        except ValueError:
            messagebox.showerror("Error", "El precio base debe ser un número válido.", parent=ventana_edit)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo actualizar la obra: {e}", parent=ventana_edit)
    tk.Button(ventana_edit, text="Guardar Cambios", font=("Arial", 14), bg="#a2f5a2", command=guardar_cambios).pack(pady=20)


def eliminar_obra(obra_id, obra_data, callback_refrescar):
    if messagebox.askyesno("Confirmar Eliminación", "¿Estás seguro de que quieres eliminar esta obra?"):
        try:
            if bucket:
                image_urls = obra_data.get('image_urls', [])
                for url in image_urls:
                    if "firebasestorage.googleapis.com" in url:
                        try:
                            path_completo = urlparse(url).path
                            path_en_bucket = unquote(path_completo.split('/o/')[-1])
                            blob = bucket.blob(path_en_bucket)
                            if blob.exists():
                                blob.delete()
                                print(f"Imagen {path_en_bucket} eliminada de Storage.")
                        except Exception as e:
                            print(f"No se pudo eliminar la imagen {url} de Storage: {e}")
            db.collection('obras_subasta').document(obra_id).delete()
            messagebox.showinfo("Éxito", "La obra ha sido eliminada.")
            callback_refrescar()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar la obra: {e}")

def abrir_ventana_historial(historial, nombre_obra):
    ventana_historial = tk.Toplevel()
    ventana_historial.title(f"Historial de Ofertas - {nombre_obra}")
    ventana_historial.geometry("500x400")
    ventana_historial.configure(bg="#e9f5ff")
    fuente_titulo = ("Arial", 14, "bold")
    fuente_item = ("Arial", 12)
    tk.Label(ventana_historial, text=f"Historial para: {nombre_obra}", font=fuente_titulo, bg="#e9f5ff").pack(pady=10)
    canvas = tk.Canvas(ventana_historial, bg="#e9f5ff", highlightthickness=0)
    scrollbar = tk.Scrollbar(ventana_historial, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg="#e9f5ff")
    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    if not historial:
        tk.Label(scroll_frame, text="No se han realizado ofertas.", font=fuente_item, bg="#e9f5ff").pack(padx=10, pady=10)
    else:
        for i, oferta in enumerate(reversed(historial)):
            texto_oferta = f"{i+1}. {oferta.get('nombre', 'N/A')} ofreció: ${oferta.get('monto', 0):,}"
            tk.Label(scroll_frame, text=texto_oferta, font=fuente_item, bg="#e9f5ff").pack(anchor="w", padx=10, pady=2)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")


# --- PESTAÑA DE GESTIÓN DE USUARIOS ---
def setup_usuarios_tab(parent_frame):
    canvas = tk.Canvas(parent_frame, bg="#d0e7f9", highlightthickness=0)
    scrollbar = tk.Scrollbar(parent_frame, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg="#d0e7f9")
    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    refrescar_usuarios(scroll_frame)

def refrescar_usuarios(scroll_frame):
    for widget in scroll_frame.winfo_children():
        widget.destroy()
    try:
        usuarios_ref = db.collection('usuarios').stream()
        for user_doc in usuarios_ref:
            crear_widget_usuario(scroll_frame, user_doc)
    except Exception as e:
        tk.Label(scroll_frame, text=f"Error al cargar usuarios: {e}", fg="red").pack()
        
def crear_widget_usuario(parent, user_doc):
    user_data = user_doc.to_dict()
    user_data['id'] = user_doc.id
    contenedor = tk.Frame(parent, bd=1, relief="solid", bg="#ffffff", padx=10, pady=10)
    contenedor.pack(pady=5, padx=10, fill="x")
    info_frame = tk.Frame(contenedor, bg="white")
    info_frame.pack(side="left", expand=True, fill="x")
    tk.Label(info_frame, text=f"Nombre: {user_data.get('nombre', 'N/A')}", font=("Arial", 14, "bold"), bg="white").pack(anchor="w")
    tk.Label(info_frame, text=f"Correo: {user_data.get('correo', 'N/A')}", font=("Arial", 12), bg="white").pack(anchor="w")
    tk.Label(info_frame, text=f"Rol: {user_data.get('rol', 'N/A').upper()}", font=("Arial", 12, "italic"), bg="white").pack(anchor="w")
    tk.Button(contenedor, text="Editar", bg="#add8e6", font=("Arial", 12),
              command=lambda data=user_data: abrir_ventana_edicion_usuario(data, lambda: refrescar_usuarios(parent))).pack(side="right")

def abrir_ventana_edicion_usuario(user_data, callback_refrescar):
    ventana_edicion = tk.Toplevel()
    ventana_edicion.title(f"Editando a {user_data.get('nombre')}")
    ventana_edicion.geometry("500x450")
    ventana_edicion.configure(bg="#d0e7f9")
    fuente_labels = ("Arial", 14)
    fuente_entries = ("Arial", 13)
    frame = tk.Frame(ventana_edicion, bg="#d0e7f9")
    frame.pack(pady=20, padx=20)
    tk.Label(frame, text="Nombre:", font=fuente_labels, bg="#d0e7f9").grid(row=0, column=0, sticky="w", pady=5)
    entry_nombre = tk.Entry(frame, font=fuente_entries, width=35)
    entry_nombre.insert(0, user_data.get('nombre', ''))
    entry_nombre.grid(row=0, column=1, pady=5)
    tk.Label(frame, text="Correo:", font=fuente_labels, bg="#d0e7f9").grid(row=1, column=0, sticky="w", pady=5)
    entry_correo = tk.Entry(frame, font=fuente_entries, width=35)
    entry_correo.insert(0, user_data.get('correo', ''))
    entry_correo.grid(row=1, column=1, pady=5)
    tk.Label(frame, text="Nueva Contraseña:", font=fuente_labels, bg="#d0e7f9").grid(row=2, column=0, sticky="w", pady=5)
    entry_clave = tk.Entry(frame, font=fuente_entries, width=35, show="*")
    entry_clave.grid(row=2, column=1, pady=5)
    tk.Label(frame, text="(Dejar en blanco para no cambiar)", font=("Arial", 9, "italic"), bg="#d0e7f9").grid(row=3, column=1, sticky="w")
    tk.Label(frame, text="Rol:", font=fuente_labels, bg="#d0e7f9").grid(row=4, column=0, sticky="w", pady=5)
    roles = ['usuario', 'admin']
    rol_var = tk.StringVar(value=user_data.get('rol'))
    combo_roles = ttk.Combobox(frame, textvariable=rol_var, values=roles, state="readonly", font=fuente_entries, width=33)
    combo_roles.grid(row=4, column=1, sticky="w", pady=5)
    def guardar_cambios():
        datos_para_actualizar = {'nombre': entry_nombre.get(), 'correo': entry_correo.get(), 'rol': rol_var.get()}
        nueva_clave = entry_clave.get()
        if nueva_clave:
            datos_para_actualizar['clave'] = nueva_clave
        if messagebox.askyesno("Confirmar", "¿Guardar los cambios para este usuario?"):
            ok, msg = actualizar_usuario(user_data.get('id'), datos_para_actualizar)
            if ok:
                messagebox.showinfo("Éxito", "Usuario actualizado.", parent=ventana_edicion)
                ventana_edicion.destroy()
                callback_refrescar()
            else:
                messagebox.showerror("Error", msg, parent=ventana_edicion)
    tk.Button(ventana_edicion, text="Guardar Cambios", font=("Arial", 14), bg="#a2f5a2", command=guardar_cambios).pack(pady=20)

# --- PESTAÑA DE CONFIGURACIÓN DE SUBASTA ---
def setup_configuracion_tab(parent_frame):
    fuente_titulo = ("Arial", 16, "bold")
    fuente_normal = ("Arial", 13)
    config_frame = tk.Frame(parent_frame, bg="#d0e7f9")
    config_frame.pack(pady=20, padx=20)
    tk.Label(config_frame, text="Configuración de Tiempos de la Subasta", font=fuente_titulo, bg="#d0e7f9").grid(row=0, column=0, columnspan=2, pady=10)
    tk.Label(config_frame, text="Formato: AAAA-MM-DD HH:MM (ej: 2025-07-14 21:00)", font=("Arial", 10, "italic"), bg="#d0e7f9").grid(row=1, column=0, columnspan=2, pady=(0, 20))
    tk.Label(config_frame, text="Fecha de Inicio:", font=fuente_normal, bg="#d0e7f9").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    entry_inicio = tk.Entry(config_frame, font=fuente_normal, width=30)
    entry_inicio.grid(row=2, column=1, padx=5, pady=5)
    tk.Label(config_frame, text="Fecha de Fin:", font=fuente_normal, bg="#d0e7f9").grid(row=3, column=0, sticky="w", pady=5)
    entry_fin = tk.Entry(config_frame, font=fuente_normal, width=30)
    entry_fin.grid(row=3, column=1, padx=5, pady=5)
    def guardar_configuracion():
        formato_fecha = "%Y-%m-%d %H:%M"
        try:
            fecha_inicio_str = entry_inicio.get()
            fecha_fin_str = entry_fin.get()
            fecha_inicio_naive = datetime.strptime(fecha_inicio_str, formato_fecha)
            fecha_fin_naive = datetime.strptime(fecha_fin_str, formato_fecha)
            fecha_inicio_aware = fecha_inicio_naive.astimezone()
            fecha_fin_aware = fecha_fin_naive.astimezone()
            if fecha_fin_aware <= fecha_inicio_aware:
                messagebox.showerror("Error de Lógica", "La fecha de fin debe ser posterior a la de inicio.")
                return
            config_ref = db.collection('configuracion').document('subasta')
            config_ref.set({'fecha_inicio': fecha_inicio_aware, 'fecha_fin': fecha_fin_aware})
            messagebox.showinfo("Éxito", "Configuración guardada.")
        except ValueError:
            messagebox.showerror("Error de Formato", f"Usa el formato: AAAA-MM-DD HH:MM")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la configuración: {e}")
    try:
        config_doc = db.collection('configuracion').document('subasta').get()
        if config_doc.exists:
            config_data = config_doc.to_dict()
            formato_fecha = "%Y-%m-%d %H:%M"
            fecha_inicio_local = config_data.get('fecha_inicio').astimezone()
            fecha_fin_local = config_data.get('fecha_fin').astimezone()
            entry_inicio.insert(0, fecha_inicio_local.strftime(formato_fecha))
            entry_fin.insert(0, fecha_fin_local.strftime(formato_fecha))
    except Exception as e:
        print(f"No se pudo cargar config de subasta: {e}")
    tk.Button(config_frame, text="Guardar Configuración", font=fuente_normal, bg="#a2f5a2", command=guardar_configuracion).grid(row=4, column=0, columnspan=2, pady=20)