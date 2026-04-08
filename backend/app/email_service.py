import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# CONFIGURACIÓN DE MAILTRAP
SMTP_SERVER = "sandbox.smtp.mailtrap.io"
SMTP_PORT = 2525
SMTP_USERNAME = "74ea577f66db56"
SMTP_PASSWORD = "2a3a1287dd9b16"  # <-- CAMBIAR CUANDO PASES A PRODUCCIÓN
SENDER_EMAIL = "bienvenida@tuplataforma.com"

def send_verification_email(email: str, token: str):
    # El enlace que activará la cuenta en tu backend
    verification_link = f"http://127.0.0.1:8000/verify-email?token={token}"
    
    # 1. Crear la estructura del mensaje
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verifica tu cuenta para comenzar en KROOT"
    msg["From"] = SENDER_EMAIL
    msg["To"] = email

    # 2. Diseñar el cuerpo del correo en HTML (CSS 100% en línea para compatibilidad universal)
    html_content = f"""
    <!doctype html>
    <html lang="es">
      <head>
        <meta charset="utf-8" />
        <meta content="width=device-width, initial-scale=1.0" name="viewport" />
        <title>KROOT - Verificación de Cuenta</title>
        <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
      </head>
      <body style="background-color: #f7f9fb; color: #191c1e; font-family: 'Inter', Arial, sans-serif; margin: 0; padding: 20px; -webkit-font-smoothing: antialiased;">
        
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; margin: 0 auto;">
          <tr>
            <td align="center" style="padding: 32px 0 16px 0;">
              <span style="font-family: 'Manrope', Arial, sans-serif; font-size: 24px; font-weight: 900; letter-spacing: -1px; color: #001736;">KROOT</span>
            </td>
          </tr>
          <tr>
            <td style="background-color: #ffffff; border-radius: 12px; padding: 40px; border: 1px solid #e0e3e5; box-shadow: 0 4px 12px rgba(25,28,30,0.06);">
              
              <div style="background-color: #002b5b; border-radius: 8px; text-align: center; overflow: hidden; margin-bottom: 32px; position: relative; height: 180px;">
                <img src="https://lh3.googleusercontent.com/aida-public/AB6AXuCTxJ1VAzDOwZgzSWrnB_jtRxMsmNM_lz2ytOjOOSDkJ4QSNz4uLq10IDBqAFiZLb327nxq804i03l_SfZlKy4Z64Uw3HUF5g3PBqDbIoZJEQHA0_ZAy8thugeuk0_xt7RR5Vw1AMbETRUIwTGw6PhtyHiFRJ3toBlrYxMmpBagiugHJZoCkDsPLt6D5J--LJoD5aMRs-i_yIHL1kDQA9GY2DjNEByguyelOH2lU20WJmTpeqXapPhDyhiIVNWROBBkiURV65Vv93o" alt="abstract gradient" style="width: 100%; height: 100%; object-fit: cover; opacity: 0.6; display: block;" />
              </div>

              <h1 style="font-family: 'Manrope', Arial, sans-serif; font-size: 32px; font-weight: 700; color: #002b5b; margin-top: 0; margin-bottom: 24px; line-height: 1.2; letter-spacing: -0.5px;">
                ¡Bienvenido a KROOT!
              </h1>

              <p style="font-size: 16px; color: #43474f; line-height: 1.6; margin-bottom: 16px; margin-top: 0;">
                Estamos muy felices de tenerte con nosotros. Has dado el primer paso para llevar el control de tu empresa a otro nivel.
              </p>

              <p style="font-size: 16px; color: #43474f; line-height: 1.6; margin-bottom: 32px; margin-top: 0;">
                Para comenzar, por favor confirma tu dirección de correo electrónico haciendo clic en el siguiente botón.
              </p>

              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="left">
                    <a href="{verification_link}" style="display: inline-block; background-color: #006d36; color: #ffffff; padding: 16px 32px; border-radius: 8px; font-weight: 600; font-size: 16px; text-decoration: none; font-family: 'Inter', Arial, sans-serif; text-align: center;">
                      Verificar mi cuenta &#8594;
                    </a>
                  </td>
                </tr>
              </table>

              <div style="margin-top: 48px; background-color: #f2f4f6; border-radius: 8px; padding: 24px;">
                <p style="font-size: 12px; font-weight: 500; color: #43474f; margin-top: 0; margin-bottom: 12px;">
                  Si el botón no funciona, copia y pega este enlace en tu navegador web:
                </p>
                <div style="background-color: #ffffff; border: 1px solid #e0e3e5; border-radius: 4px; padding: 12px; word-break: break-all;">
                  <a href="{verification_link}" style="font-size: 12px; color: #001736; font-family: monospace; text-decoration: none; opacity: 0.7;">
                    {verification_link}
                  </a>
                </div>
              </div>

            </td>
          </tr>
          
          <tr>
            <td align="center" style="padding: 48px 0;">
              <p style="margin: 0 0 16px 0;">
                <a href="#" style="font-size: 12px; font-weight: 500; color: #64748b; text-decoration: underline; margin: 0 12px;">Privacy Policy</a>
                <a href="#" style="font-size: 12px; font-weight: 500; color: #64748b; text-decoration: underline; margin: 0 12px;">Support</a>
                <a href="#" style="font-size: 12px; font-weight: 500; color: #64748b; text-decoration: underline; margin: 0 12px;">Unsubscribe</a>
              </p>
              <p style="font-size: 12px; font-weight: 500; color: #001736; opacity: 0.6; margin: 0;">
                © 2026 KROOT. All rights reserved.
              </p>
            </td>
          </tr>
        </table>
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