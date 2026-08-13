"""! 
@file lanzar_campana.py
@brief Script principal para la automatización de búsqueda y prospección por correo electrónico.
@details Este script utiliza DuckDuckGo para buscar empresas locales, extrae sus correos y envía propuestas personalizadas mediante SMTP.
@author Daniel Jose Coste Santos
@date 2026
"""

import logging
import requests
import os
import re
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from ddgs import DDGS
from email_validator import validate_email, EmailNotValidError

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

# Enlace público de tu Google Drive con permisos para "Cualquier persona con el enlace"
ENLACE_CV_ONLINE = "https://drive.google.com/file/d/1gPaPYxijwrLuZmOZLsG0_oPwUkv99uko/view?usp=drive_link"


def buscar_empresas_duckduckgo(query, limite=10):
    """!
    @brief Realiza una búsqueda web para encontrar empresas.
    @param query (str) El término de búsqueda que se enviará al motor.
    @param limite (int) Número máximo de resultados a extraer.
    @return list Una lista de diccionarios que contienen el 'nombre' y la 'web' de cada empresa.
    """
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


def extraer_correo(url):
    """!
    @brief Analiza el HTML de una página web para extraer y validar correos electrónicos.
    @details Utiliza expresiones regulares para atrapar correos, los pasa por una lista de exclusión (typos) y finalmente realiza una validación de registros MX DNS.
    @param url (str) La dirección web de la empresa a analizar.
    @return str|None Devuelve el correo en texto plano si es válido y real, o None si no encuentra nada útil.
    """
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


def enviar_propuesta():
    """!
    @brief Función principal que orquesta la ejecución del script.
    @details Se encarga de llamar al motor de búsqueda, iterar sobre los negocios, conectar al servidor SMTP mediante TLS y enviar los mensajes HTML personalizados.
    """
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
                    <p>Hola equipo de <strong>{nombre}</strong>,</p>
                    
                    <p>He estado revisando su sitio web ({web}) y me comunico para ponerme a su disposición.</p>
                    
                    <p>Soy un programador independiente y estudiante de Inteligencia Artificial enfocado en la automatización. Estoy buscando empresas en la zona que requieran apoyo técnico, desarrollo de scripts para interactuar con APIs, gestión de bases de datos o resolución de problemas técnicos estructurados.</p>
                    
                    <p>Me adapto rápidamente a nuevas tecnologías y me enfoco en crear herramientas prácticas que optimicen flujos de trabajo.</p>
                    
                    <div class="button-container">
                        <a href="{ENLACE_CV_ONLINE}" target="_blank" class="btn">Ver mi Currículum Vitae</a>
                    </div>
                    
                    <p>Podemos agendar una breve llamada de 5 minutos si actualmente necesitan apoyo en sus proyectos de desarrollo.</p>
                    
                    <p>Quedo a su disposición.</p>
                </div>
                <div class="footer">
                    Este es un correo directo enviado por Daniel Coste.<br>
                    Contacto: {SENDER_EMAIL} <br>
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


if __name__ == "__main__":
    enviar_propuesta()