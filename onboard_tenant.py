import requests
import json
import sys
from getpass import getpass


def clear_screen():
    print("\033[H\033[J")


def print_banner():
    print("=" * 60)
    print("🌟 OMNICORE - ONBOARDING DE NUEVO TENANT 🌟")
    print("=" * 60)


def run_onboarding():
    clear_screen()
    print_banner()

    # 1. Configuración de conexión
    api_base = (
        input("🌐 URL de la API (default: http://localhost:8000): ")
        or "http://localhost:8000"
    )
    domain = input("🌍 Dominio Público para Webhooks (ej: https://api.midominio.com): ")
    if not domain:
        print("⚠️  El dominio es obligatorio para configurar Meta WhatsApp.")
        return

    print("\n--- 👤 Datos de la Cuenta Admin ---")
    email = input("📧 Email: ")
    password = getpass("🔑 Contraseña: ")
    business_name = input("🏢 Nombre del Negocio: ")

    # 2. Registro del Tenant
    print("\n🚀 Registrando negocio en la plataforma...")
    try:
        reg_data = {
            "email": email,
            "password": password,
            "business_name": business_name,
        }
        response = requests.post(f"{api_base}/auth/register", json=reg_data)
        response.raise_for_status()
        res_json = response.json()

        token = res_json["token"]
        tenant_id = res_json["tenant_id"]
        webhook_secret = res_json["webhook_secret"]
        print(f"✅ Tenant creado exitosamente. ID: {tenant_id}")
    except Exception as e:
        print(f"❌ Error en el registro: {e}")
        return

    # 3. Configuración de Credenciales de WhatsApp
    print("\n--- 📱 Integración con Meta WhatsApp ---")
    print(
        "Para que el sistema pueda enviar mensajes, necesitamos el API Token de Meta."
    )
    whatsapp_token = input("🔑 Meta WhatsApp API Token: ")

    if whatsapp_token:
        print("💾 Guardando credenciales...")
        cred_payload = {
            "command": "system.set_credential",
            "params": {
                "service": "whatsapp",
                "api_key": whatsapp_token,
                "secret": None,
                "metadata": json.dumps({"provider": "meta"}),
            },
        }
        try:
            headers = {"Authorization": f"Bearer {token}"}
            cred_res = requests.post(
                f"{api_base}/api/execute", headers=headers, json=cred_payload
            )
            cred_res.raise_for_status()
            print("✅ Credenciales de WhatsApp vinculadas.")
        except Exception as e:
            print(f"⚠️  Error guardando credenciales: {e}")

    # 4. Generación de Hoja de Configuración
    webhook_url = f"{domain}/hooks/{webhook_secret}/whatsapp_message"

    clear_screen()
    print_banner()
    print("\n✨ ¡ONBOARDING COMPLETADO CON ÉXITO! ✨")
    print("\n" + "-" * 60)
    print("📋 HOJA DE CONFIGURACIÓN PARA META (WhatsApp Business)")
    print("-" * 60)
    print(f"🔗 Webhook URL:   {webhook_url}")
    print(f"🔑 Verify Token:  {webhook_secret}")
    print(f"🔑 Access Token:  {whatsapp_token if whatsapp_token else 'No configurado'}")
    print(f"🆔 Tenant ID:     {tenant_id}")
    print("-" * 60)
    print("\n🔐 Credenciales de Acceso al Panel:")
    print(f"📧 Email:         {email}")
    print(f"🔑 Password:      {password}")
    print("-" * 60)
    print(
        "\n👉 Copia la Webhook URL en el panel de Meta Developers -> WhatsApp -> Configuration"
    )
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_onboarding()
    except KeyboardInterrupt:
        print("\n\n👋 Proceso cancelado por el usuario.")
        sys.exit(0)
