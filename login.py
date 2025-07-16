import tkinter as tk
from tkinter import messagebox
import firebase_admin
from firebase_admin import credentials

# --- MÓDULOS DE LA APLICACIÓN ---
# Se importarán después de inicializar Firebase para evitar errores.

# --- INICIALIZACIÓN DE FIREBASE ---
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred, {
            # Asegúrate de que esta línea coincida exactamente
            'storageBucket': 'rastro-de-luz-d69a5.firebasestorage.app'
        })
    print("✅ Conexión con Firebase (Firestore y Storage) exitosa.")
except Exception as e:  
    messagebox.showerror("Error Crítico", f"No se pudo conectar a Firebase: {e}")
    exit()

# Ahora que Firebase está inicializado, importamos nuestros módulos
from auth import registrar_usuario, verificar_usuario
from galeria_admin import abrir_panel_admin
from galeria_app import abrir_galeria

# Código secreto para el acceso de administrador
CODIGO_ADMIN = "050806"

def mostrar_formulario(root, rol, accion):
    """Muestra el formulario para 'Iniciar Sesión' o 'Registro' para un rol específico."""
    root.withdraw()
    ventana_formulario = tk.Toplevel(root)
    ventana_formulario.title(f"Formulario de {accion.capitalize()} - {rol.upper()}")
    ventana_formulario.geometry("450x450")
    ventana_formulario.configure(bg="#d0e7f9")
    fuente = ("Arial", 14)

    def al_cerrar():
        ventana_formulario.destroy()
        mostrar_opciones_login(root, rol)
    ventana_formulario.protocol("WM_DELETE_WINDOW", al_cerrar)

    titulo = "📝 Registro" if accion == "registro" else "🔐 Iniciar Sesión"
    tk.Label(ventana_formulario, text=f"{titulo} - {rol.upper()}", font=("Arial", 20, "bold"), bg="#d0e7f9").pack(pady=20)
    
    frame_campos = tk.Frame(ventana_formulario, bg="#d0e7f9")
    frame_campos.pack(pady=10)
    entrada_nombre = None
    if accion == "registro":
        tk.Label(frame_campos, text="Nombre:", font=fuente, bg="#d0e7f9").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        entrada_nombre = tk.Entry(frame_campos, font=fuente, width=30)
        entrada_nombre.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(frame_campos, text="Correo:", font=fuente, bg="#d0e7f9").grid(row=1, column=0, sticky="e", padx=5, pady=5)
    entrada_correo = tk.Entry(frame_campos, font=fuente, width=30)
    entrada_correo.grid(row=1, column=1, padx=5, pady=5)

    tk.Label(frame_campos, text="Contraseña:", font=fuente, bg="#d0e7f9").grid(row=2, column=0, sticky="e", padx=5, pady=5)
    entrada_contraseña = tk.Entry(frame_campos, font=fuente, width=30, show="*")
    entrada_contraseña.grid(row=2, column=1, padx=5, pady=5)

    def procesar_registro():
        ok, msg = registrar_usuario(
            entrada_nombre.get(), entrada_correo.get(), entrada_contraseña.get(), rol=rol)
        if ok:
            messagebox.showinfo("Éxito", "Usuario registrado. Ahora puedes iniciar sesión.", parent=ventana_formulario)
            al_cerrar()
        else:
            messagebox.showerror("Error", msg, parent=ventana_formulario)

    def procesar_login():
        datos_usuario, msg = verificar_usuario(entrada_correo.get(), entrada_contraseña.get())
        if datos_usuario:
            if datos_usuario.get('rol') != rol:
                messagebox.showerror("Acceso Denegado", f"Tus credenciales son correctas, pero no tienes permisos de '{rol}'.", parent=ventana_formulario)
                return
            
            ventana_formulario.destroy() 
            if rol == 'admin':
                abrir_panel_admin(root, datos_usuario)
            else:
                abrir_galeria(root, datos_usuario)
        else:
            messagebox.showerror("Error", msg, parent=ventana_formulario)

    if accion == "registro":
        tk.Button(ventana_formulario, text="Registrarse", font=("Arial", 13), bg="#a2f5a2", width=20, command=procesar_registro).pack(pady=10)
    else:
        tk.Button(ventana_formulario, text="Ingresar", font=("Arial", 13), bg="#99ccff", width=20, command=procesar_login).pack(pady=10)

    tk.Button(ventana_formulario, text="‹ Volver", font=("Arial", 11),
              relief="flat", fg="blue", bg="#d0e7f9", cursor="hand2", command=al_cerrar).pack(pady=15)


