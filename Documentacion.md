# Sistema de Automatizador Correos
@author Daniel Jose Coste Santos
@version 1.0.0
@date 2026

## Descripción General
Este proyecto es un script automatizado en **Python** diseñado para la prospección comercial e institucional (*Cold Emailing*). Su objetivo principal es buscar negocios locales en la web, extraer correos electrónicos, validar su entrega mediante consultas DNS y enviar de forma automática propuestas de servicios estructuradas en HTML.

---

## Dependencias y Requisitos
Para que este script funcione correctamente, es necesario contar con **Python 3.10+** y las siguientes librerías de terceros:

*   `requests` (>=2.31): Descarga y peticiones de código fuente HTML.
*   `ddgs`: Búsqueda automatizada utilizando DuckDuckGo.
*   `email-validator`: Validación sintáctica de correos.
*   `dnspython`: Comprobación de registros MX para validar entrega.
*   `python-dotenv`: Gestión segura de credenciales de entorno.

```bash
pip install requests duckduckgo_search email-validator dnspython python-dotenv
```

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
*   `SMTP_SERVER="smtp.gmail.com"`: Define la dirección del servidor de correo saliente. En este caso, configurado para usar el servidor SMTP de Gmail.
*   `SMTP_PORT=587`: Especifica el puerto por el que se conectará al servidor SMTP. El puerto 587 es el estándar para conexiones seguras (STARTTLS).
*   `SENDER_EMAIL="tu_correo@gmail.com"`: Tu dirección de correo electrónico real desde la cual se enviarán los mensajes.
*   `SENDER_PASSWORD="..."`: Tu contraseña. Si usas Gmail u otro servicio moderno, **no debes poner tu contraseña habitual**, sino generar una "Contraseña de Aplicación" de 16 dígitos desde los ajustes de seguridad de tu cuenta.

---

## Explicación del Código Línea por Línea

A continuación, se documentan los fragmentos principales del script actualizados a su versión real. Cada bloque de código va acompañado de una lista explicativa.

### 1. Búsqueda de Empresas (DuckDuckGo)
Esta función busca en internet utilizando DuckDuckGo, lo que nos permite obtener resultados sin usar API Keys de pago.

```python
def buscar_empresas_duckduckgo(query, limite=10):  
    logging.info(f"Buscando en DuckDuckGo: '{query}'...")
    empresas = []
    try:
        resultados = DDGS().text(query, max_results=limite)
        for res in resultados:
            empresas.append(
                {"nombre": res.get("title", "Empresa Local"), "web": res.get("href", "")}
            )
        return empresas
    except Exception as e:
        logging.error(f"Error en la búsqueda: {e}")
        return []
```

**Desglose línea por línea:**
*   `def buscar_empresas_duckduckgo(query, limite=10):` Define la función. Recibe el texto a buscar (`query`) y un límite de resultados por defecto de 10.
*   `logging.info(...)` Imprime un mensaje en la consola para saber qué término exacto se está buscando.
*   `empresas = []` Crea una lista vacía donde guardaremos los datos de las empresas encontradas.
*   `try:` Inicia un bloque de control de errores. Si DuckDuckGo bloquea la conexión, el programa no se cerrará de golpe.
*   `resultados = DDGS().text(query, max_results=limite)` Llama a la librería `duckduckgo_search` (`DDGS`). El método `.text()` hace la búsqueda web real, limitando la cantidad de resultados.
*   `for res in resultados:` Inicia un bucle que recorrerá cada página web encontrada en la búsqueda.
*   `empresas.append({...})` Agrega un nuevo diccionario a nuestra lista de `empresas`.
*   `"nombre": res.get("title", "Empresa Local")` Extrae el título de la página web. Si no lo encuentra, usa "Empresa Local" por defecto.
*   `"web": res.get("href", "")` Extrae la URL (el enlace) de la página web.
*   `return empresas` Devuelve la lista completa de empresas una vez termina el bucle.
*   `except Exception as e:` Captura cualquier error que ocurra durante la búsqueda.
*   `logging.error(...)` Registra el error exacto en la consola para poder investigar qué falló.
*   `return []` Si hay un error, devuelve una lista vacía para que el resto del programa pueda continuar sin romperse.

