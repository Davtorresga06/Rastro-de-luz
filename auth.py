import firebase_admin
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from werkzeug.security import generate_password_hash, check_password_hash

# Se asume que Firebase ya fue inicializado en el script principal (login.py)
db = firestore.client()

def registrar_usuario(nombre, correo, clave, rol='usuario'):
    """
    Registra un nuevo usuario en la colección 'usuarios' de Firestore.
    Almacena la contraseña de forma segura y asigna el rol especificado.
    """
    try:
        # Verifica eficientemente si el correo ya existe
        usuarios_ref = db.collection('usuarios')
        consulta = usuarios_ref.where(filter=FieldFilter("correo", "==", correo)).limit(1).stream()

        if len(list(consulta)) > 0:
            return False, "El correo electrónico ya está registrado."

        # Hashea la contraseña para no guardarla en texto plano
        clave_hasheada = generate_password_hash(clave)

        # Crea el documento del nuevo usuario con el rol proporcionado
        nuevo_usuario = {
            'nombre': nombre,
            'correo': correo,
            'clave_hash': clave_hasheada,
            'rol': rol,
            'fecha_registro': firestore.SERVER_TIMESTAMP
        }

        # Agrega el nuevo usuario a la base de datos
        usuarios_ref.add(nuevo_usuario)
        return True, "Registro exitoso."
    except Exception as e:
        return False, f"Ocurrió un error en el registro: {e}"


def verificar_usuario(correo, clave):
    """
    Verifica las credenciales de un usuario.
    Si son correctas, devuelve un diccionario con los datos del usuario.
    Si no, devuelve None.
    """
    try:
        usuarios_ref = db.collection('usuarios')
        consulta = usuarios_ref.where(filter=FieldFilter("correo", "==", correo)).limit(1).stream()
        resultados = list(consulta)

        if not resultados:
            return None, "Correo o contraseña incorrectos."

        usuario_doc = resultados[0]
        usuario_data = usuario_doc.to_dict()
        
        # Añadimos el ID del documento a los datos, será útil para futuras actualizaciones
        usuario_data['id'] = usuario_doc.id

        clave_guardada_hash = usuario_data.get('clave_hash')

        # Compara de forma segura la contraseña proporcionada con el hash guardado
        if check_password_hash(clave_guardada_hash, clave):
            # Devolvemos todos los datos del usuario si la clave es correcta
            return usuario_data, "Inicio de sesión exitoso."
        else:
            return None, "Correo o contraseña incorrectos."
    except Exception as e:
        return None, f"Ocurrió un error en la verificación: {e}"


def actualizar_usuario(usuario_id, datos_actualizados):
    """
    Actualiza los datos de un usuario. Si se incluye una nueva clave,
    la hashea antes de guardarla.
    """
    try:
        # Si en los datos a actualizar viene una 'clave' nueva...
        if 'clave' in datos_actualizados:
            nueva_clave = datos_actualizados.pop('clave') # La sacamos del diccionario
            # Solo hashear si el campo de nueva clave no está vacío
            if nueva_clave:
                datos_actualizados['clave_hash'] = generate_password_hash(nueva_clave)

        usuario_ref = db.collection('usuarios').document(usuario_id)
        usuario_ref.update(datos_actualizados)
        return True, "Usuario actualizado correctamente."
    except Exception as e:
        return False, f"Ocurrió un error al actualizar el usuario: {e}"