/**
 * CivicTriage — Web Client Application Logic
 * Vanilla JavaScript implementation providing state management, REST API integration,
 * dynamic view routing, real-time feedback, and accessible UI controls.
 */

class CivicTriageApp {
    constructor() {
        this.state = {
            user: null,
            token: localStorage.getItem('civictriage_token') || null,
            theme: localStorage.getItem('civictriage_theme') || 'dark',
            activeTab: 'auth',
            citizenSubtab: 'submit',
            authTab: 'login',
            wards: [],
            officerItems: [],
            activeModalGrievanceId: null,
            healthCheckTimer: null
        };

        this.applyTheme(this.state.theme);
        this.init();
    }

    applyTheme(theme) {
        this.state.theme = theme;
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('civictriage_theme', theme);
        const btn = document.getElementById('btn-theme-toggle');
        if (btn) {
            btn.textContent = theme === 'dark' ? '☀️' : '🌙';
            btn.title = theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode';
        }
    }

    toggleTheme() {
        const nextTheme = this.state.theme === 'dark' ? 'light' : 'dark';
        this.applyTheme(nextTheme);
    }

    async init() {
        this.applyTheme(this.state.theme);
        this.initWards();
        this.startHealthMonitor();
        this.initCivicBackground();
        this.startRealtimeSync();

        // Close profile dropdown when clicking outside
        document.addEventListener('click', (e) => {
            const wrapper = document.getElementById('user-profile-wrapper');
            if (wrapper && !wrapper.contains(e.target)) {
                this.closeProfileDropdown();
            }
        });

        if (this.state.token) {
            await this.verifyCurrentSession();
        } else {
            this.showTab('auth');
        }
    }

    // -----------------------------------------------------------------------
    // Dynamic Civic Smart-City Canvas Background
    // -----------------------------------------------------------------------
    initCivicBackground() {
        const canvas = document.getElementById('civic-bg-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        let width = (canvas.width = window.innerWidth);
        let height = (canvas.height = window.innerHeight);

        window.addEventListener('resize', () => {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
            initNodes();
        });

        let nodes = [];
        const nodeCount = Math.min(48, Math.max(22, Math.floor((width * height) / 32000)));
        const colors = ['#38bdf8', '#818cf8', '#34d399', '#f59e0b'];

        function initNodes() {
            nodes = [];
            for (let i = 0; i < nodeCount; i++) {
                nodes.push({
                    x: Math.random() * width,
                    y: Math.random() * height,
                    vx: (Math.random() - 0.5) * 0.42,
                    vy: (Math.random() - 0.5) * 0.42,
                    radius: Math.random() * 2.2 + 1.2,
                    color: colors[Math.floor(Math.random() * colors.length)],
                    pulse: Math.random() * Math.PI,
                    pulseSpeed: 0.02 + Math.random() * 0.03
                });
            }
        }

        let mouse = { x: -1000, y: -1000 };
        window.addEventListener('mousemove', (e) => {
            mouse.x = e.clientX;
            mouse.y = e.clientY;
        });

        let packets = [];
        function spawnPacket(n1, n2) {
            if (packets.length > 16) return;
            packets.push({
                x1: n1.x, y1: n1.y,
                x2: n2.x, y2: n2.y,
                progress: 0,
                speed: 0.012 + Math.random() * 0.015,
                color: n1.color
            });
        }

        initNodes();
        let lastPacketTime = 0;

        function render(time) {
            ctx.clearRect(0, 0, width, height);

            for (let i = 0; i < nodes.length; i++) {
                const n = nodes[i];
                n.x += n.vx;
                n.y += n.vy;

                if (n.x < 0 || n.x > width) n.vx *= -1;
                if (n.y < 0 || n.y > height) n.vy *= -1;

                const dx = mouse.x - n.x;
                const dy = mouse.y - n.y;
                const dist = Math.hypot(dx, dy);
                if (dist < 130) {
                    n.x -= (dx / dist) * 0.7;
                    n.y -= (dy / dist) * 0.7;
                }

                n.pulse += n.pulseSpeed;
                const currentRadius = n.radius + Math.sin(n.pulse) * 0.6;

                ctx.beginPath();
                ctx.arc(n.x, n.y, currentRadius * 2.2, 0, Math.PI * 2);
                ctx.fillStyle = n.color === '#38bdf8' ? 'rgba(56, 189, 248, 0.15)' : 'rgba(99, 102, 241, 0.12)';
                ctx.fill();

                ctx.beginPath();
                ctx.arc(n.x, n.y, Math.max(0.5, currentRadius), 0, Math.PI * 2);
                ctx.fillStyle = n.color;
                ctx.fill();

                for (let j = i + 1; j < nodes.length; j++) {
                    const n2 = nodes[j];
                    const d = Math.hypot(n.x - n2.x, n.y - n2.y);
                    if (d < 160) {
                        const alpha = (1 - d / 160) * 0.22;
                        ctx.strokeStyle = `rgba(56, 189, 248, ${alpha})`;
                        ctx.lineWidth = 0.85;
                        ctx.beginPath();
                        ctx.moveTo(n.x, n.y);
                        ctx.lineTo(n2.x, n2.y);
                        ctx.stroke();

                        if (time - lastPacketTime > 600 && Math.random() < 0.08) {
                            spawnPacket(n, n2);
                            lastPacketTime = time;
                        }
                    }
                }
            }

            for (let p = packets.length - 1; p >= 0; p--) {
                const pkt = packets[p];
                pkt.progress += pkt.speed;
                if (pkt.progress >= 1) {
                    packets.splice(p, 1);
                    continue;
                }
                const px = pkt.x1 + (pkt.x2 - pkt.x1) * pkt.progress;
                const py = pkt.y1 + (pkt.y2 - pkt.y1) * pkt.progress;

                ctx.beginPath();
                ctx.arc(px, py, 2.5, 0, Math.PI * 2);
                ctx.fillStyle = pkt.color;
                ctx.fill();
            }

            requestAnimationFrame(render);
        }

        requestAnimationFrame(render);
    }

    // -----------------------------------------------------------------------
    // Real-Time Data Sync Loop (3.5s Interval)
    // -----------------------------------------------------------------------
    startRealtimeSync() {
        if (this.state.syncTimer) clearInterval(this.state.syncTimer);
        this.state.syncTimer = setInterval(() => {
            if (this.state.activeTab === 'officer') {
                this.loadOfficerQueue(true);
            } else if (this.state.activeTab === 'citizen' && this.state.citizenSubtab === 'history') {
                this.loadCitizenGrievances(true);
            }
        }, 3500);
    }

    // -----------------------------------------------------------------------
    // API Request Utility
    // -----------------------------------------------------------------------
    async apiRequest(endpoint, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        };

        if (this.state.token) {
            headers['Authorization'] = `Bearer ${this.state.token}`;
        }

        try {
            const res = await fetch(endpoint, {
                ...options,
                headers
            });

            if (res.status === 401) {
                if (this.state.user) {
                    this.showToast('Session expired. Please sign in again.', 'error');
                }
                this.logout(false);
                return null;
            }

            const data = await res.json().catch(() => null);

            if (!res.ok) {
                const errMsg = (data && data.detail) || (data && data.message) || `Error: ${res.statusText}`;
                throw new Error(errMsg);
            }

            return data;
        } catch (err) {
            console.error(`API Error on ${endpoint}:`, err);
            throw err;
        }
    }

