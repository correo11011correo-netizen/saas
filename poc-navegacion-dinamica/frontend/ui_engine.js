/**
 * UIEngine
 * Se encarga exclusivamente de dibujar la UI basándose en los datos.
 * No tiene lógica de permisos, solo renderiza lo que recibe.
 */
class UIEngine {
    constructor() {
        this.hubContainer = document.getElementById('hub-container');
        this.dockContainer = document.getElementById('dock-container');
        this.menuContainer = document.getElementById('menu-container');
        this.userStatus = document.getElementById('user-status');
    }

    renderUser(userData) {
        this.userStatus.innerText = `${userData.name} (${userData.role})`;
    }

    renderHub(hubData, onModuleSelect) {
        this.hubContainer.innerHTML = '';
        hubData.forEach(item => {
            const div = document.createElement('div');
            div.className = 'hub-item';
            div.innerHTML = `
                <i data-lucide="${item.icon}"></i>
                <span>${item.label}</span>
            `;
            div.onclick = () => onModuleSelect(item.id);
            this.hubContainer.appendChild(div);
        });
        lucide.createIcons();
    }

    renderDock(dockData, activePanel, onPanelSelect) {
        this.dockContainer.innerHTML = '';
        dockData.forEach(item => {
            const div = document.createElement('div');
            div.className = `dock-item ${item.id === activePanel ? 'active' : ''}`;
            div.innerHTML = `
                <i data-lucide="${item.icon}" style="width:16px; height:16px;"></i>
                <span>${item.label}</span>
            `;
            div.onclick = () => onPanelSelect(item.id);
            this.dockContainer.appendChild(div);
        });
        lucide.createIcons();
    }

    renderMenu(menuData, onMenuItemSelect) {
        this.menuContainer.innerHTML = '';
        menuData.forEach(item => {
            const btn = document.createElement('button');
            btn.className = 'menu-btn';
            btn.innerHTML = `<i data-lucide="${item.icon}" style="width:16px; height:16px;"></i> ${item.label}`;
            btn.onclick = () => onMenuItemSelect(item.id);
            this.menuContainer.appendChild(btn);
        });
        lucide.createIcons();
    }
}

const ui = new UIEngine();
