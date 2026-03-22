/**
 * animations.js
 * Scroll-based reveal animations and navigation effects
 */

(function () {
    'use strict';

    // ============================================
    // Navigation Scroll Effect
    // ============================================
    const nav = document.getElementById('mainNav');

    if (nav) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 60) {
                nav.classList.add('nav--scrolled');
            } else {
                nav.classList.remove('nav--scrolled');
            }
        }, { passive: true });
    }


    // ============================================
    // Scroll Reveal — Intersection Observer
    // ============================================
    const revealElements = document.querySelectorAll('.reveal');

    if (revealElements.length > 0 && 'IntersectionObserver' in window) {
        const revealObserver = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    revealObserver.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.15,
            rootMargin: '0px 0px -40px 0px'
        });

        revealElements.forEach((el, index) => {
            el.style.transitionDelay = `${index * 0.1}s`;
            revealObserver.observe(el);
        });
    } else {
        revealElements.forEach((el) => {
            el.classList.add('revealed');
        });
    }


    // ============================================
    // Smooth Anchor Scrolling
    // href="#" 단독(빈 앵커)은 querySelector가 SyntaxError를 던지므로
    // 실제 섹션 ID가 있는 경우에만 스크롤 처리합니다.
    // ============================================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');

            // '#' 단독이거나 '#' 뒤에 아무것도 없으면 건너뜀
            if (!href || href === '#') return;

            const target = document.querySelector(href);
            if (target) {
                e.preventDefault();
                const navHeight = nav ? nav.offsetHeight : 0;
                const targetPosition = target.getBoundingClientRect().top + window.scrollY - navHeight - 20;
                window.scrollTo({ top: targetPosition, behavior: 'smooth' });
            }
        });
    });

})();