    // -----------------------------------------------------------------------
    // Ollama Engine Health Monitor
    // -----------------------------------------------------------------------
    async checkSystemHealth() {
        const sideStatus = document.getElementById('sidebar-system-status');
        const sideText = document.getElementById('sidebar-engine-status-text');
        const sideDot = document.getElementById('sidebar-engine-dot');

        try {
            const res = await fetch('/api/system/health');
            if (res.ok) {
                const data = await res.json();
                if (data.ollama_online) {
                    if (sideStatus) sideStatus.className = 'sidebar-system-status';
                    if (sideText) sideText.textContent = `Ollama Online (${data.model || 'llama3.2:3b'})`;
                    if (sideDot) sideDot.style.background = '#10b981';
                } else {
                    if (sideStatus) sideStatus.className = 'sidebar-system-status offline';
                    if (sideText) sideText.textContent = `Ollama Offline (Review Mode)`;
                    if (sideDot) sideDot.style.background = '#f59e0b';
                }
            }
        } catch (e) {
            if (sideStatus) sideStatus.className = 'sidebar-system-status offline';
            if (sideText) sideText.textContent = `Ollama Offline`;
            if (sideDot) sideDot.style.background = '#f59e0b';
        }
    }

    startHealthMonitor() {
        this.checkSystemHealth();
        if (this.state.healthCheckTimer) clearInterval(this.state.healthCheckTimer);
        this.state.healthCheckTimer = setInterval(() => this.checkSystemHealth(), 15000);
    }

    // -----------------------------------------------------------------------
    // Ward Loader
    // -----------------------------------------------------------------------
    async initWards() {
        try {
            const res = await fetch('/api/wards');
            if (res.ok) {
                const data = await res.json();
                this.state.wards = data.wards || [];
                this.renderWardDropdowns();
            }
        } catch (e) {
            console.error('Failed to load wards', e);
        }
    }

    renderWardDropdowns() {
        // Citizen submission select
        const submitSelect = document.getElementById('grievance-ward');
        if (submitSelect) {
            submitSelect.innerHTML = '';
            this.state.wards.forEach(w => {
                const opt = document.createElement('option');
                opt.value = w;
                opt.textContent = w;
                submitSelect.appendChild(opt);
            });
            const otherOpt = document.createElement('option');
            otherOpt.value = 'Other / Unspecified';
            otherOpt.textContent = 'Other / Unspecified';
            submitSelect.appendChild(otherOpt);
        }

        // Officer filter select
        const filterSelect = document.getElementById('filter-ward');
        if (filterSelect) {
            filterSelect.innerHTML = '<option value="All">All Wards</option>';
            this.state.wards.forEach(w => {
                const opt = document.createElement('option');
                opt.value = w;
                opt.textContent = w;
                filterSelect.appendChild(opt);
            });
        }
    }

    handleWardChange(val) {
        const customGroup = document.getElementById('custom-ward-group');
        if (val === 'Other / Unspecified') {
            customGroup.style.display = 'block';
            document.getElementById('grievance-custom-ward').required = true;
        } else {
            customGroup.style.display = 'none';
            document.getElementById('grievance-custom-ward').required = false;
        }
    }

    // -----------------------------------------------------------------------
    // Authentication & Session
    // -----------------------------------------------------------------------
    async verifyCurrentSession() {
        try {
            const res = await this.apiRequest('/api/auth/me');
            if (res && res.success && res.user) {
                this.setUser(res.user);
                this.navigateHome();
            } else {
                this.logout(false);
            }
        } catch (e) {
            this.logout(false);
        }
    }

