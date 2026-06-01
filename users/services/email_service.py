from django.core.mail import EmailMultiAlternatives
from django.conf import settings


def _obfuscate_email(email: str) -> str:
    local, domain = email.split('@', 1)
    visible = local[:2] if len(local) >= 2 else local
    return f"{visible}****@{domain}"


def send_verification_email(user_email: str, username: str, token_uuid: str) -> None:
    verification_url = f"{settings.BACKEND_BASE_URL}/users/verify-email/{token_uuid}/"
    obfuscated = _obfuscate_email(user_email)

    subject = "Verificá tu cuenta en QueVesVe!&"

    text_body = (
        f"Hola @{username},\n\n"
        f"Verificá tu email en QueVesVe!&\n"
        f"{'─' * 40}\n\n"
        f"Para confirmar tu cuenta, ingresá al siguiente enlace:\n\n"
        f"{verification_url}\n\n"
        f"El enlace expira en 24 horas.\n\n"
        f"{'─' * 40}\n"
        f"Información de seguridad:\n"
        f"• Este email fue enviado a {obfuscated}\n"
        f"• QueVesVe!& nunca te pedirá tu contraseña por email\n"
        f"• Si no creaste una cuenta, ignorá este mensaje\n\n"
        f"© 2025 QueVesVe!&"
    )

    html_body = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Verificá tu cuenta en QueVesVe!&amp;</title>
</head>
<body style="margin:0;padding:0;background-color:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f5f5f5;padding:40px 16px;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="background-color:#F5A623;padding:28px 40px;text-align:center;">
              <h1 style="margin:0;color:#ffffff;font-size:26px;font-weight:700;letter-spacing:-0.5px;">QueVesVe!&amp;</h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px 40px 32px;">
              <p style="margin:0 0 6px;color:#111111;font-size:20px;font-weight:600;">Hola, @{username}</p>
              <p style="margin:0 0 28px;color:#555555;font-size:15px;line-height:1.6;">
                Para confirmar que este email te pertenece y activar la verificación de tu cuenta, hacé clic en el botón de abajo.
              </p>

              <!-- CTA -->
              <table cellpadding="0" cellspacing="0" style="margin:0 0 12px;">
                <tr>
                  <td style="background-color:#F5A623;border-radius:6px;">
                    <a href="{verification_url}"
                       style="display:inline-block;padding:14px 32px;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;letter-spacing:0.2px;">
                      Verificar mi cuenta
                    </a>
                  </td>
                </tr>
              </table>
              <p style="margin:0 0 28px;color:#888888;font-size:12px;word-break:break-all;">
                O copiá este enlace en tu navegador:
                <br><span style="color:#F5A623;">{verification_url}</span>
              </p>

              <p style="margin:0;color:#888888;font-size:13px;line-height:1.6;">
                Este enlace expira en <strong>24 horas</strong>. Si no lo usás, podés pedir uno nuevo desde tu perfil en la app.
              </p>
            </td>
          </tr>

          <!-- Security -->
          <tr>
            <td style="padding:24px 40px;background-color:#FFF8ED;border-top:1px solid #FFE5B4;">
              <p style="margin:0 0 10px;color:#b45309;font-size:13px;font-weight:600;">Información de seguridad</p>
              <ul style="margin:0;padding:0 0 0 18px;color:#555555;font-size:13px;line-height:1.8;">
                <li>Este email fue enviado a <strong>{obfuscated}</strong></li>
                <li>QueVesVe!&amp; <strong>nunca te pedirá tu contraseña</strong> por email ni por otro medio</li>
                <li>Si no creaste una cuenta, ignorá este mensaje &mdash; no pasará nada</li>
              </ul>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:20px 40px;border-top:1px solid #eeeeee;text-align:center;">
              <p style="margin:0 0 4px;color:#aaaaaa;font-size:12px;">
                &copy; 2025 QueVesVe!&amp;
                &nbsp;&middot;&nbsp;
                <a href="mailto:soporte@quevesve.app" style="color:#F5A623;text-decoration:none;">Soporte</a>
              </p>
              <p style="margin:0;color:#bbbbbb;font-size:11px;">
                Email generado automáticamente &mdash; por favor no respondas a este mensaje.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user_email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=True)
