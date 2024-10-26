import json
import base64
import requests
from flask import Flask, request, jsonify
import os
import threading
from threading import Lock
import unicodedata  # Importado para normalizar textos y eliminar tildes

app = Flask(__name__)

# Ruta base para los archivos
BASE_PATH = "./"

# Nueva ruta para los archivos de datos
DATA_PATH = os.path.join(BASE_PATH, "datos")

# Archivos que contienen los números que ya han recibido los mensajes
sent_numbers_file = os.path.join(DATA_PATH, "sent_numbers.txt")
precio_file = os.path.join(DATA_PATH, "precio.txt")
tienda_file = os.path.join(DATA_PATH, "tienda.txt")  # Archivo para la regla "tienda"

# Bloqueos para acceso a archivos
sent_numbers_lock = Lock()
precio_file_lock = Lock()
tienda_file_lock = Lock()

# Nombres de los archivos PDF
pdf_names = [
    "RELOJES de Caballero.pdf",
    "CARTERAS.pdf",
    "RELOJES de Dama.pdf",
    "MORRALES de Dama.pdf",
    "MORRALES de Caballero.pdf"
]
pdf_files = [os.path.join(BASE_PATH, pdf) for pdf in pdf_names]

# Nombres de los archivos de video para bienvenida
welcome_video_files = [
    os.path.join(BASE_PATH, "video1.mp4"),
    #os.path.join(BASE_PATH, "video2.mp4"),
    #os.path.join(BASE_PATH, "video3.mp4"),
    #os.path.join(BASE_PATH, "video4.mp4"),
    os.path.join(BASE_PATH, "video2.mp4")
]

# Nombres de los archivos de video para 'tienda'
tienda_video_files = [
    os.path.join(BASE_PATH, "impuestos.mp4")
]

# Nombres de los archivos de imagen para 'tienda'
image_names = [
    "tienda1.jpeg",
    "tienda2.jpeg"
]
image_files = [os.path.join(BASE_PATH, img) for img in image_names]

# Mensajes de bienvenida
welcome_messages = [
    "👋💚 *Buenas* 🤗",
    "Somos empresa 💼 *RUC: 20610868577* Registrada desde *1993* 🥳⭐⭐⭐⭐⭐",
    "✅🩷🩵 Precios *POR DOCENA*\n(si lleva 12 productos *en TOTAL* ) 🛒✨\n▫️⌚Relojes: *50 soles*\n https://wa.me/c/51903510695 \n▫️👜Carteras: *50 soles*\n▫️💼Morrales: *50 soles*\n▫️ Billeteras: *20 soles*\n▫️👛Monederos: *15 soles*\n▫️👝Chequeras: *30 soles*\n▫️Correas: *30 soles*"
]

# Texto para el primer video
first_video_message = """🥳Replica *A1 Rolex* ✨😍
⌚Por *DOCENA* relojes *50 soles*
💚 *CUALQUIER MODELO mismos precios* 🛍️"""

# Wuzapi API endpoint y token
wuzapi_url_text = "http://localhost:8080/chat/send/text"
wuzapi_url_document = "http://localhost:8080/chat/send/document"
wuzapi_url_video = "http://localhost:8080/chat/send/video"
wuzapi_url_image = "http://localhost:8080/chat/send/image"
wuzapi_token = "jhon"

# Diccionarios para manejar las sesiones y bloqueos por usuario
active_sessions = {}  # Cambiado para ser un diccionario de diccionarios
session_locks = {}

# Precodificar los PDFs, videos y imágenes
encoded_pdfs = {}
encoded_videos = {}
encoded_images = {}


def precodificar_archivos():
    """Precarga y codifica los archivos PDF, videos y imágenes."""
    for pdf_filename, pdf_name in zip(pdf_files, pdf_names):
        print(f"Precargando y codificando PDF {pdf_name}")
        encoded_pdf = encode_file_to_base64(pdf_filename)
        encoded_pdfs[pdf_name] = encoded_pdf

    for video_filename in welcome_video_files + tienda_video_files:
        video_name = os.path.basename(video_filename)
        print(f"Precargando y codificando video {video_name}")
        encoded_video = encode_file_to_base64(video_filename)
        encoded_videos[video_name] = encoded_video

    for image_filename, image_name in zip(image_files, image_names):
        print(f"Precargando y codificando imagen {image_name}")
        encoded_image = encode_file_to_base64(image_filename)
        encoded_images[image_name] = encoded_image