    setUser(user) {
        this.state.user = user;
        const appLayout = document.getElementById('app-layout');
        const authView = document.getElementById('view-auth');

        if (user) {
            if (authView) authView.style.display = 'none';
            if (appLayout) appLayout.style.display = 'flex';

            const isAdmin = user.role === 'admin' || user.role === 'officer' || (user.email && user.email.toLowerCase().includes('officer')) || (user.email && user.email.toLowerCase().includes('admin'));
            const roleLabel = user.role === 'citizen' ? 'Citizen' : 'Officer';
            const roleClass = user.role === 'citizen' ? 'citizen' : 'officer';
            const avatarChar = user.role === 'citizen' ? '👤' : '👮';

            // Populate Left Sidebar User Profile Card (Screen 2)
            const sideName = document.getElementById('sidebar-user-name');
            if (sideName) sideName.textContent = user.name;
            const sideEmail = document.getElementById('sidebar-user-email');
            if (sideEmail) sideEmail.textContent = user.email;
            const sideAvatar = document.getElementById('sidebar-user-avatar');
            if (sideAvatar) sideAvatar.textContent = avatarChar;
            const sideBadge = document.getElementById('sidebar-role-badge');
            if (sideBadge) {
                sideBadge.textContent = roleLabel;
                sideBadge.className = `role-badge ${roleClass}`;
            }

            // Role-based Navigation Item Visibility
            const sideNavCitizen = document.getElementById('side-nav-citizen');
            const sideNavOfficer = document.getElementById('side-nav-officer');

            if (user.role === 'citizen') {
                if (sideNavCitizen) sideNavCitizen.style.display = 'flex';
                if (sideNavOfficer) sideNavOfficer.style.display = 'none';
                const greeting = document.getElementById('citizen-greeting-text');
                if (greeting) greeting.textContent = `Welcome, ${user.name} (${user.email})`;
            } else {
                if (sideNavCitizen) sideNavCitizen.style.display = 'none';
                if (sideNavOfficer) sideNavOfficer.style.display = 'flex';
                const greeting = document.getElementById('officer-greeting-text');
                if (greeting) greeting.textContent = `Logged in: ${user.name} (${user.email})`;
            }
        } else {
            if (appLayout) appLayout.style.display = 'none';
            if (authView) authView.style.display = 'flex';
        }
    }

    togglePasswordVisibility(inputId, btnId) {
        const input = document.getElementById(inputId);
        const btn = document.getElementById(btnId);
        if (!input) return;
        if (input.type === 'password') {
            input.type = 'text';
            if (btn) btn.textContent = '🙈';
        } else {
            input.type = 'password';
            if (btn) btn.textContent = '👁️';
        }
    }

    async quickDemoLogin(role) {
        const emailInput = document.getElementById('login-email');
        const passInput = document.getElementById('login-password');
        let email = 'citizen@example.com';
        let pass = 'Citizen123';

        if (role === 'officer' || role === 'admin') {
            email = 'officer@civictriage.gov.in';
            pass = 'Officer123';
        }

        if (emailInput) emailInput.value = email;
        if (passInput) passInput.value = pass;
        this.showToast(`Authenticating 1-click ${role} credentials...`, 'info');
        await this.executeLogin(email, pass);
    }

    setUserPreferredLanguage(langCode) {
        this.state.preferredLang = langCode;
        localStorage.setItem('civictriage_lang', langCode);
        const labelMap = { en: 'English', hi: 'हिन्दी (Hindi)', te: 'తెలుగు (Telugu)' };
        const label = labelMap[langCode] || 'English';

        // Update pills active state
        ['en', 'hi', 'te'].forEach(c => {
            const pill = document.getElementById(`lang-pill-${c}`);
            if (pill) pill.classList.toggle('active', c === langCode);
        });

        const prefSelect = document.getElementById('prof-pref-lang');
        if (prefSelect) prefSelect.value = langCode;
        this.showToast(`Language set to ${label}`, 'info');
    }

    // -----------------------------------------------------------------------
    // Profile Dropdown & Modal Actions
    // -----------------------------------------------------------------------
    toggleProfileDropdown() {
        const dropdown = document.getElementById('user-profile-dropdown');
        const wrapper = document.getElementById('user-profile-wrapper');
        if (!dropdown || !wrapper) return;

        const isVisible = dropdown.style.display === 'block';
        if (isVisible) {
            dropdown.style.display = 'none';
            wrapper.classList.remove('open');
        } else {
            dropdown.style.display = 'block';
            wrapper.classList.add('open');
        }
    }

    closeProfileDropdown() {
        const dropdown = document.getElementById('user-profile-dropdown');
        const wrapper = document.getElementById('user-profile-wrapper');
        if (dropdown) dropdown.style.display = 'none';
        if (wrapper) wrapper.classList.remove('open');
    }

    openProfileModal() {
        this.closeProfileDropdown();
        const modal = document.getElementById('user-profile-modal');
        if (!modal) return;

        const user = this.state.user;
        if (user) {
            const isAdmin = user.role === 'admin' || (user.email && user.email.toLowerCase().includes('admin'));
            const roleLabel = isAdmin ? 'Administrator' : user.role === 'citizen' ? 'Citizen' : 'Municipal Officer';
            const roleClass = isAdmin ? 'admin' : user.role;
            const avatarChar = isAdmin ? '🏛️' : user.role === 'citizen' ? '👤' : '👮';

            document.getElementById('prof-modal-name').textContent = user.name;
            document.getElementById('prof-modal-email').textContent = user.email;
            document.getElementById('prof-modal-avatar').textContent = avatarChar;
            const profRole = document.getElementById('prof-modal-role');
            profRole.textContent = roleLabel;
            profRole.className = `role-badge ${roleClass}`;
            document.getElementById('prof-modal-ward').textContent = user.role === 'citizen' ? 'Ward 12 (Indiranagar)' : 'All Municipal Wards';
        }

        modal.style.display = 'flex';
    }

    closeProfileModal() {
        const modal = document.getElementById('user-profile-modal');
        if (modal) modal.style.display = 'none';
    }

    closeProfileModalOutside(e) {
        if (e.target && e.target.id === 'user-profile-modal') {
            this.closeProfileModal();
        }
    }

