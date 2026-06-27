/**
 * OMNICORE WELCOME ENGINE
 * Gestiona la pantalla de aterrizaje, login y registro.
 */

const Welcome = {
    state: {
        isLogin: true
    },

    init() {
        this.render();
        this.bindEvents();
    },

    render() {
        const html = `
            <div class="welcome-screen" style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: var(--spacing-lg); text-align: center; min-height: 100vh;">
                <div class="brand-logo" style="font-size: 48px; margin-bottom: var(--spacing-sm); color: var(--color-primary);">${Icons.star}</div>
                <h1 style="margin-bottom: var(--spacing-sm);">OmniCore</h1>
                <p class="text-muted" style="margin-bottom: var(--spacing-lg);">El centro de control industrial para tu negocio.</p>

                <div id="auth-container" style="width: 100%; max-width: 350px;">
                    ${this.state.isLogin ? this.getLoginForm() : this.getRegisterForm()}
                </div>

                <div style="margin-top: var(--spacing-md);">
                    <button id="toggle-auth" class="btn" style="background: none; color: var(--color-primary); font-size: 14px; font-weight: 600;">
                        ${this.state.isLogin ? '¿No tienes cuenta? Regístrate aquí' : '¿Ya tienes cuenta? Inicia sesión'}
                    </button>
                </div>
            </div>
        `;
        UI.render('app-root', html);
    },

    getLoginForm() {
        return `
            <div class="auth-form" style="background: white; padding: var(--spacing-lg); border-radius: var(--radius-lg); border: 1px solid var(--color-border); box-shadow: var(--shadow-md);">
                <h3 style="margin-bottom: var(--spacing-md);">Iniciar Sesión</h3>
                <input type="email" id="auth-email" class="input-field" placeholder="Correo electrónico">
                <input type="password" id="auth-pass" class="input-field" placeholder="Contraseña">
                <button id="auth-submit" class="btn btn-primary" style="width: 100%;">Entrar al Hub</button>
            </div>
        `;
    },

    getRegisterForm() {
        return `
            <div class="auth-form" style="background: white; padding: var(--spacing-lg); border-radius: var(--radius-lg); border: 1px solid var(--color-border); box-shadow: var(--shadow-md);">
                <h3 style="margin-bottom: var(--spacing-md);">Crear Negocio</h3>
                <input type="text" id="reg-biz" class="input-field" placeholder="Nombre del Negocio">
                <input type="email" id="reg-email" class="input-field" placeholder="Correo electrónico">
                <input type="password" id="reg-pass" class="input-field" placeholder="Contraseña">
                <button id="auth-submit" class="btn btn-primary" style="width: 100%;">Registrar Empresa</button>
            </div>
        `;
    },

    bindEvents() {
        const toggleBtn = document.getElementById('toggle-auth');
        if (toggleBtn) {
            toggleBtn.onclick = () => {
                this.state.isLogin = !this.state.isLogin;
                this.render(); // Re-renderiza toda la pantalla para actualizar formularios y textos
                this.bindEvents(); // Re-vincula eventos ya que el DOM cambió
            };
        }

        // Usamos delegación de eventos pero solo una vez por renderizado
        const submitBtn = document.getElementById('auth-submit');
        if (submitBtn) {
            submitBtn.onclick = async () => {
                if (this.state.isLogin) await this.handleLogin();
                else await this.handleRegister();
            };
        }
    },

    async handleLogin() {
        const email = document.getElementById('auth-email')?.value;
        const pass = document.getElementById('auth-pass')?.value;

        if (!email || !pass) return UI.toast('Por favor completa todos los campos', 'error');

        UI.showLoading();
        try {
            const res = await API.login(email, pass);
            Session.saveSession(res.token, res.user);
            UI.toast('Bienvenido a OmniCore', 'success');

            if (window.App) window.App.init();
        } catch (e) {
            UI.toast(e.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async handleRegister() {
        const biz = document.getElementById('reg-biz')?.value;
        const email = document.getElementById('reg-email')?.value;
        const pass = document.getElementById('reg-pass')?.value;

        if (!biz || !email || !pass) return UI.toast('Por favor completa todos los campos', 'error');

        UI.showLoading();
        try {
            const res = await API.register(email, pass, biz);
            Session.saveSession(res.token, res.user);
            UI.toast('Negocio creado exitosamente', 'success');

            if (window.App) window.App.init();
        } catch (e) {
            UI.toast(e.message, 'error');
        } finally {
            UI.hideLoading();
        }
    }
};

window.Welcome = Welcome;