def encode_file_to_base64(file_path):
    with open(file_path, "rb") as file:
        return base64.b64encode(file.read()).decode('utf-8')


def has_received_catalog(phone_number):
    if not os.path.exists(sent_numbers_file):
        return False
    with sent_numbers_lock:
        with open(sent_numbers_file, 'r') as file:
            return phone_number in file.read()


def mark_as_sent(phone_number):
    with sent_numbers_lock:
        with open(sent_numbers_file, 'a') as file:
            file.write(phone_number + '\n')


def has_received_precio(phone_number):
    if not os.path.exists(precio_file):
        return False
    with precio_file_lock:
        with open(precio_file, 'r') as file:
            return phone_number in file.read()


def mark_as_precio_sent(phone_number):
    with precio_file_lock:
        with open(precio_file, 'a') as file:
            file.write(phone_number + '\n')


def has_received_tienda(phone_number):
    if not os.path.exists(tienda_file):
        return False
    with tienda_file_lock:
        with open(tienda_file, 'r') as file:
            return phone_number in file.read()


def mark_as_tienda_sent(phone_number):
    with tienda_file_lock:
        with open(tienda_file, 'a') as file:
            file.write(phone_number + '\n')


def send_message(phone_number, message_text):
    """Función para enviar un mensaje de texto."""
    print(f"Enviando mensaje: {message_text} a {phone_number}")
    payload = {
        "Phone": phone_number,
        "Body": message_text
    }
    response = requests.post(wuzapi_url_text, json=payload, headers={"token": wuzapi_token})
    print(f"Respuesta de Wuzapi: {response.json()}")


def send_pdf(phone_number, pdf_name):
    """Función para enviar un PDF precodificado."""
    print(f"Enviando PDF {pdf_name} a {phone_number}")
    encoded_pdf = encoded_pdfs.get(pdf_name)
    if not encoded_pdf:
        print(f"Error: PDF {pdf_name} no está precodificado.")
        return
    payload = {
        "Phone": phone_number,
        "Document": f"data:application/octet-stream;base64,{encoded_pdf}",
        "FileName": pdf_name
    }
    response = requests.post(wuzapi_url_document, json=payload, headers={"token": wuzapi_token})
    print(f"Respuesta de Wuzapi: {response.json()}")


def send_video(phone_number, video_name, caption=None):
    """Función para enviar un video precodificado."""
    print(f"Enviando video {video_name} a {phone_number}")
    encoded_video = encoded_videos.get(video_name)
    if not encoded_video:
        print(f"Error: Video {video_name} no está precodificado.")
        return
    payload = {
        "Phone": phone_number,
        "Video": f"data:video/mp4;base64,{encoded_video}",
        "FileName": video_name
    }
    if caption:
        payload["Caption"] = caption
    elif video_name == "video1.mp4":
        payload["Caption"] = first_video_message
    response = requests.post(wuzapi_url_video, json=payload, headers={"token": wuzapi_token})
    print(f"Respuesta de Wuzapi: {response.json()}")


def send_image(phone_number, image_name, caption):
    """Función para enviar una imagen precodificada."""
    print(f"Enviando imagen {image_name} a {phone_number}")
    encoded_image = encoded_images.get(image_name)
    if not encoded_image:
        print(f"Error: Imagen {image_name} no está precodificado.")
        return
    payload = {
        "Phone": phone_number,
        "Image": f"data:image/jpeg;base64,{encoded_image}",
        "FileName": image_name,
        "Caption": caption
    }
    response = requests.post(wuzapi_url_image, json=payload, headers={"token": wuzapi_token})
    print(f"Respuesta de Wuzapi: {response.json()}")


def remove_accents(input_str):
    """Función para eliminar tildes y acentos de un texto."""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])


def start_wuzapi():
    # URL de inicio de sesión
    login_url = "http://localhost:8080/login/?token=jhon"

    try:
        # Intentamos hacer una solicitud GET al URL de login para iniciar Wuzapi
        response = requests.get(login_url)

        if response.status_code == 200:
            print("Iniciado correctamente en Wuzapi.")
        else:
            print(f"Error al iniciar sesión en Wuzapi: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Error de conexión: {e}")