    switchAuthTab(tab) {
        this.state.authTab = tab;
        const loginContent = document.getElementById('tab-login-content');
        const registerContent = document.getElementById('tab-register-content');
        const btnSignIn = document.getElementById('tab-btn-signin');
        const btnRegister = document.getElementById('tab-btn-register');

        if (tab === 'login') {
            if (loginContent) loginContent.style.display = 'block';
            if (registerContent) registerContent.style.display = 'none';
            if (btnSignIn) btnSignIn.classList.add('active');
            if (btnRegister) btnRegister.classList.remove('active');
        } else {
            if (registerContent) registerContent.style.display = 'block';
            if (loginContent) loginContent.style.display = 'none';
            if (btnRegister) btnRegister.classList.add('active');
            if (btnSignIn) btnSignIn.classList.remove('active');
        }
    }

    async handleLogin(e) {
        if (e) e.preventDefault();
        const email = document.getElementById('login-email').value.trim();
        const password = document.getElementById('login-password').value;
        await this.executeLogin(email, password);
    }

    async executeLogin(email, password) {
        const btn = document.getElementById('btn-submit-login');
        const originalText = btn ? btn.innerHTML : 'Sign In to Portal';

        try {
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span>Signing in...</span>';
            }

            const res = await this.apiRequest('/api/auth/login', {
                method: 'POST',
                body: JSON.stringify({ email, password })
            });

            if (res && res.success) {
                this.state.token = res.token;
                localStorage.setItem('civictriage_token', res.token);
                this.setUser(res.user);
                this.showToast(`Welcome back, ${res.user.name}!`, 'success');
                this.navigateHome();
            }
        } catch (err) {
            this.showToast(err.message || 'Login failed. Check your credentials.', 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        }
    }

