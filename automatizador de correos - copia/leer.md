# Sistema de Prospección Automatizada {#mainpage}

## Descripción General
Este proyecto es un script automatizado en **Python** diseñado para la prospección comercial e institucional (*Cold Emailing*). Su objetivo principal es buscar negocios locales en la web, extraer correos electrónicos, validar su entrega mediante consultas DNS y enviar de forma automática propuestas de servicios estructuradas en HTML.

@author Daniel Jose Coste Santos
@version 1.0.0
@date 2026

---

## Dependencias y Requisitos
Para que este script funcione correctamente, es necesario contar con **Python 3.10+** y las siguientes librerías de terceros:

- `requests` (>=2.31): Descarga y peticiones de código fuente HTML.
- `ddgs`: Búsqueda automatizada utilizando DuckDuckGo.
- `email-validator`: Validación sintáctica de correos.
- `dnspython`: Comprobación de registros MX para validar entrega.
- `python-dotenv`: Gestión segura de credenciales de entorno.

\code{.bash}
pip install requests ddgs email-validator dnspython python-dotenv
\endcode

---

## Configuración del Archivo `.env`

El sistema utiliza un modelo *stateless* (sin estado guardado en memoria) y requiere un archivo `.env` en la misma carpeta que el script principal. Esto es vital para proteger tus contraseñas y evitar que queden expuestas en el código fuente.

Crea un archivo llamado exactamente `.env` y pega este código dentro, reemplazando los valores con tus datos reales:

```env
# Configuración del servidor de salida (Ejemplo con Gmail)
SMTP_SERVER="smtp.gmail.com"
SMTP_PORT=587

# Tus credenciales de acceso
SENDER_EMAIL="tu_correo@gmail.com"
SENDER_PASSWORD="tu_contraseña_de_aplicacion_de_16_digitos"
```

> **Nota importante:** Nunca subas este archivo a GitHub ni lo compartas con nadie. Añade `.env` a tu archivo `.gitignore`.

**Desglose línea por línea del archivo `.env`:**

<ul>
<li>
<p><code>SMTP_SERVER="smtp.gmail.com"</code>: Define la dirección del servidor de correo saliente. En este caso, configurado para usar el servidor SMTP de Gmail.</p>
</li>
<li>
<p><code>SMTP_PORT=587</code>: Especifica el puerto por el que se conectará al servidor SMTP. El puerto 587 es el estándar para conexiones seguras (STARTTLS).</p>
</li>
<li>
<p><code>SENDER_EMAIL="tu_correo@gmail.com"</code>: Tu dirección de correo electrónico real desde la cual se enviarán los mensajes.</p>
</li>
<li>
<p><code>SENDER_PASSWORD="..."</code>: Tu contraseña. Si usas Gmail u otro servicio moderno, <strong>no debes poner tu contraseña habitual</strong>, sino generar una "Contraseña de Aplicación" de 16 dígitos desde los ajustes de seguridad de tu cuenta.</p>
</li>
</ul>

---

## Explicación del Código Línea por Línea

A continuación, se documentan los fragmentos principales del script. Cada bloque de código va acompañado de una lista explicativa.

### 1. Búsqueda de Empresas (DuckDuckGo)

Esta función busca en internet utilizando DuckDuckGo, lo que nos permite obtener resultados sin usar API Keys de pago.

```python
def buscar_empresas_duckduckgo(query, limite=10):
    logging.info(f"Buscando en DuckDuckGo: {query}...")
    empresas = []
    try:
        resultados = DDGS().text(query, max_results=limite)
        for res in resultados:
            empresas.append({
                "nombre": res.get("title", "Empresa Local"), 
                "web": res.get("href", "")
            })
        return empresas
    except Exception as e:
        logging.error(f"Error en la búsqueda: {e}")
        return []
```

**Desglose línea por línea:**