@app.route('/webhook', methods=['POST'])
def webhook():
    # Obtener los datos entrantes
    if request.content_type == 'application/json':
        data = request.get_json()
    elif request.content_type == 'application/x-www-form-urlencoded':
        data = request.form.to_dict()
        if 'jsonData' in data:
            data['jsonData'] = json.loads(data['jsonData'])
    else:
        return jsonify({"error": "Unsupported Media Type"}), 415

    print(f"Datos recibidos: {data}")  # Para depuración

    try:
        sender_full = data['jsonData']['event']['Info']['Sender']
        sender = sender_full.split('@')[0]  # Extraer solo el número de teléfono
    except KeyError:
        return jsonify({"error": "Bad Request: No sender found"}), 400

    # Obtener el texto del mensaje si está disponible
    message_text = ''
    try:
        message_text = data['jsonData']['event']['Message']['conversation']
    except KeyError:
        pass  # El mensaje puede no contener 'conversation' en algunos casos

    # Listado de palabras clave para la regla "tienda"
    tienda_keywords = [
        'donde', 'dnd', 'dnde',
    'estan', 'estn', 'est',
    'ubicados', 'ubicado', 'ubicar', 'ubi', 'ubic',
    'envios', 'envio', 'env', 'envi',
    'local', 'locales', 'loc',
    'fisico', 'fisica', 'fisic', 'fis',
    'tienda', 'tiend', 'tda', 'tnd',
    'delivery', 'deliviri', 'delibery', 'deliv', 'del',
    'presencial', 'presencialmente', 'presenc', 'presen',
    'son', 'som',
    'ubicar', 'ubica', 'ubicas', 'ubic',
    'provincia', 'provincias', 'provin', 'prov',
    'contraentrega', 'contrentrega', 'cntraentrega', 'contra',
    'entrega', 'entregas', 'entregar', 'entreg',
    'pago', 'pagos', 'pagar', 'pag',
    'deposito', 'deposit', 'dep',
    'transferencia', 'transfer', 'transf', 'trans',
    'yape', 'yap',
    'hacia', 'haci',
    'hacen', 'hace', 'hac', 'ace',
    'metodo', 'metodos', 'metod', 'met',
    'lima', 'limas', 'lma',
    'arequipa', 'aqp',
    'tacna',
    'peru',
    'parte', 'partes', 'part',
    'queda', 'quedan', 'qued',
    'somos', 'soy', 'son', 'som',
    'shalom',
    'olva',
    'enviaria', 'enviar', 'envia',
    'pruebas', 'prueba', 'prueb',
    'confianza', 'confian', 'conf',
    'estafa', 'estafas', 'estaf',
    'seguridad', 'seguro', 'segur',
    'nuevo', 'nueva', 'nuev',
    'comprar', 'compra', 'compr',
    'tiene', 'tienen', 'tien',
    'personal', 'persona', 'person',
    'traer', 'trae', 'traes', 'tra',
    'puedes', 'puede', 'pued',
    'dar', 'doy', 'da',
    'importados', 'importado', 'import',
    'agencia', 'agencias', 'agen',
    'dias', 'dia',
    'cuantos', 'cuanto', 'cuant',
    'demora', 'demoraria', 'demor',
    'envio', 'env',
    'para', 'par',
    'deliviri', 'delibery', 'deliv',
    'motorizado', 'motorizados', 'motoriz',
    'ubi', 'ubic',
    'localizacion', 'localiz',
    'haces', 'ace', 'hac',
    'quiero', 'quieres', 'quier',
    'ases', 'ace',
    'hora', 'horas', 'hor',
    'interesado', 'interes', 'interesa',
    'medios', 'medio', 'medi',
    'adquirir', 'adquir',
    'estamos', 'esta', 'estan',
    'momento', 'momentos', 'moment',
    'aka', 'aca',
    'asta', 'hasta', 'ast',
    'traiga', 'traig',
    'viajo', 'viaja', 'viaj',
    'fuera', 'fuer',
    'estoy', 'esta',
    'trabajo', 'trabaja', 'trabaj',
    'alla',
    'recogerlo', 'recoger', 'recog',
    'entregas', 'entregar', 'entreg',
    'adelantado', 'adelantar', 'adelant',
    'enviar', 'envia', 'envi',
    'domicilio', 'domic',
    'ventanilla', 'ventan',
    'todo', 'toda', 'todas', 'todos', 'tod',
    'ubico', 'ubic',
    'cusco',
    'encuentran', 'encuentra', 'encontr',
    'recoje', 'recoge', 'recog',
    'llega', 'llegar', 'lleg',
    'cuando', 'cuand',
    'asen', 'hacen', 'hace', 'hac',
    'provincias', 'provincia', 'provin', 'prov',
    'como', 'cm',
    'es',
    'xk', 'xq', 'por que', 'porque',
    'trujillo',
    'quieras', 'quier',
    'gratis', 'grat',
    'domde', 'donde', 'dnd',
    'eres', 'er',
    'x',
    'adelantado', 'adelant',
    'adelante', 'adelant',
    'primero', 'primer', 'prim',
    'seguro', 'segur',
    'adicional', 'adicion',
    'pedido', 'pedidos', 'pedir', 'ped',
    'distrito', 'distritos', 'distr',
    'acercarme', 'acercar', 'acerc',
    'ciudad', 'ciud',
    'ustedes', 'usted', 'uds', 'ud',
    'lugar', 'lugares', 'lug',
    'otro', 'otros', 'otra', 'otr',
    'hacer', 'hacen', 'hace', 'hac',
    'podriamos', 'podria', 'podr',
    'tienen', 'tiene', 'tien',
    'domiciliado', 'domicili',
    'verlos', 'verlo', 'ver',
    'persona', 'personal', 'person',
    'visitar', 'visita', 'visit',
    'enviarte', 'enviar', 'envia',
    'contacto', 'contact',
    'avion', 'avio',
    'cercado', 'cerca', 'cerc',
    'nacional', 'nacion',
    'nivel', 'niveles', 'niv',
    'mandan', 'manda', 'mand',
    'sitios', 'sitio', 'siti',
    'canete',
    'su','lima', 'lim', 'lma',
    'arequipa', 'aqp', 'areq', 'areqpa',
    'cusco', 'cus', 'cusc',
    'trujillo', 'truji', 'truj',
    'chiclayo', 'chicla', 'chic',
    'piura', 'piur',
    'iquitos', 'iquit', 'iqt',
    'pucallpa', 'pucall', 'puc',
    'tacna', 'tac',
    'huancayo', 'huanca', 'huanc',
    'juliaca', 'julia', 'jul',
    'ica', 'ic',
    'cajamarca', 'cajamar', 'caj',
    'ayacucho', 'ayacuch', 'aya',
    'puno', 'pun',
    'tarapoto', 'tarap', 'tarapot',
    'chimbote', 'chimbo', 'chimb',
    'moquegua', 'moqueg', 'moq',
    'huanuco', 'huanuc', 'huan',
    'abancay', 'abanc', 'aban',
    'huaraz', 'huara', 'huar',
    'tumbes', 'tumb',
    'puerto maldonado', 'puerto maldo', 'p maldonado', 'pmald',
    'ica', 'ic',
    'talara', 'talar',
    'huacho', 'huach',
    'cerro de pasco', 'cerro pasco', 'c pasco', 'cpasco',
    'sullana', 'sullan', 'sull',
    'cuzco', 'cuz',
    'pisco', 'pisc',
    'bagua', 'bag',
    'jaen', 'jae',
    'moyobamba', 'moyobamb', 'moyo',
    'yurimaguas', 'yurimagu', 'yuri',
    'huaral', 'huara',
    'satipo', 'sati',
    'mollendo', 'mollen', 'moll',
    'barranca', 'barranc', 'barr',
    'chepen', 'chep',
    'puquio', 'puqui',
    'tarma', 'tarm',
    'chincha', 'chinch',
    'paita', 'pait',
    'camaná', 'camana', 'caman',
    'pucusana', 'pucusan', 'pucu',
    'lunahuana', 'lunahuan', 'luna',
    'chincheros', 'chincher', 'chinch',
    'ocros', 'ocr',
    'paramonga', 'paramong', 'param',
    'chancay', 'chanca', 'chan',
    'rioja', 'rioj',
    'tocache', 'tocach', 'toc',
    'la merced', 'l merced', 'lmerced',
    'chilca', 'chilc',
    'ancón', 'ancon', 'anco',
    'pisco', 'pisc',
    'ferreñafe', 'ferrenafe', 'ferren',
    'sechura', 'sechur', 'sech',
    'mochumi', 'mochum',
    'ilave', 'ilav',
    'san ignacio', 's ignacio', 's. ignacio',
    'casma', 'casm',
    'huanta', 'huant',
    'huaytará', 'huaytara', 'huayt',
    'catacaos', 'catacao', 'catac',
    'tarma', 'tarm',
    'tocache', 'tocach', 'toc',
    'moyobamba', 'moyobamb', 'moyo',
    'pichanaki', 'pichanak', 'pich',
    'zarumilla', 'zarumill', 'zaru',
    'nazca', 'nazc',
    'chachapoyas', 'chachapoy', 'chacha',
    'san vicente de cañete', 'san vicente', 's vicente', 'cañete', 'canete',
    'huancavelica', 'huancav', 'huanc',
    'callao', 'calla',
    'colán', 'colan', 'cola',
    'cutervo', 'cuterv', 'cut',
    'chulucanas', 'chulucan', 'chulu',
    'reque', 'req',
    'tumbes', 'tumb',
    'zarate', 'zarat',
    'chachapoyas', 'chachapoy', 'chacha',
    'otros', 'otra', 'otr',
    'se',
    'limas', 'lima', 'lma',
    'partes', 'parte', 'part',
    'todes', 'toda', 'todos', 'tod',
    'encomienda', 'encomiendas', 'encomiend',
    'ir', 'voy', 'va',
    'iremos', 'ire',
    'visitaremos', 'visitar', 'visit',
    'estaremos', 'estar', 'esta',
    'hora', 'horas', 'hor',
    'atienden', 'atiende', 'atend',
    'venden', 'vende', 'vend',
    'publicidad', 'publica', 'public',
    'cancela', 'cancelar', 'cancel',
    'mano', 'manos', 'man',
    'exacta', 'exacto', 'exact',
    'diferencias', 'diferentes', 'diferent', 'diferenc',
    'ubicada', 'ubicado', 'ubicar', 'ubic',
    'cofnirmas', 'confirmas', 'confirmar', 'confirm',
    'dejar', 'dej',
    'traes', 'trae', 'tra',
    'verdad', 'verd',
    'mandar', 'manda', 'mand',
    'ate',
    'llegan', 'llega', 'lleg',
    'encontrarte', 'encontrar', 'encontr',
    'podemos', 'pueden', 'puede', 'pod',
    'hoy',
    'manana',
    'encontrarlos', 'encontrar', 'encontr',
    'llegue', 'llegar', 'lleg',
    'modo', 'modos', 'mod',
    'comas',
    'saber', 'sabes', 'sab',
    'conocer', 'conoces', 'conoc',
    'plaza', 'plaz',
    'zona', 'zonas', 'zon',
    'ahorita', 'ahora', 'ahor',
    'favor', 'fav',
    'hacemos', 'hace', 'hac',
    'tren', 'trenes', 'tren',
    'estacion',
    'podrias', 'podrian', 'podria', 'podr',
    'flores', 'flor',
    'pago', 'pagos', 'pag','pgo',
    'llegar', 'llega', 'lleg',
    ]

    # Normalizar el texto del mensaje y eliminar tildes
    message_normalized = remove_accents(message_text).lower()

    # Asegurar que solo un hilo procese la interacción de un cliente
    if sender not in session_locks:
        session_locks[sender] = Lock()

    with session_locks[sender]:
        if not has_received_catalog(sender):
            # Es la primera vez que nos contacta, enviar mensajes de bienvenida
            if sender not in active_sessions:
                active_sessions[sender] = {}
            if 'welcome' not in active_sessions[sender]:
                active_sessions[sender]['welcome'] = True
                threading.Thread(target=send_welcome_pdfs_videos_to_client, args=(sender,)).start()
            else:
                print(f"Welcome messages already being sent to {sender}, not starting another thread.")
        else:
            # Ya ha recibido los mensajes de bienvenida
            if any(keyword in message_normalized for keyword in tienda_keywords):
                # Prioridad a la regla "tienda"
                if not has_received_tienda(sender):
                    if sender not in active_sessions:
                        active_sessions[sender] = {}
                    if 'tienda' not in active_sessions[sender]:
                        active_sessions[sender]['tienda'] = True
                        threading.Thread(target=send_tienda_messages, args=(sender,)).start()
                    else:
                        print(f"Tienda messages already being sent to {sender}, not starting another thread.")
                else:
                    print(f"Tienda messages already sent to {sender}.")
            elif not has_received_precio(sender):
                if sender not in active_sessions:
                    active_sessions[sender] = {}
                if 'precio' not in active_sessions[sender]:
                    active_sessions[sender]['precio'] = True
                    threading.Thread(target=send_precio_message, args=(sender,)).start()
                else:
                    print(f"Precio messages already being sent to {sender}, not starting another thread.")

    return jsonify({"status": "success"}), 200


