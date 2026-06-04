/** @odoo-module **/
/**
 * Ran Ahlai — Website Frontend JS
 * Dark Automotive Theme
 *
 * ฟีเจอร์:
 *  1. initBestSellers()        — ดึงสินค้าแนะนำจาก Admin Backend
 *  2. initHomepageCategories() — ดึงหมวดหมู่จาก Admin Backend
 *  3. initFlashSale()          — countdown + สินค้า Flash Sale (สุ่มทุก 8 ชั่วโมง)
 *  4. Scroll reveal, parallax, navbar, smooth scroll
 */

// ── CONSTANTS ─────────────────────────────────────────────────────
const SLOT_SECS = 8 * 3600;       // 8 ชั่วโมง
const EPOCH_START_TS = 1748217600;     // 2025-05-26 00:00:00 UTC
const REFRESH_MS = 5 * 60 * 1000; // refresh ทุก 5 นาที

// ── HELPERS ───────────────────────────────────────────────────────
function formatPrice(num) {
    return '฿ ' + Number(num).toLocaleString('th-TH', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });
}

function escHtml(str) {
    return String(str || '').replace(/[&<>"']/g, c =>
        ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
    );
}

function pad(n) { return String(n).padStart(2, '0'); }

function getSlotInfo() {
    const nowSec = Math.floor(Date.now() / 1000);
    const elapsed = nowSec - EPOCH_START_TS;
    const slotIndex = Math.floor(elapsed / SLOT_SECS);
    const secsInSlot = elapsed % SLOT_SECS;
    const secsLeft = SLOT_SECS - secsInSlot;
    return { slotIndex, secsLeft };
}

async function apiFetch(url) {
    try {
        const res = await fetch(url, { cache: 'no-store' });
        if (!res.ok) throw new Error(`${url} → HTTP ${res.status}`);
        return await res.json();
    } catch (e) {
        console.warn('RanAhlai API:', e.message);
        return null;
    }
}

// ─────────────────────────────────────────────────────────────────
// 1. BEST SELLERS — Admin-managed products
// ─────────────────────────────────────────────────────────────────
async function initBestSellers() {
    const grid = document.getElementById('ra-best-sellers-grid');
    if (!grid) return;

    async function render() {
        const data = await apiFetch('/homepage/best-sellers');

        if (!data || !data.products || data.products.length === 0) {
            grid.innerHTML = `
                <div class="col-12 text-center py-4">
                    <p style="color:#aaa;">ยังไม่มีสินค้าแนะนำ — ตั้งค่าที่ Backend → ⭐ สินค้าแนะนำ</p>
                    <a href="/shop" class="ra-btn-red" style="display:inline-block;margin-top:12px;">ดูสินค้าทั้งหมด →</a>
                </div>`;
            return;
        }

        grid.style.opacity = '0';
        grid.style.transform = 'translateY(8px)';
        grid.style.transition = 'opacity 0.4s ease, transform 0.4s ease';

        setTimeout(() => {
            grid.innerHTML = data.products.map(p => `
                <div class="col-6 col-md-3">
                    <a href="${p.url}" class="ra-product-card d-block text-decoration-none" style="position:relative; overflow:hidden;">
                        ${p.badge_text ? `<span class="ra-product-badge" style="background:${p.badge_color};">${escHtml(p.badge_text)}</span>` : ''}
                        ${!p.in_stock ? '<div class="ra-flash-out-stock">หมดชั่วคราว</div>' : ''}
                        <div class="ra-product-img-wrap" style="text-align:center; padding:24px; min-height:140px; display:flex; align-items:center; justify-content:center; ${!p.in_stock ? 'opacity:0.5;' : ''}">
                            <img src="${p.image_url}" alt="${escHtml(p.name)}"
                                 loading="lazy"
                                 style="max-height:120px; max-width:100%; object-fit:contain;"
                                 onerror="this.style.display='none';this.nextElementSibling.style.display='block';">
                            <span style="display:none;font-size:3rem;">🔧</span>
                        </div>
                        <div class="ra-product-info">
                            <p class="ra-product-name">${escHtml(p.name)}</p>
                            <div><span class="ra-product-price">${formatPrice(p.price)}</span></div>
                        </div>
                    </a>
                </div>
            `).join('');

            grid.style.opacity = '1';
            grid.style.transform = 'translateY(0)';
            initProductCardPulse();
            initScrollRevealFor(grid.querySelectorAll('.ra-product-card'));
        }, 300);
    }

    await render();
    setInterval(render, REFRESH_MS);
}

// ─────────────────────────────────────────────────────────────────
// 2. HOMEPAGE CATEGORIES — Admin-managed
// ─────────────────────────────────────────────────────────────────
async function initHomepageCategories() {
    const grid = document.getElementById('ra-cat-grid');
    if (!grid) return;

    async function render() {
        const data = await apiFetch('/homepage/categories');

        if (!data || !data.categories || data.categories.length === 0) {
            renderFallbackCategories(grid);
            return;
        }

        grid.style.transition = 'opacity 0.3s ease';
        grid.style.opacity = '0';

        setTimeout(() => {
            grid.innerHTML = data.categories.map((cat, i) => `
                <a href="${cat.url}" class="ra-cat-card" id="cat-dyn-${cat.id}">
                    <span class="ra-cat-icon">${cat.icon}</span>
                    <p class="ra-cat-name">${escHtml(cat.name)}</p>
                    <p class="ra-cat-count">${cat.product_count > 0 ? cat.product_count + '+ รายการ' : 'ดูสินค้า'}</p>
                </a>
            `).join('');
            grid.style.opacity = '1';
            initScrollRevealFor(grid.querySelectorAll('.ra-cat-card'));
        }, 250);
    }

    await render();
    setInterval(render, REFRESH_MS);
}

function renderFallbackCategories(grid) {
    const defs = [
        { icon: '🛢️', name: 'น้ำมันเครื่อง', url: '/shop/category/นามนเครอง-1' },
        { icon: '⚙️', name: 'ระบบเบรก', url: '/shop/category/ระบบเบรก-2' },
        { icon: '🔧', name: 'โช้คอัพ', url: '/shop/category/ชวงลาง-5' },
        { icon: '🔘', name: 'ยางรถยนต์', url: '/shop/category/ยางลอ-6' },
        { icon: '💡', name: 'ไฟและไฟฟ้า', url: '/shop/category/ระบบไฟฟา-8' },
        { icon: '💨', name: 'ไส้กรอง', url: '/shop/category/กรองกากาศ-10' },
    ];
    grid.innerHTML = defs.map(d => `
        <a href="${d.url}" class="ra-cat-card">
            <span class="ra-cat-icon">${d.icon}</span>
            <p class="ra-cat-name">${d.name}</p>
        </a>
    `).join('');
    grid.style.opacity = '1';
}

// ─────────────────────────────────────────────────────────────────
// 3. FLASH SALE — countdown + real products
// ─────────────────────────────────────────────────────────────────
async function initFlashSale() {
    const hoursEl = document.getElementById('ra-hours');
    const minsEl = document.getElementById('ra-mins');
    const secsEl = document.getElementById('ra-secs');
    const grid = document.getElementById('ra-flash-grid');
    if (!hoursEl || !minsEl || !secsEl || !grid) return;

    let lastSlot = -1;
    let isLoading = false;

    async function loadProducts() {
        if (isLoading) return;
        isLoading = true;

        grid.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        grid.style.opacity = '0';
        grid.style.transform = 'translateY(10px)';

        const data = await apiFetch('/flash-sale/data');

        setTimeout(() => {
            renderFlashProducts(grid, data);
            grid.style.opacity = '1';
            grid.style.transform = 'translateY(0)';
            isLoading = false;
            initProductCardPulse();

            // Dynamic update of "ดูโปรทั้งหมด →" link
            const viewAllBtn = document.getElementById('ra-flash-view-all');
            if (viewAllBtn) {
                if (data && data.tag_id) {
                    viewAllBtn.href = `/shop?tags=${data.tag_id}`;
                } else {
                    viewAllBtn.href = `/shop`;
                }
            }
        }, 400);
    }

    function tick() {
        const { slotIndex, secsLeft } = getSlotInfo();
        const h = Math.floor(secsLeft / 3600);
        const m = Math.floor((secsLeft % 3600) / 60);
        const s = secsLeft % 60;

        hoursEl.textContent = pad(h);
        minsEl.textContent = pad(m);
        secsEl.textContent = pad(s);

        updateProgressBar(secsLeft);

        if (slotIndex !== lastSlot) {
            lastSlot = slotIndex;
            loadProducts();
            const label = document.getElementById('ra-flash-label');
            if (label) {
                label.classList.add('ra-flash-burst');
                setTimeout(() => label.classList.remove('ra-flash-burst'), 700);
            }
        }

        // Urgency < 10 นาที
        const items = document.querySelectorAll('.ra-countdown-item');
        if (secsLeft < 600) {
            items.forEach(el => el.classList.add('ra-countdown-urgent'));
            const label = document.getElementById('ra-flash-label');
            if (label) label.classList.add('ra-label-urgent');
        } else {
            items.forEach(el => el.classList.remove('ra-countdown-urgent'));
            const label = document.getElementById('ra-flash-label');
            if (label) label.classList.remove('ra-label-urgent');
        }
    }

    loadProducts();
    tick();
    setInterval(tick, 1000);
}

function renderFlashProducts(grid, data) {
    if (!data || !data.products || data.products.length === 0) {
        grid.innerHTML = `
            <div class="col-12 text-center py-4">
                <p style="color:#aaa;">ยังไม่มีสินค้า Flash Sale — ตั้งค่าที่ Backend → ⚡ Flash Sale</p>
                <a href="/shop" class="ra-btn-red" style="display:inline-block;margin-top:12px;">ดูสินค้าทั้งหมด →</a>
            </div>`;
        return;
    }

    grid.innerHTML = data.products.map(p => `
        <div class="col-6 col-md-3">
            <a href="${p.url}" class="ra-product-card ra-flash-card d-block text-decoration-none" style="position:relative; overflow:hidden;">
                <span class="ra-product-badge">-${p.discount_pct}%</span>
                ${!p.in_stock ? '<div class="ra-flash-out-stock">หมดชั่วคราว</div>' : ''}
                <div class="ra-product-img-wrap" style="text-align:center;padding:20px;min-height:140px;display:flex;align-items:center;justify-content:center; ${!p.in_stock ? 'opacity:0.5;' : ''}">
                    <img src="${p.image_url}" alt="${escHtml(p.name)}"
                         loading="lazy"
                         style="max-height:120px;max-width:100%;object-fit:contain;"
                         onerror="this.style.display='none';this.nextElementSibling.style.display='block';">
                    <span style="display:none;font-size:3rem;">🔧</span>
                </div>
                <div class="ra-product-info">
                    <p class="ra-product-name">${escHtml(p.name)}</p>
                    ${p.brand ? `<p class="ra-product-brand">${escHtml(p.brand)}</p>` : ''}
                    <div style="display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;">
                        <span class="ra-product-price">${formatPrice(p.price)}</span>
                        <span class="ra-product-old-price">${formatPrice(p.original_price)}</span>
                    </div>
                </div>
            </a>
        </div>
    `).join('');
}

function updateProgressBar(secsLeft) {
    const bar = document.getElementById('ra-flash-progress');
    if (!bar) return;
    const pct = Math.max(0, Math.min(100, (secsLeft / SLOT_SECS) * 100));
    bar.style.width = pct + '%';
    bar.style.background = pct > 50
        ? 'linear-gradient(90deg,#e63946,#ff6b35)'
        : pct > 15
            ? 'linear-gradient(90deg,#e63946,#ffd700)'
            : 'linear-gradient(90deg,#e63946,#ff0000)';
}

// ─────────────────────────────────────────────────────────────────
// 4. SCROLL REVEAL
// ─────────────────────────────────────────────────────────────────
function initScrollReveal() {
    initScrollRevealFor(document.querySelectorAll(
        '.ra-cat-card, .ra-product-card, .ra-promo-card, .ra-feature-item, .ra-brand-badge, .ra-stat-item'
    ));
}

function initScrollRevealFor(targets) {
    if (!targets || !targets.length || !window.IntersectionObserver) return;

    targets.forEach((el, i) => {
        if (el.classList.contains('ra-cat-skeleton') || el.classList.contains('ra-product-skeleton')) return;
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = `opacity 0.5s ease ${(i % 6) * 0.07}s, transform 0.5s ease ${(i % 6) * 0.07}s`;
    });

    const obs = new IntersectionObserver(entries => {
        entries.forEach(e => {
            if (e.isIntersecting) {
                e.target.style.opacity = '1';
                e.target.style.transform = 'translateY(0)';
                obs.unobserve(e.target);
            }
        });
    }, { threshold: 0.1 });

    targets.forEach(el => {
        if (!el.classList.contains('ra-cat-skeleton') && !el.classList.contains('ra-product-skeleton')) {
            obs.observe(el);
        }
    });
}

// ─────────────────────────────────────────────────────────────────
// 5. OTHER INTERACTIONS
// ─────────────────────────────────────────────────────────────────
function initHeroParallax() {
    const hero = document.querySelector('.ra-hero');
    if (!hero) return;
    let ticking = false;
    window.addEventListener('scroll', () => {
        if (!ticking) {
            window.requestAnimationFrame(() => {
                const deco = hero.querySelector('.ra-hero-deco');
                if (deco) deco.style.transform = `translateY(${window.scrollY * 0.06}px)`;
                ticking = false;
            });
            ticking = true;
        }
    }, { passive: true });
}

function initNavbarShrink() {
    const header = document.querySelector('header#top, header.o_header_standard');
    if (!header) return;
    window.addEventListener('scroll', () => {
        header.style.boxShadow = window.scrollY > 60
            ? '0 4px 40px rgba(0,0,0,0.7)'
            : '0 2px 30px rgba(0,0,0,0.55)';
    }, { passive: true });
}

function initProductCardPulse() {
    document.querySelectorAll('.ra-product-card').forEach(card => {
        if (card._pulseInit) return;
        card._pulseInit = true;
        card.addEventListener('mouseenter', () => {
            const badge = card.querySelector('.ra-product-badge');
            if (badge) { badge.style.transform = 'scale(1.1)'; badge.style.transition = 'transform 0.2s'; }
        });
        card.addEventListener('mouseleave', () => {
            const badge = card.querySelector('.ra-product-badge');
            if (badge) badge.style.transform = 'scale(1)';
        });
    });
}

function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(link => {
        link.addEventListener('click', e => {
            const href = link.getAttribute('href');
            if (!href || href === '#' || href === '#!') return;
            try {
                const target = document.querySelector(href);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            } catch (err) {
                // Ignore invalid selector errors
            }
        });
    });
}

// ─────────────────────────────────────────────────────────────────
// INIT — รองรับทั้ง DOM โหลดแล้ว และยังไม่โหลด
// แก้ปัญหา: Odoo JS module โหลดหลัง DOMContentLoaded ไปแล้ว
// ─────────────────────────────────────────────────────────────────
function initAll() {
    initBestSellers();
    initHomepageCategories();
    initFlashSale();
    initScrollReveal();
    initHeroParallax();
    initNavbarShrink();
    initProductCardPulse();
    initSmoothScroll();
}

// ✅ ตรวจสอบ readyState ก่อน — ถ้า DOM โหลดแล้วให้รันทันที
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
} else {
    // DOM พร้อมแล้ว (โหลด JS module หลัง DOM ready) → รันทันที
    initAll();
}
