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
        let lastScrollY = 0;

        window.addEventListener('scroll', () => {
            const currentScrollY = window.scrollY;

            if (currentScrollY > 60) {
                nav.classList.add('nav--scrolled');
            } else {
                nav.classList.remove('nav--scrolled');
            }

            lastScrollY = currentScrollY;
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
            // Stagger the delay for sequential reveals
            el.style.transitionDelay = `${index * 0.1}s`;
            revealObserver.observe(el);
        });
    } else {
        // Fallback: show everything immediately
        revealElements.forEach((el) => {
            el.classList.add('revealed');
        });
    }


    // ============================================
    // Smooth Anchor Scrolling
    // ============================================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                const navHeight = nav ? nav.offsetHeight : 0;
                const targetPosition = target.getBoundingClientRect().top + window.scrollY - navHeight - 20;

                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

})();