<ul>
<li>
<p><code>def buscar_empresas_duckduckgo(query, limite=10):</code> Define la función. Recibe el texto a buscar (<code>query</code>) y un límite de resultados por defecto de 10.</p>
</li>
<li>
<p><code>logging.info(...)</code> Imprime un mensaje en la consola para saber en qué parte del proceso está el script.</p>
</li>
<li>
<p><code>empresas = []</code> Crea una lista vacía donde guardaremos los datos de las empresas encontradas.</p>
</li>
<li>
<p><code>try:</code> Inicia un bloque de control de errores. Si DuckDuckGo bloquea la conexión, el programa no se cerrará de golpe.</p>
</li>
<li>
<p><code>resultados = DDGS().text(query, max_results=limite)</code> Llama a la librería <code>duckduckgo_search</code> (<code>DDGS</code>). El método <code>.text()</code> hace la búsqueda web real, limitando la cantidad de resultados.</p>
</li>
<li>
<p><code>for res in resultados:</code> Inicia un bucle que recorrerá cada página web encontrada en la búsqueda.</p>
</li>
<li>
<p><code>empresas.append({...})</code> Agrega un nuevo diccionario a nuestra lista de <code>empresas</code>.</p>
</li>
<li>
<p><code>"nombre": res.get("title", "Empresa Local")</code> Extrae el título de la página web. Si no lo encuentra, usa "Empresa Local" por defecto.</p>
</li>
<li>
<p><code>"web": res.get("href", "")</code> Extrae la URL (el enlace) de la página web.</p>
</li>
<li>
<p><code>return empresas</code> Devuelve la lista completa de empresas una vez termina el bucle.</p>
</li>
<li>
<p><code>except Exception as e:</code> Captura cualquier error que ocurra durante la búsqueda.</p>
</li>
<li>
<p><code>logging.error(...)</code> Registra el error exacto en la consola para poder investigar qué falló.</p>
</li>
<li>
<p><code>return []</code> Si hay un error, devuelve una lista vacía para que el resto del programa pueda continuar sin romperse.</p>
</li>
</ul>

---

### 2. Extracción y Validación de Correo Electrónico

Una vez que tenemos la URL, descargamos su código fuente para buscar patrones de correos electrónicos. Luego validamos si esos correos existen.

```python
def extraer_correo(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            # Busca el correo con Expresiones Regulares (Regex)
            patron = r"[a-zA-Z0-9.%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
            correos = re.findall(patron, res.text)
            
            # Valida los registros DNS MX de los correos encontrados
            for correo_candidato in correos:
                try:
                    validacion = validate_email(correo_candidato, check_deliverability=True)
                    return validacion.normalized
                except EmailNotValidError:
                    continue
        return None
    except Exception:
        pass
    return None
```

**mmg línea por línea:**

<ul>
<li>
<p><code>def extraer_correo(url):</code> Función que recibe una dirección web (URL) de una empresa.</p>
</li>
<li>
<p><code>headers = {"User-Agent": ...}</code> Disfraza nuestro script como si fuera un navegador web normal (Chrome en Windows). Muchas páginas bloquean accesos si detectan que es un script o bot.</p>
</li>
<li>
<p><code>res = requests.get(url, headers=headers, timeout=10)</code> Hace la petición web a la página. Espera máximo 10 segundos (<code>timeout</code>); si la página es muy lenta, se cancela para no quedarse colgado.</p>
</li>
<li>
<p><code>if res.status_code == 200:</code> Comprueba que la página cargó correctamente (el código HTTP 200 significa "OK").</p>
</li>
<li>
<p><code>patron = r"..."</code> Define una Expresión Regular (Regex). Esto es un patrón matemático que describe la forma de un email (texto + @ + texto + . + dominio).</p>
</li>
<li>
<p><code>correos = re.findall(patron, res.text)</code> Busca en todo el código HTML de la página (dentro de <code>res.text</code>) cualquier fragmento de texto que coincida con el patrón de correo definido arriba.</p>
</li>
<li>
<p><code>for correo_candidato in correos:</code> Recorre todos los correos que haya encontrado en la página (puede haber correos falsos o de ejemplo como <code>test@test.com</code>).</p>
</li>
<li>
<p><code>validacion = validate_email(..., check_deliverability=True)</code> Utiliza la librería <code>email_validator</code>. <code>check_deliverability=True</code> hace una consulta real a los registros DNS (MX) del dominio para ver si el servidor de correo realmente existe y puede recibir mensajes.</p>
</li>
<li>
<p><code>return validacion.normalized</code> Si el correo es real, lo devuelve en su formato estandarizado (en minúsculas) y termina la función.</p>
</li>
<li>
<p><code>except EmailNotValidError:</code> Si el validador descubre que el correo es falso o no existe, atrapa el error.</p>
</li>
<li>
<p><code>continue</code> Salta al siguiente correo de la lista para probarlo.</p>
</li>
<li>
<p><code>return None</code> Si después de revisar todo no encontró ningún correo válido, devuelve "Nada" (None).</p>
</li>
</ul>

