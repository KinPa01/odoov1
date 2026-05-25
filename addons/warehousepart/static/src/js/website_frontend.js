/** @odoo-module **/
/**
 * Ran Ahlai — Website Frontend JS
 * Dark Automotive Theme — Interactive Features
 */

import { ready } from "@web/core/utils/timing";

// ── COUNTDOWN TIMER ─────────────────────────────────────────────
function initCountdown() {
    const hoursEl = document.getElementById('ra-hours');
    const minsEl  = document.getElementById('ra-mins');
    const secsEl  = document.getElementById('ra-secs');
    if (!hoursEl || !minsEl || !secsEl) return;

    // Flash sale ends at midnight tonight (or configurable)
    const now = new Date();
    const endOfDay = new Date(now);
    endOfDay.setHours(23, 59, 59, 0);

    function pad(n) { return String(n).padStart(2, '0'); }

    function tick() {
        const remaining = Math.max(0, endOfDay - new Date());
        const totalSecs = Math.floor(remaining / 1000);
        const h = Math.floor(totalSecs / 3600);
        const m = Math.floor((totalSecs % 3600) / 60);
        const s = totalSecs % 60;

        hoursEl.textContent = pad(h);
        minsEl.textContent  = pad(m);
        secsEl.textContent  = pad(s);

        // Flash red on the last minute
        if (remaining < 60000) {
            document.querySelectorAll('.ra-countdown-item').forEach(el => {
                el.style.borderColor = 'rgba(230, 57, 70, 0.6)';
                el.style.background  = 'rgba(230, 57, 70, 0.12)';
            });
        }
    }

    tick();
    setInterval(tick, 1000);
}

// ── SCROLL REVEAL ANIMATION ─────────────────────────────────────
function initScrollReveal() {
    const targets = document.querySelectorAll(
        '.ra-cat-card, .ra-product-card, .ra-promo-card, .ra-feature-item, .ra-brand-badge, .ra-stat-item'
    );
    if (!targets.length || !window.IntersectionObserver) return;

    // Prepare elements
    targets.forEach((el, i) => {
        el.style.opacity    = '0';
        el.style.transform  = 'translateY(24px)';
        el.style.transition = `opacity 0.5s ease ${(i % 6) * 0.07}s, transform 0.5s ease ${(i % 6) * 0.07}s`;
    });

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity   = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12 });

    targets.forEach(el => observer.observe(el));
}

// ── HERO PARALLAX (subtle) ──────────────────────────────────────
function initHeroParallax() {
    const hero = document.querySelector('.ra-hero');
    if (!hero) return;

    let ticking = false;
    window.addEventListener('scroll', () => {
        if (!ticking) {
            window.requestAnimationFrame(() => {
                const scrollY = window.scrollY;
                const deco = hero.querySelector('.ra-hero-deco');
                if (deco) {
                    deco.style.transform = `translateY(${scrollY * 0.06}px)`;
                }
                ticking = false;
            });
            ticking = true;
        }
    }, { passive: true });
}

// ── NAVBAR SHRINK ON SCROLL ─────────────────────────────────────
function initNavbarShrink() {
    const header = document.querySelector('header#top, header.o_header_standard');
    if (!header) return;

    window.addEventListener('scroll', () => {
        if (window.scrollY > 60) {
            header.style.boxShadow = '0 4px 40px rgba(0,0,0,0.7)';
        } else {
            header.style.boxShadow = '0 2px 30px rgba(0,0,0,0.55)';
        }
    }, { passive: true });
}

// ── PRODUCT CARD HOVER SOUND (optional — visual pulse) ──────────
function initProductCardPulse() {
    document.querySelectorAll('.ra-product-card').forEach(card => {
        card.addEventListener('mouseenter', () => {
            const badge = card.querySelector('.ra-product-badge');
            if (badge) {
                badge.style.transform = 'scale(1.1)';
                badge.style.transition = 'transform 0.2s ease';
            }
        });
        card.addEventListener('mouseleave', () => {
            const badge = card.querySelector('.ra-product-badge');
            if (badge) badge.style.transform = 'scale(1)';
        });
    });
}

// ── SMOOTH SCROLL FOR ANCHOR LINKS ─────────────────────────────
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(link => {
        link.addEventListener('click', (e) => {
            const target = document.querySelector(link.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

// ── INIT ALL ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initCountdown();
    initScrollReveal();
    initHeroParallax();
    initNavbarShrink();
    initProductCardPulse();
    initSmoothScroll();
});