    async handleRegister(e) {
        e.preventDefault();
        const btn = document.getElementById('btn-submit-register');
        const originalText = btn.innerHTML;

        const name = document.getElementById('reg-name').value.trim();
        const email = document.getElementById('reg-email').value.trim();
        const password = document.getElementById('reg-password').value;

        try {
            btn.disabled = true;
            btn.innerHTML = '<span>Creating account...</span>';

            const res = await this.apiRequest('/api/auth/register', {
                method: 'POST',
                body: JSON.stringify({ name, email, password })
            });

            if (res && res.success) {
                this.showToast('Registration successful! Please sign in with your password.', 'success');
                this.switchAuthTab('login');
                document.getElementById('login-email').value = email;
                document.getElementById('login-password').value = '';
                document.getElementById('reg-name').value = '';
                document.getElementById('reg-email').value = '';
                document.getElementById('reg-password').value = '';
            }
        } catch (err) {
            this.showToast(err.message || 'Registration failed.', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }

    async logout(notify = true) {
        try {
            await fetch('/api/auth/logout', { method: 'POST' });
        } catch (e) {
            // ignore
        }

        this.state.user = null;
        this.state.token = null;
        localStorage.removeItem('civictriage_token');
        this.setUser(null);
        this.showTab('auth');
        if (notify) this.showToast('Signed out successfully.', 'info');
    }

    navigateHome() {
        if (!this.state.user) {
            this.showTab('auth');
        } else if (this.state.user.role === 'citizen') {
            this.showTab('citizen');
        } else if (this.state.user.role === 'officer') {
            this.showTab('officer');
        } else {
            this.showTab('insights');
        }
    }

    // -----------------------------------------------------------------------
    // Main View Switching
    // -----------------------------------------------------------------------
    showTab(tabName) {
        if (!this.state.user && tabName !== 'auth') {
            tabName = 'auth';
        }

        this.state.activeTab = tabName;

        const authView = document.getElementById('view-auth');
        const appLayout = document.getElementById('app-layout');

        if (tabName === 'auth') {
            if (authView) authView.style.display = 'flex';
            if (appLayout) appLayout.style.display = 'none';
            document.body.classList.add('auth-view-active');
            return;
        } else {
            if (authView) authView.style.display = 'none';
            if (appLayout) appLayout.style.display = 'flex';
            document.body.classList.remove('auth-view-active');
        }

        const sections = ['citizen', 'officer', 'insights'];
        sections.forEach(s => {
            const el = document.getElementById(`view-${s}`);
            if (el) el.style.display = s === tabName ? 'block' : 'none';
        });

        // Update sidebar nav radio indicators
        const navBtns = {
            citizen: document.getElementById('side-nav-citizen'),
            officer: document.getElementById('side-nav-officer'),
            insights: document.getElementById('side-nav-insights')
        };

        Object.keys(navBtns).forEach(k => {
            if (navBtns[k]) {
                if (k === tabName) navBtns[k].classList.add('active');
                else navBtns[k].classList.remove('active');
            }
        });

        // Trigger view-specific loads
        if (tabName === 'citizen') {
            if (this.state.citizenSubtab === 'history') {
                this.loadCitizenGrievances();
            }
        } else if (tabName === 'officer') {
            this.loadOfficerQueue();
        } else if (tabName === 'insights') {
            this.loadInsights();
        }
    }

    // -----------------------------------------------------------------------
    // Citizen Portal Functions
    // -----------------------------------------------------------------------
    switchCitizenSubtab(subtab) {
        this.state.citizenSubtab = subtab;
        const btnSubmit = document.getElementById('subtab-submit-btn');
        const btnHistory = document.getElementById('subtab-history-btn');
        const contentSubmit = document.getElementById('citizen-subcontent-submit');
        const contentHistory = document.getElementById('citizen-subcontent-history');

        if (subtab === 'submit') {
            btnSubmit.classList.add('active');
            btnHistory.classList.remove('active');
            contentSubmit.style.display = 'block';
            contentHistory.style.display = 'none';
        } else {
            btnHistory.classList.add('active');
            btnSubmit.classList.remove('active');
            contentHistory.style.display = 'block';
            contentSubmit.style.display = 'none';
            this.loadCitizenGrievances();
        }
    }

    loadSample(sampleKey) {
        const textarea = document.getElementById('grievance-text');
        const wardSelect = document.getElementById('grievance-ward');

        if (sampleKey === 'live_wire') {
            wardSelect.value = 'Ward 10';
            textarea.value = 'An electric wire snapped and fell into a puddle right outside the primary school gate. Sparks are flying everywhere!';
        } else if (sampleKey === 'water_hi') {
            wardSelect.value = 'Ward 4';
            textarea.value = 'हमारे इलाके में पिछले चार दिनों से पीने का पानी नहीं आया है। पानी के बिना खाना बनाना भी दूभर हो गया है।';
        } else if (sampleKey === 'manhole_te') {
            wardSelect.value = 'Ward 2';
            textarea.value = 'మెయిన్ రోడ్డుపై డ్రైనేజ్ మ్యాన్‌హోల్ మూత పూర్తిగా విరిగిపోయి తెరిచి ఉంది. రాత్రి సమయంలో ఎవరైనా పడిపోతే ప్రాణాలు పోతాయి!';
        }

        this.handleWardChange(wardSelect.value);
        this.updateCharCount(textarea.value);
        this.showToast('Sample loaded into form! Ready to submit.', 'info');
    }

    updateCharCount(val) {
        const len = (val || '').length;
        document.getElementById('grievance-char-count').textContent = `${len} character${len === 1 ? '' : 's'}`;
    }

    async handleGrievanceSubmit(e) {
        e.preventDefault();
        const btn = document.getElementById('btn-submit-grievance');
        const originalText = btn.textContent;

        const wardSelect = document.getElementById('grievance-ward');
        const customWardInput = document.getElementById('grievance-custom-ward');
        const textarea = document.getElementById('grievance-text');

        let ward = wardSelect.value;
        if (ward === 'Other / Unspecified') {
            ward = customWardInput.value.trim();
            if (!ward) {
                this.showToast('Please specify your locality/ward.', 'error');
                return;
            }
        }

        const text = textarea.value.trim();
        if (text.length < 5) {
            this.showToast('Please describe the grievance with at least 5 characters.', 'error');
            return;
        }

        try {
            btn.disabled = true;
            btn.textContent = 'Registering Grievance...';

            const res = await this.apiRequest('/api/grievances', {
                method: 'POST',
                body: JSON.stringify({ ward, text })
            });

            if (res && res.success) {
                this.showToast(`✅ Grievance #${res.grievance_id} registered immediately! Automated triage running.`, 'success');
                textarea.value = '';
                this.updateCharCount('');

                // Display Instant Triage Receipt Card in Submit View
                const resultBox = document.getElementById('grievance-submission-result');
                if (resultBox) {
                    resultBox.style.display = 'block';
                    const priorityClass = res.priority === 'Immediate' || res.priority === 'High' ? 'urgent' : res.priority === 'Soon' || res.priority === 'Medium' ? 'soon' : 'routine';
                    resultBox.innerHTML = `
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.65rem;">
                            <span style="font-weight: 700; color: #f8fafc; font-size: 1rem;">✅ Grievance #${res.grievance_id} Successfully Filed</span>
                            <span class="role-badge ${priorityClass}" style="font-size: 0.8rem; padding: 3px 10px;">${res.priority || 'Immediate'} Priority</span>
                        </div>
                        <div style="color: #cbd5e1; font-size: 0.88rem; line-height: 1.5; margin-bottom: 0.5rem;">
                            <strong>Category:</strong> ${res.category || 'General'} • <strong>Ward:</strong> ${res.ward || ward} • <strong>Language:</strong> ${(res.detected_language || 'en').toUpperCase()}
                        </div>
                        <div style="color: #94a3b8; font-size: 0.85rem; background: rgba(0,0,0,0.25); padding: 0.65rem 0.85rem; border-radius: 6px; border-left: 3px solid #38bdf8;">
                            <strong>AI Summary:</strong> ${res.english_summary || 'Grievance intake logged into triage queue.'}<br>
                            <small style="color: #64748b; margin-top: 4px; display: block;">${res.reason || 'Escalation safety check applied.'}</small>
                        </div>
                    `;
                }

                // Silently refresh history records
                this.loadCitizenGrievances(true);
            }
        } catch (err) {
            this.showToast(err.message || 'Submission failed.', 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }

    async loadCitizenGrievances(silent = false) {
        const container = document.getElementById('citizen-grievances-container');
        const countBadge = document.getElementById('citizen-count-badge');
        if (!silent) {
            container.innerHTML = '<p style="padding: 1rem; color: #64748b;">Loading your grievances...</p>';
        }

        try {
            const res = await this.apiRequest('/api/citizen/grievances');
            if (!res || !res.grievances) return;

            const items = res.grievances;
            countBadge.textContent = items.length;

            if (items.length === 0) {
                container.innerHTML = `
                    <div style="background: #ffffff; border: 1px dashed #cbd5e1; border-radius: 10px; padding: 2.5rem; text-align: center;">
                        <span style="font-size: 2rem;">📝</span>
                        <h3 style="font-size: 1.1rem; color: #0f172a; margin: 0.5rem 0 0.25rem 0;">No grievances filed yet</h3>
                        <p style="color: #64748b; font-size: 0.88rem;">Submit your first civic issue using the submit tab above.</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = items.map(g => this.renderCitizenGrievanceCard(g)).join('');
        } catch (err) {
            container.innerHTML = `<p style="padding: 1rem; color: #b91c1c;">Error loading grievances: ${err.message}</p>`;
        }
    }

    renderCitizenGrievanceCard(g) {
        const rawPri = g.priority || 'Unassigned';
        const pri = (rawPri === 'Immediate' || rawPri === 'High') ? 'High' : (rawPri === 'Soon' || rawPri === 'Medium') ? 'Medium' : (rawPri === 'Routine' || rawPri === 'Low') ? 'Low' : rawPri;
        const priClass = pri === 'High' ? 'pri-high' : pri === 'Medium' ? 'pri-medium' : pri === 'Low' ? 'pri-low' : 'pri-unassigned';
        const borderClass = pri === 'High' ? 'border-high' : pri === 'Medium' ? 'border-medium' : pri === 'Low' ? 'border-low' : '';

        const st = g.status || 'Received';
        const stClass = st === 'Received' ? 'status-received' : st === 'In Progress' ? 'status-inprogress' : st === 'Resolved' ? 'status-resolved' : 'status-review';

        const cat = g.category || 'Unassigned';
        const lang = (g.detected_language || 'en').toUpperCase();
        const dateStr = g.created_at ? new Date(g.created_at).toLocaleString() : '';

        return `
            <div class="grievance-item-card ${borderClass}">
                <div class="grievance-card-top">
                    <div class="grievance-pills-row">
                        <span class="grievance-id-tag">#${g.id}</span>
                        <span class="pri-pill ${priClass}">${pri}</span>
                        <span class="status-pill ${stClass}">${st}</span>
                        <span class="cat-pill">${cat}</span>
                        <span class="grievance-ward-tag">📍 ${this.escapeHtml(g.ward || 'Unspecified')}</span>
                        <span class="cat-pill">🗣️ ${lang}</span>
                    </div>
                    <span class="grievance-date-tag">🕒 ${dateStr}</span>
                </div>

                <div class="grievance-original-box">
                    "${this.escapeHtml(g.original_text)}"
                </div>

                ${g.english_summary ? `
                    <div class="grievance-summary-box">
                        <b>English Summary:</b> ${this.escapeHtml(g.english_summary)}
                    </div>
                ` : ''}

                ${g.reason ? `
                    <div class="grievance-reason-box">
                        <b>Triage Logic:</b> ${this.escapeHtml(g.reason)}
                    </div>
                ` : ''}

                ${g.latest_note ? `
                    <div class="citizen-note-banner">
                        <b>👮 Officer Update:</b> "${this.escapeHtml(g.latest_note)}" 
                        <span style="font-size: 0.72rem; color: #166534; margin-left: 6px;">(${new Date(g.latest_note_at).toLocaleString()})</span>
                    </div>
                ` : ''}
            </div>
        `;
    }

    // -----------------------------------------------------------------------
    // Officer Queue Functions
    // -----------------------------------------------------------------------
    async loadOfficerQueue(silent = false) {
        const tbody = document.getElementById('officer-queue-tbody');
        if (!silent) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 2rem; color: #64748b;">Loading triage queue...</td></tr>';
        }

        const priority = document.getElementById('filter-priority').value;
        const category = document.getElementById('filter-category').value;
        const ward = document.getElementById('filter-ward').value;
        const status = document.getElementById('filter-status').value;

        const queryParams = new URLSearchParams({ priority, category, ward, status });

        try {
            const res = await this.apiRequest(`/api/officer/queue?${queryParams.toString()}`);
            if (!res || !res.items) return;

            // Update KPI cards
            const m = res.metrics;
            document.getElementById('kpi-total-val').textContent = m.total;
            if (document.getElementById('kpi-high-val')) document.getElementById('kpi-high-val').textContent = m.high ?? m.immediate;
            if (document.getElementById('kpi-medium-val')) document.getElementById('kpi-medium-val').textContent = m.medium ?? m.soon;
            if (document.getElementById('kpi-low-val')) document.getElementById('kpi-low-val').textContent = m.low ?? m.routine;
            if (document.getElementById('kpi-immediate-val')) document.getElementById('kpi-immediate-val').textContent = m.high ?? m.immediate;
            if (document.getElementById('kpi-soon-val')) document.getElementById('kpi-soon-val').textContent = m.medium ?? m.soon;
            document.getElementById('kpi-review-val').textContent = m.needs_review;

            this.state.officerItems = res.items;
            this.renderOfficerTable(res.items);
        } catch (err) {
            if (!silent) {
                tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 2rem; color: #b91c1c;">Error: ${err.message}</td></tr>`;
            }
        }
    }

    renderOfficerTable(items) {
        const tbody = document.getElementById('officer-queue-tbody');
        if (!items || items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 2.5rem; color: #64748b;">No grievances match current filters.</td></tr>';
            return;
        }

        tbody.innerHTML = items.map(r => {
            const rawPri = r.priority || 'Unassigned';
            const pri = (rawPri === 'Immediate' || rawPri === 'High') ? 'High' : (rawPri === 'Soon' || rawPri === 'Medium') ? 'Medium' : (rawPri === 'Routine' || rawPri === 'Low') ? 'Low' : rawPri;
            const priClass = pri === 'High' ? 'pri-high' : pri === 'Medium' ? 'pri-medium' : pri === 'Low' ? 'pri-low' : 'pri-unassigned';
            const rowClass = pri === 'High' ? 'row-high' : '';

            const st = r.status || 'Received';
            const stClass = st === 'Received' ? 'status-received' : st === 'In Progress' ? 'status-inprogress' : st === 'Resolved' ? 'status-resolved' : 'status-review';

            const summaryText = r.english_summary || r.original_text || '';
            const dateStr = r.created_at ? new Date(r.created_at).toLocaleDateString() : '';

            return `
                <tr class="${rowClass}">
                    <td><span class="pri-pill ${priClass}">${pri}</span></td>
                    <td><b>#${r.id}</b></td>
                    <td><span class="cat-pill">📍 ${this.escapeHtml(r.ward || 'N/A')}</span></td>
                    <td><b>${this.escapeHtml(r.category || 'Pending')}</b></td>
                    <td>
                        <div class="table-citizen-cell">
                            <span class="citizen-name-text">${this.escapeHtml(r.citizen_name || 'Citizen')}</span>
                            <span class="citizen-lang-tag">🗣️ ${(r.detected_language || 'en').toUpperCase()}</span>
                        </div>
                    </td>
                    <td>
                        <div class="table-summary-cell" title="${this.escapeHtml(summaryText)}">
                            ${this.escapeHtml(summaryText)}
                        </div>
                    </td>
                    <td><span class="status-pill ${stClass}">${st}</span></td>
                    <td style="font-size: 0.78rem; color: #64748b;">${dateStr}</td>
                    <td style="text-align: center;">
                        <button type="button" class="btn btn-outline btn-sm" onclick="app.openGrievanceDetail(${r.id})">
                            🔍 Inspect
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    filterQueueLocally(query) {
        const q = (query || '').toLowerCase().trim();
        if (!q) {
            this.renderOfficerTable(this.state.officerItems);
            return;
        }

        const filtered = this.state.officerItems.filter(r => {
            return (
                String(r.id).includes(q) ||
                (r.ward || '').toLowerCase().includes(q) ||
                (r.category || '').toLowerCase().includes(q) ||
                (r.original_text || '').toLowerCase().includes(q) ||
                (r.english_summary || '').toLowerCase().includes(q) ||
                (r.citizen_name || '').toLowerCase().includes(q)
            );
        });

        this.renderOfficerTable(filtered);
    }

    // -----------------------------------------------------------------------
    // Officer Detail Modal Inspection & Updates
    // -----------------------------------------------------------------------
    async openGrievanceDetail(id) {
        this.state.activeModalGrievanceId = id;
        const modal = document.getElementById('officer-detail-modal');
        modal.style.display = 'flex';

        document.getElementById('modal-grievance-title').textContent = `Grievance #${id}`;
        document.getElementById('modal-hidden-grievance-id').value = id;
        document.getElementById('modal-update-note-text').value = '';

        try {
            const res = await this.apiRequest(`/api/officer/grievance/${id}`);
            if (!res || !res.grievance) return;

            const g = res.grievance;
            const notes = res.notes || [];

            document.getElementById('modal-grievance-subtitle').textContent = `Ward: ${g.ward || 'Unspecified'} | Logged: ${new Date(g.created_at).toLocaleString()}`;
            
            const rawPri = g.priority || 'Unassigned';
            const pri = (rawPri === 'Immediate' || rawPri === 'High') ? 'High' : (rawPri === 'Soon' || rawPri === 'Medium') ? 'Medium' : (rawPri === 'Routine' || rawPri === 'Low') ? 'Low' : rawPri;
            const priPill = document.getElementById('modal-priority-pill');
            priPill.textContent = pri;
            priPill.className = `pri-pill ${pri === 'High' ? 'pri-high' : pri === 'Medium' ? 'pri-medium' : pri === 'Low' ? 'pri-low' : 'pri-unassigned'}`;

            document.getElementById('modal-category-pill').textContent = g.category || 'Unassigned';
            
            const stPill = document.getElementById('modal-status-pill');
            stPill.textContent = g.status || 'Received';
            stPill.className = `status-pill ${g.status === 'Received' ? 'status-received' : g.status === 'In Progress' ? 'status-inprogress' : g.status === 'Resolved' ? 'status-resolved' : 'status-review'}`;

            document.getElementById('modal-emotion-pill').textContent = `Tone: ${g.emotion || 'Neutral'}`;

            document.getElementById('modal-original-text').textContent = g.original_text || '';
            document.getElementById('modal-detected-lang').textContent = (g.detected_language || 'en').toUpperCase();
            document.getElementById('modal-citizen-name').textContent = g.citizen_name || 'Citizen';
            document.getElementById('modal-citizen-email').textContent = g.citizen_email || '';

            document.getElementById('modal-english-summary').textContent = g.english_summary || '(Summary pending classification)';
            document.getElementById('modal-priority-reason').textContent = g.reason || '(Reasoning pending)';

            // Set current status in select box
            document.getElementById('modal-update-status-select').value = g.status || 'Received';

            // Render historical notes
            const timeline = document.getElementById('modal-notes-timeline');
            if (notes.length === 0) {
                timeline.innerHTML = '<p class="empty-notes-hint">No notes recorded yet.</p>';
            } else {
                timeline.innerHTML = notes.map(n => `
                    <div class="note-bubble">
                        <div class="note-bubble-meta">
                            <span class="note-bubble-author">👮 ${this.escapeHtml(n.officer_name || 'Officer')}</span>
                            <span>${new Date(n.created_at).toLocaleString()}</span>
                        </div>
                        <div style="color: #0f172a;">${this.escapeHtml(n.note)}</div>
                    </div>
                `).join('');
            }
        } catch (err) {
            this.showToast(`Error opening grievance #${id}: ${err.message}`, 'error');
            this.closeModal();
        }
    }

    closeModal() {
        const modal = document.getElementById('officer-detail-modal');
        modal.style.display = 'none';
        this.state.activeModalGrievanceId = null;
    }

    closeModalOutside(e) {
        if (e.target && e.target.id === 'officer-detail-modal') {
            this.closeModal();
        }
    }

    async handleStatusUpdate(e) {
        e.preventDefault();
        const id = this.state.activeModalGrievanceId;
        if (!id) return;

        const btn = document.getElementById('btn-save-status');
        const originalText = btn.textContent;

        const newStatus = document.getElementById('modal-update-status-select').value;
        const note = document.getElementById('modal-update-note-text').value.trim();

        try {
            btn.disabled = true;
            btn.textContent = 'Saving...';

            const res = await this.apiRequest(`/api/officer/grievance/${id}/status`, {
                method: 'POST',
                body: JSON.stringify({ status: newStatus, note })
            });

            if (res && res.success) {
                this.showToast(res.message, 'success');
                // Refresh modal data and background table
                await this.openGrievanceDetail(id);
                this.loadOfficerQueue();
            }
        } catch (err) {
            this.showToast(err.message || 'Failed to update status.', 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }

    // -----------------------------------------------------------------------
    // Insights & Analytics
    // -----------------------------------------------------------------------
    async loadInsights() {
        try {
            const res = await this.apiRequest('/api/insights');
            if (!res || !res.metrics) return;

            const m = res.metrics;
            document.getElementById('insight-total-val').textContent = m.total;
            document.getElementById('insight-immediate-val').textContent = m.immediate;
            document.getElementById('insight-resolved-val').textContent = m.resolved;
            document.getElementById('insight-wards-val').textContent = m.active_wards;

            // Render Categories Chart
            this.renderBarChart(
                'chart-container-category',
                res.distributions.categories || {},
                '#2563eb'
            );

            // Render Priority Breakdown
            this.renderUrgencyBreakdown(
                'chart-container-priority',
                res.distributions.priorities || {},
                m.total
            );

            // Render Wards Chart
            this.renderBarChart(
                'chart-container-ward',
                res.distributions.wards || {},
                '#8b5cf6'
            );

            // Render Recent 20 Table
            this.renderRecentTable(res.recent || []);
        } catch (err) {
            this.showToast('Error loading insights: ' + err.message, 'error');
        }
    }

    renderBarChart(containerId, dataMap, barColor) {
        const container = document.getElementById(containerId);
        const keys = Object.keys(dataMap);

        if (keys.length === 0) {
            container.innerHTML = '<p style="color: #94a3b8; font-size: 0.88rem; text-align: center;">No distribution data available.</p>';
            return;
        }

        const maxVal = Math.max(...Object.values(dataMap), 1);

        const rows = keys.map(k => {
            const val = dataMap[k];
            const pct = Math.round((val / maxVal) * 100);
            return `
                <div class="chart-bar-row">
                    <span class="chart-bar-label" title="${this.escapeHtml(k)}">${this.escapeHtml(k)}</span>
                    <div class="chart-bar-track">
                        <div class="chart-bar-fill" style="width: ${pct}%; background-color: ${barColor};">
                            ${val > 0 ? val : ''}
                        </div>
                    </div>
                    <span class="chart-bar-val">${val}</span>
                </div>
            `;
        }).join('');

        container.innerHTML = `<div class="chart-bar-list">${rows}</div>`;
    }

    renderUrgencyBreakdown(containerId, priorityMap, total) {
        const container = document.getElementById(containerId);
        const imm = priorityMap['Immediate'] || 0;
        const soon = priorityMap['Soon'] || 0;
        const routine = priorityMap['Routine'] || 0;

        const immPct = total > 0 ? Math.round((imm / total) * 100) : 0;
        const soonPct = total > 0 ? Math.round((soon / total) * 100) : 0;
        const routinePct = total > 0 ? Math.round((routine / total) * 100) : 0;

        container.innerHTML = `
            <div class="urgency-grid">
                <div class="urgency-metric-box immediate">
                    <div class="urgency-metric-label" style="color: #b91c1c;">🚨 Immediate</div>
                    <div class="urgency-metric-val" style="color: #b91c1c;">${imm}</div>
                    <div class="urgency-metric-pct">${immPct}% of all issues</div>
                </div>
                <div class="urgency-metric-box soon">
                    <div class="urgency-metric-label" style="color: #c2410c;">⚠️ Soon</div>
                    <div class="urgency-metric-val" style="color: #c2410c;">${soon}</div>
                    <div class="urgency-metric-pct">${soonPct}% of all issues</div>
                </div>
                <div class="urgency-metric-box routine">
                    <div class="urgency-metric-label" style="color: #15803d;">🟢 Routine</div>
                    <div class="urgency-metric-val" style="color: #15803d;">${routine}</div>
                    <div class="urgency-metric-pct">${routinePct}% of all issues</div>
                </div>
            </div>
        `;
    }

    renderRecentTable(items) {
        const tbody = document.getElementById('insights-recent-tbody');
        if (!items || items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: #94a3b8; padding: 1.5rem;">No recent records.</td></tr>';
            return;
        }

        tbody.innerHTML = items.map(r => {
            const rawPri = r.priority || 'Unassigned';
            const pri = (rawPri === 'Immediate' || rawPri === 'High') ? 'High' : (rawPri === 'Soon' || rawPri === 'Medium') ? 'Medium' : (rawPri === 'Routine' || rawPri === 'Low') ? 'Low' : rawPri;
            const priClass = pri === 'High' ? 'pri-high' : pri === 'Medium' ? 'pri-medium' : pri === 'Low' ? 'pri-low' : 'pri-unassigned';
            const st = r.status || 'Received';
            const stClass = st === 'Received' ? 'status-received' : st === 'In Progress' ? 'status-inprogress' : st === 'Resolved' ? 'status-resolved' : 'status-review';

            return `
                <tr>
                    <td><b>#${r.id}</b></td>
                    <td>${this.escapeHtml(r.ward || 'N/A')}</td>
                    <td><b>${this.escapeHtml(r.category || 'Other')}</b></td>
                    <td><span class="pri-pill ${priClass}">${pri}</span></td>
                    <td>${(r.detected_language || 'en').toUpperCase()}</td>
                    <td style="max-width: 250px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        ${this.escapeHtml(r.english_summary || '')}
                    </td>
                    <td><span class="status-pill ${stClass}">${st}</span></td>
                    <td style="font-size: 0.78rem; color: #64748b;">${r.created_at ? new Date(r.created_at).toLocaleDateString() : ''}</td>
                </tr>
            `;
        }).join('');
    }

    exportCSV() {
        this.showToast('Preparing and downloading CSV...', 'info');
        window.location.href = '/api/insights/export';
    }

    // -----------------------------------------------------------------------
    // UI Helpers & Toast Notifications
    // -----------------------------------------------------------------------
    showToast(message, type = 'info', duration = 3800) {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        const icon = type === 'success' ? '✅' : type === 'error' ? '⚠️' : 'ℹ️';
        toast.innerHTML = `<span>${icon}</span><span>${this.escapeHtml(message)}</span>`;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            setTimeout(() => toast.remove(), 250);
        }, duration);
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}

// Instantiate global app instance
const app = new CivicTriageApp();
window.app = app;