---

### 3. Ejecución y Envío de Correos (SMTP)

Esta función orquesta todo: busca las empresas, extrae los correos y se conecta al servidor SMTP para enviar la propuesta.

```python
def enviar_propuesta():
    negocios = buscar_empresas_duckduckgo("empresas de desarrollo de software", limite=15)
    
    # Conecta al servidor de correos
    servidor = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    servidor.starttls()
    servidor.login(SENDER_EMAIL, SENDER_PASSWORD)
    
    for negocio in negocios:
        correo = extraer_correo(negocio["web"])
        if not correo:
            continue
            
        # Prepara el mensaje
        mensaje = MIMEMultipart("alternative")
        mensaje["Subject"] = "Propuesta de servicios técnicos e IA - Daniel Coste"
        mensaje["To"] = correo
        
        # Envia el correo y espera 15 segundos (Anti-Spam)
        servidor.send_message(mensaje)
        time.sleep(15)
        
    servidor.quit()
```

**Desglose línea por línea:**

<ul>
<li>
<p><code>negocios = buscar_empresas_duckduckgo(...)</code> Ejecuta el primer paso: busca 15 "empresas de desarrollo de software".</p>
</li>
<li>
<p><code>servidor = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)</code> Inicia la conexión con el servidor de salida (ej. Gmail) usando el puerto configurado en el archivo <code>.env</code>.</p>
</li>
<li>
<p><code>servidor.starttls()</code> Inicia el cifrado TLS. Esto es crucial para que la contraseña y los correos viajen encriptados de forma segura por internet.</p>
</li>
<li>
<p><code>servidor.login(SENDER_EMAIL, SENDER_PASSWORD)</code> Inicia sesión en tu cuenta de correo usando tus credenciales.</p>
</li>
<li>
<p><code>for negocio in negocios:</code> Itera sobre cada empresa que encontró en DuckDuckGo.</p>
</li>
<li>
<p><code>correo = extraer_correo(negocio["web"])</code> Llama a la segunda función para raspar y validar el correo de la página web de esa empresa.</p>
</li>
<li>
<p><code>if not correo: continue</code> Si la función devolvió <code>None</code> (no encontró correo o era inválido), pasa directamente a la siguiente empresa ignorando el resto del código.</p>
</li>
<li>
<p><code>mensaje = MIMEMultipart("alternative")</code> Crea el "sobre" del correo electrónico que permite enviar tanto texto plano como HTML enriquecido.</p>
</li>
<li>
<p><code>mensaje["Subject"] = "..."</code> Define el asunto del correo que verá el destinatario.</p>
</li>
<li>
<p><code>mensaje["To"] = correo</code> Asigna el correo extraído como destinatario.</p>
</li>
<li>
<p><code>servidor.send_message(mensaje)</code> Envía el correo preparado a través del servidor conectado.</p>
</li>
<li>
<p><code>time.sleep(15)</code> Pausa el programa por 15 segundos enteros. Esto actúa como un mecanismo Anti-Spam para que los proveedores (como Gmail) no te bloqueen la cuenta por enviar masivamente en un segundo.</p>
</li>
<li>
<p><code>servidor.quit()</code> Cierra la conexión de forma segura con el servidor de correos al terminar todo el bucle.</p>
</li>
</ul>