def send_precio_message(sender):
    try:
        # Enviar los dos mensajes solicitados
        messages = [
            "⌚ *Por DOCENA* relojes *50 soles*",
            "¿Cuántas unidades desea llevar? 🙌☺️",
            "70 soles le podemos dejar *por unidad*"
        ]
        for message in messages:
            send_message(sender, message)
        mark_as_precio_sent(sender)
    finally:
        # Remover 'precio' de active_sessions[sender]
        if 'precio' in active_sessions.get(sender, {}):
            active_sessions[sender].pop('precio', None)
            if not active_sessions[sender]:
                active_sessions.pop(sender, None)
        # Limpiar la sesión y el bloqueo
        session_locks.pop(sender, None)


def send_tienda_messages(sender):
    """Envía las imágenes y video de la tienda al cliente."""
    try:
        # Enviar la primera imagen con su caption
        image1_name = "tienda1.jpeg"
        image1_caption = "📍Tenemos *TIENDA FÍSICA* en la *Zona Franca del Perú* 🚚 *Mz K Lote 08* 🙌🏻✨ 🤩Ciudad de *TACNA, Perú* 🇵🇪"
        send_image(sender, image1_name, image1_caption)

        # Enviar la segunda imagen con su caption
        image2_name = "tienda2.jpeg"
        image2_caption = "Nosotros somos *PROVEEDORES* de *acá de la Zona Económica Especial de TACNA*✨🤗🫱🏻‍🫲🏻"
        send_image(sender, image2_name, image2_caption)

        # Enviar el video con su caption
        video_name = "impuestos.mp4"
        video_caption = """🤩Trabajamos en la *Zona Franca del Perú* pues es zona *LIBRE DE IMPUESTOS* 🥳✨🫱🏻‍🫲🏻"""
        send_video(sender, video_name, caption=video_caption)

        # Enviar el mensaje de texto
        message = """*Contraentrega* en toda Tacna 

Entregamos *personalmente a domicilio*"""
        send_message(sender, message)

        mark_as_tienda_sent(sender)
    finally:
        # Remover 'tienda' de active_sessions[sender]
        if 'tienda' in active_sessions.get(sender, {}):
            active_sessions[sender].pop('tienda', None)
            if not active_sessions[sender]:
                active_sessions.pop(sender, None)
        # Limpiar la sesión y el bloqueo
        session_locks.pop(sender, None)


def send_welcome_pdfs_videos_to_client(sender):
    """Envía los mensajes de bienvenida, PDFs y videos al cliente."""
    try:
        # Enviar mensajes de bienvenida
        for message in welcome_messages:
            send_message(sender, message)

        # Enviar PDFs
        for pdf_name in pdf_names:
            send_pdf(sender, pdf_name)

        # Enviar videos
        for video_filename in welcome_video_files:
            video_name = os.path.basename(video_filename)
            send_video(sender, video_name)

        mark_as_sent(sender)
    finally:
        # Remover 'welcome' de active_sessions[sender]
        if 'welcome' in active_sessions.get(sender, {}):
            active_sessions[sender].pop('welcome', None)
            if not active_sessions[sender]:
                active_sessions.pop(sender, None)
        session_locks.pop(sender, None)


# Ejecutar inicializaciones al importar el módulo
precodificar_archivos()
start_wuzapi()