---

### 2. Extracción y Validación de Correo Electrónico
Una vez que tenemos la URL, descargamos su código fuente para buscar patrones de correos electrónicos. El código implementa exclusiones y listas negras para evitar correos falsos antes de validar su existencia.

```python
def extraer_correo(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            patron = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
            correos = re.findall(patron, res.text)
            
            # Lista negra de errores tipográficos comunes o correos de prueba
            typos_conocidos = ["infc", "infa", "inf0", "contato", "soprt", "adminis", "test", "ejemplo", "tuemail"]
            
            # Exclusiones generales de archivos o dominios de ejemplo
            exclusiones = ["png", "jpg", "w3.org", "sentry", "example", "domain", "correo@"]
            
            posibles = []
            for c in correos:
                c_lower = c.lower()
                local_part = c_lower.split("@")[0]
                
                if any(t in local_part for t in typos_conocidos):
                    continue
                if any(ex in c_lower for ex in exclusiones):  
                    continue
                
                posibles.append(c)
            
            # Verificación avanzada de entrega DNS para evitar correos inexistentes
            for correo_candidato in posibles:
                try:
                    validacion = validate_email(correo_candidato, check_deliverability=True)
                    return validacion.normalized
                except EmailNotValidError:
                    continue
                except:
                    pass
        return None
    except Exception:
        pass 
    return None
```

**Desglose línea por línea:**
*   `headers = {"User-Agent": ...}` Disfraza nuestro script como si fuera un navegador web normal (Chrome en Windows) para evitar bloqueos.
*   `res = requests.get(url, headers=headers, timeout=10)` Hace la petición web esperando máximo 10 segundos.
*   `patron = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"` Define la Expresión Regular para detectar correos (incluye guiones bajos `_` en la validación).
*   `correos = re.findall(patron, res.text)` Busca coincidencias en el código fuente HTML.
*   `typos_conocidos` y `exclusiones`: Define listas de palabras bloqueadas para ignorar imágenes (png, jpg), dominios falsos o errores de escritura (infc, inf0).
*   `for c in correos:` Itera y convierte los correos a minúsculas (`c_lower`). Si el correo contiene alguna palabra de las listas negras, lo salta (`continue`). Si pasa los filtros, lo añade a la lista `posibles`.
*   `validacion = validate_email(..., check_deliverability=True)` Verifica mediante DNS (MX) si el servidor puede recibir mensajes.
*   `return validacion.normalized` Si el correo es real, lo devuelve en minúsculas y termina la función.

---

### 3. Ejecución y Envío de Correos (SMTP con HTML)
Esta función orquesta todo: comprueba credenciales, busca las empresas, extrae los correos, construye un mensaje HTML profesional y se conecta al servidor SMTP para enviarlo.