def mostrar_opciones_login(root, rol):
    """Muestra los botones 'Iniciar Sesión' y 'Registrarse'."""
    root.withdraw()
    ventana_opciones = tk.Toplevel(root)
    ventana_opciones.title(f"Acceso {rol.capitalize()}")
    ventana_opciones.geometry("400x300")
    ventana_opciones.configure(bg="#d0e7f9")
    fuente = ("Arial", 14)

    def al_cerrar():
        root.deiconify()
        ventana_opciones.destroy()
    ventana_opciones.protocol("WM_DELETE_WINDOW", al_cerrar)

    tk.Label(ventana_opciones, text=f"Acceso {rol.upper()}", font=("Arial", 20, "bold"), bg="#d0e7f9").pack(pady=20)
    tk.Button(ventana_opciones, text="🔐 Iniciar Sesión", font=fuente, width=20,
              command=lambda: [ventana_opciones.destroy(), mostrar_formulario(root, rol, "login")]).pack(pady=10)
    tk.Button(ventana_opciones, text="📝 Registrarse", font=fuente, width=20,
              command=lambda: [ventana_opciones.destroy(), mostrar_formulario(root, rol, "registro")]).pack(pady=10)

    tk.Button(ventana_opciones, text="‹ Volver al inicio", font=("Arial", 11),
              relief="flat", fg="blue", bg="#d0e7f9", cursor="hand2", command=al_cerrar).pack(pady=15)


def validar_admin(root):
    """Abre una ventana para pedir el código de administrador."""
    root.withdraw()
    ventana_codigo = tk.Toplevel(root)
    ventana_codigo.title("Código de Administrador")
    ventana_codigo.geometry("350x200")
    ventana_codigo.configure(bg="#d0e7f9")
    fuente = ("Arial", 14)

    def al_cerrar():
        root.deiconify()
        ventana_codigo.destroy()
    ventana_codigo.protocol("WM_DELETE_WINDOW", al_cerrar)

    tk.Label(ventana_codigo, text="Ingresa el código:", font=fuente, bg="#d0e7f9").pack(pady=10)
    entrada_codigo = tk.Entry(ventana_codigo, font=fuente, show="*")
    entrada_codigo.pack()
    entrada_codigo.focus_force()

    def verificar():
        if entrada_codigo.get() == CODIGO_ADMIN:
            ventana_codigo.destroy()
            mostrar_opciones_login(root, "admin")
        else:
            messagebox.showerror("Código Incorrecto", "El código ingresado no es válido.", parent=ventana_codigo)
    
    botones_frame = tk.Frame(ventana_codigo, bg="#d0e7f9")
    botones_frame.pack(pady=20)

    tk.Button(botones_frame, text="Validar", font=fuente, command=verificar).pack(side="left", padx=10)
    tk.Button(botones_frame, text="Volver", font=("Arial", 12), command=al_cerrar).pack(side="left", padx=10)


def iniciar_app_escritorio():
    """Función principal que crea la ventana raíz con selección de rol."""
    root = tk.Tk()
    root.title("Bienvenido a Rastro de Luz")
    root.geometry("500x300")
    root.configure(bg="#d0e7f9")
    fuente = ("Arial", 14)

    tk.Label(root, text="🎨 Rastro de Luz", font=("Arial", 24, "bold"), bg="#d0e7f9").pack(pady=30)
    tk.Button(root, text="Acceso Usuario", font=fuente, width=25, height=2,
              command=lambda: mostrar_opciones_login(root, "usuario")).pack(pady=10)
    tk.Button(root, text="Acceso Administración", font=fuente, width=25, height=2,
              command=lambda: validar_admin(root)).pack(pady=10)
    root.mainloop()


if __name__ == "__main__":
    iniciar_app_escritorio()