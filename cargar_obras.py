import firebase_admin
from firebase_admin import credentials, firestore

# --- INICIALIZACIÓN DE FIREBASE ---
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Conexión con Firestore exitosa.")
except Exception as e:
    print(f"❌ Error al conectar con Firebase: {e}")
    exit()

# --- DATOS DE LAS OBRAS CON URLs PÚBLICAS Y VERIFICADAS ---
obras_a_cargar = [
    {
        "nombre": "La noche estrellada", "autor": "Vincent van Gogh", "fecha": "1889",
        "descripcion": "Una de las obras más icónicas del postimpresionismo.",
        "image_urls": ["https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1024px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"],
        "historial_ofertas": [], "ofertas": {"precio_base": 1000000, "subasta_abierta": True}
    },
    {
        "nombre": "La joven de la perla", "autor": "Johannes Vermeer", "fecha": "c. 1665",
        "descripcion": "Obra maestra del pintor neerlandés, a veces llamada la 'Mona Lisa del Norte'.",
        "image_urls": ["https://upload.wikimedia.org/wikipedia/commons/thumb/d/d7/Meisje_met_de_parel.jpg/800px-Meisje_met_de_parel.jpg"], # <-- LINK CORREGIDO
        "historial_ofertas": [], "ofertas": {"precio_base": 850000, "subasta_abierta": True}
    },
    {
        "nombre": "La Mona Lisa", "autor": "Leonardo da Vinci", "fecha": "c. 1503-1506",
        "descripcion": "El retrato más famoso del mundo, conocido por su enigmática sonrisa.",
        "image_urls": ["https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_natural_color.jpg/800px-Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_natural_color.jpg"], # <-- LINK CORREGIDO
        "historial_ofertas": [], "ofertas": {"precio_base": 2500000, "subasta_abierta": True}
    },
    {
        "nombre": "El Hombre de Vitruvio", "autor": "Leonardo da Vinci", "fecha": "c. 1490",
        "descripcion": "Estudio de las proporciones del cuerpo humano.",
        "image_urls": ["https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/Da_Vinci_Vitruve_Luc_Viatour.jpg/800px-Da_Vinci_Vitruve_Luc_Viatour.jpg"],
        "historial_ofertas": [], "ofertas": {"precio_base": 500000, "subasta_abierta": True}
    },
    {
        "nombre": "La última cena", "autor": "Leonardo da Vinci", "fecha": "c. 1495–1498",
        "descripcion": "Mural que representa la última cena de Jesús con sus apóstoles.",
        "image_urls": ["https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Leonardo_da_Vinci_-_The_Last_Supper_high_res.jpg/1280px-Leonardo_da_Vinci_-_The_Last_Supper_high_res.jpg"], # <-- LINK CORREGIDO
        "historial_ofertas": [], "ofertas": {"precio_base": 1800000, "subasta_abierta": True}
    }
]

# --- LÓGICA DE CARGA ---
obras_ref = db.collection('obras_subasta')
print("Iniciando carga de obras a Firestore...")

for obra_data in obras_a_cargar:
    obra_data['timestamp'] = firestore.SERVER_TIMESTAMP
    obras_ref.add(obra_data)
    print(f"✔️ Obra '{obra_data['nombre']}' registrada en Firestore.")

print("\n✅ Proceso de carga finalizado.")