```python
def enviar_propuesta():
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        logging.error("Falta configurar el .env")
        return
        
    query_busqueda = "empresas de desarrollo de software Santo Domingo"
    negocios = buscar_empresas_duckduckgo(query_busqueda, limite=15)
    
    if not negocios:
        logging.warning("No se encontraron resultados.")
        return
        
    try:
        servidor = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        servidor.starttls()
        servidor.login(SENDER_EMAIL, SENDER_PASSWORD)
    except Exception as e:
        logging.error(f"Error de SMTP: {e}")
        return
        
    for negocio in negocios:
        nombre = negocio["nombre"].split("|")[0].strip()
        web = negocio["web"]  
        logging.info(f"Analizando: {nombre}")
        correo = extraer_correo(web)
        
        if not correo:
            continue
            
        logging.info(f"¡Correo encontrado! {correo}")
        
        mensaje = MIMEMultipart("alternative")
        mensaje["From"] = SENDER_EMAIL
        mensaje["To"] = correo
        mensaje["Subject"] = "Propuesta de servicios técnicos e IA - Daniel Coste"
        
        html_cuerpo = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f3f4f6; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
                .header {{ background-color: #1e293b; padding: 30px 40px; text-align: left; }}
                .header h1 {{ color: #ffffff; margin: 0; font-size: 22px; font-weight: 500; }}
                .header p {{ color: #94a3b8; margin: 5px 0 0 0; font-size: 14px; }}
                .content {{ padding: 40px; color: #334155; line-height: 1.6; font-size: 15px; }}
                .button-container {{ text-align: center; margin: 35px 0; }}
                .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff !important; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-weight: 600; font-size: 15px; box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2); }}
                .footer {{ background-color: #f8fafc; padding: 20px 40px; text-align: center; color: #64748b; font-size: 13px; border-top: 1px solid #e2e8f0; line-height: 1.5; }}  
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Daniel Jose Coste Santos</h1>
                    <p>Desarrollador de Software & Estudiante de IA</p>
                </div>
                <div class="content">
                    <p>Hola equipo de <strong>{{nombre}}</strong>,</p>
                    <p>He estado revisando su sitio web ({{web}}) y me comunico para ponerme a su disposición.</p>
                    <p>Soy un programador independiente y estudiante de Inteligencia Artificial enfocado en la automatización. Estoy buscando empresas en la zona que requieran apoyo técnico, desarrollo de scripts para interactuar con APIs, gestión de bases de datos o resolución de problemas técnicos estructurados.</p>
                    <p>Me adapto rápidamente a nuevas tecnologías y me enfoco en crear herramientas prácticas que optimicen flujos de trabajo.</p>
                    <div class="button-container">
                        <a href="{{ENLACE_CV_ONLINE}}" target="_blank" class="btn">Ver mi Currículum Vitae</a>
                    </div>
                    <p>Podemos agendar una breve llamada de 5 minutos si actualmente necesitan apoyo en sus proyectos de desarrollo.</p>
                    <p>Quedo a su disposición.</p>
                </div>
                <div class="footer">
                    Este es un correo directo enviado por Daniel Coste.<br>
                    Contacto: {{SENDER_EMAIL}} <br>
                    Santo Domingo, República Dominicana.
                </div>
            </div>
        </body>
        </html>  
        """
        
        parte_html = MIMEText(html_cuerpo, "html", "utf-8")
        mensaje.attach(parte_html)
        
        try:
            servidor.send_message(mensaje)
            logging.info(f"✅ Propuesta enviada exitosamente a: {correo}")
            time.sleep(15)
        except Exception as e:
            logging.error(f"❌ Error al enviar a {correo}: {e}")
            
    servidor.quit()
    logging.info("Campaña finalizada.")
```

**Desglose línea por línea:**
*   `if not SENDER_EMAIL...` Valida preventivamente si el archivo `.env` fue configurado correctamente antes de correr el script.
*   `query_busqueda = "empresas de desarrollo de software Santo Domingo"` Establece la consulta exacta para DuckDuckGo, buscando hasta 15 negocios.
*   `servidor.starttls()` y `servidor.login(...)` Se conectan a tu SMTP de forma segura gestionando posibles errores de autenticación con un `try-except`.
*   `nombre = negocio["nombre"].split("|")[0].strip()` Limpia el nombre extraído (ej: quita el nombre de la página después de una barra "|").
*   `html_cuerpo = f"""..."""` Construye una plantilla HTML responsiva con estilos CSS incorporados, inyectando dinámicamente el `{nombre}` de la empresa, la `{web}` y tu currículum `{ENLACE_CV_ONLINE}`.
*   `parte_html = MIMEText(html_cuerpo, "html", "utf-8")` Convierte la cadena HTML en un objeto de correo y se lo adjunta al mensaje principal usando `mensaje.attach()`.
*   `time.sleep(15)` Pausa el script 15 segundos después de cada envío exitoso para evitar ser marcado como Spam.
*   `servidor.quit()` Cierra la conexión SMTP una vez terminado el bucle y finaliza la campaña.
