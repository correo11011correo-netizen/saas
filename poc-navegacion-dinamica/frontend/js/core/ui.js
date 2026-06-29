/**
 * UI Engine
 * Motor de renderizado puro. No toma decisiones, solo dibuja.
 */
const UI = {
    elements: {
        hub: document.getElementById('hub-container'),
        dock: document.getElementById('main-dock'),
        moduleView: document.getElementById('module-container'),
        moduleTitle: document.getElementById('module-title'),
        panelContent: document.getElementById('panel-content'),
        userDisplay: document.getElementById('current-user-display')
    },

    renderUser(user) {
        this.elements.userDisplay.innerText = `${user.name} (${user.role})`;
    },

    renderHub(hubData, onSelect) {
        this.elements.hub.innerHTML = '';
        hubData.forEach(item => {
            const div = document.createElement('div');
            div.className = 'hub-item';
            div.innerHTML = `
                <i data-lucide="${item.icon}"></i>
                <span>${item.label}</span>
            `;
            div.onclick = () => onSelect(item.id);
            this.elements.hub.appendChild(div);
        });
        lucide.createIcons();
    },

    renderDock(dockData, activePanel, onSelect) {
        this.elements.dock.innerHTML = '';
        dockData.forEach(item => {
            const div = document.createElement('div');
            div.className = `dock-item ${item.id === activePanel ? 'active' : ''}`;
            div.innerHTML = `
                <i data-lucide="${item.icon}"></i>
                <span>${item.label}</span>
            `;
            div.onclick = () => onSelect(item.id);
            this.elements.dock.appendChild(div);
        });
        lucide.createIcons();
    },

    showModule(title, panelId) {
        this.elements.hub.classList.add('hidden');
        this.elements.moduleView.classList.remove('hidden');
        this.elements.dock.classList.remove('hidden');
        this.elements.moduleTitle.innerText = title;

        this.elements.panelContent.innerHTML = `
            <div style="background: white; padding: 30px; border-radius: 12px; box-shadow: var(--shadow);">
                <h3>Contenido del Panel: ${panelId}</h3>
                <p>Este panel fue renderizado dinámicamente basándose en la matriz de permisos del servidor.</p>
            </div>
        `;
    },

    hideModule() {
        this.elements.hub.classList.remove('hidden');
        this.elements.moduleView.classList.add('hidden');
        this.elements.dock.classList.add('hidden');
    }
};
