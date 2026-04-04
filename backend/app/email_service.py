import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# CONFIGURACIÓN DE MAILTRAP
# Reemplaza estos valores con los que te dio Mailtrap
# ==========================================
SMTP_SERVER = "sandbox.smtp.mailtrap.io"
SMTP_PORT = 2525
SMTP_USERNAME = "74ea577f66db56"
SMTP_PASSWORD = "2a3a1287dd9b16"  # <-- CAMBIAR
SENDER_EMAIL = "bienvenida@tuplataforma.com" # Puede ser cualquiera en Mailtrap

def send_verification_email(email: str, token: str):
    # El enlace que activará la cuenta en tu backend
    verification_link = f"http://127.0.0.1:8000/verify-email?token={token}"
    
    # 1. Crear la estructura del mensaje
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verifica tu cuenta para comenzar"
    msg["From"] = SENDER_EMAIL
    msg["To"] = email

    # 2. Diseñar el cuerpo del correo en HTML
    html_content = f"""
    <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #191C1E; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h2 style="color: #002B5B;">¡Bienvenido a la Kroot!</h2>
            </div>
            
            <p style="font-size: 16px;">Estamos muy felices de tenerte con nosotros. Has dado el primer paso para llevar el control de tu empresa a otro nivel.</p>
            
            <p style="font-size: 16px;">Para comenzar, por favor confirma tu dirección de correo electrónico haciendo clic en el siguiente botón:</p>
            
            <div style="text-align: center; margin: 40px 0;">
                <a href="{verification_link}" style="background-color: #50C878; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; display: inline-block;">Verificar mi cuenta</a>
            </div>
            
            <p style="font-size: 14px; color: #5A6272;">Si el botón no funciona, copia y pega este enlace en tu navegador web:</p>
            <p style="font-size: 12px; color: #5A6272; word-break: break-all;">{verification_link}</p>
        </body>
    </html>
    """
    
    # 3. Adjuntar el diseño al mensaje
    part = MIMEText(html_content, "html")
    msg.attach(part)

    # 4. Conectar con el servidor SMTP y enviar
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())
        print(f"✅ Correo real enviado exitosamente a {email} (Revisa tu bandeja de Mailtrap)")
    except Exception as e:
        print(f"❌ Error al enviar el correo: {e}")