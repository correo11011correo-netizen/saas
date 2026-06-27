from playwright.sync_api import sync_playwright


def deep_audit():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("console", lambda msg: print(f"Browser: {msg.text}"))

        # Mapeo completo de rutas y sus respectivos paneles/dock items esperados
        # Nota: Ajustar según ID de panel real en cada HTML
        site_map = {
            "/stock": [
                {"label": "Inventario", "id": "view-stock"},
                {"label": "Caja", "id": "view-cash"},
                {"label": "Reportes", "id": "view-reports"},
                {"label": "Staff", "id": "view-personnel"},
            ],
            "/whatsapp": [
                {"label": "Chats", "id": "view-chats"},
                {"label": "Bots", "id": "view-bots"},
                {"label": "Flujos", "id": "view-flows"},
                {"label": "Config.", "id": "view-config"},
            ],
            "/mercado-pago": [
                {"label": "Clientes", "id": "section-clients"},
                {"label": "Cobros", "id": "section-payments"},
                {"label": "Global", "id": "section-global_payments"},
                {"label": "Suscrip.", "id": "section-subscriptions"},
            ],
        }

        for path, test_cases in site_map.items():
            print(f"\n--- Auditoría de Módulo: {path} ---")
            page.goto(f"http://localhost:8000{path}")
            page.wait_for_timeout(3000)

            for case in test_cases:
                print(f"  > Probando panel: {case['label']}")
                dock_item = page.query_selector(
                    f'.dock-item[data-label="{case["label"]}"]'
                )
                if not dock_item:
                    print(f"    ❌ Icono '{case['label']}' no encontrado.")
                    continue

                dock_item.click()
                page.wait_for_timeout(1000)

                # Verificar activación (buscando clase 'active' o visibilidad)
                # WhatsApp/MP pueden usar 'hidden' para ocultar, Stock usa 'active' para mostrar
                is_active = page.evaluate(
                    f"document.getElementById('{case['id']}').offsetParent !== null"
                )
                if is_active:
                    print(f"    ✅ Panel '{case['label']}' visible.")
                else:
                    print(f"    ❌ Panel '{case['label']}' NO visible.")

        browser.close()


if __name__ == "__main__":
    deep_audit()
