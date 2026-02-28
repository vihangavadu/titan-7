/* ============================================
   TitanXanti — Main JavaScript
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {

    // ---- Navbar Scroll Effect ----
    const navbar = document.getElementById('navbar');
    if (navbar) {
        window.addEventListener('scroll', () => {
            navbar.classList.toggle('scrolled', window.scrollY > 50);
        });
    }

    // ---- Mobile Menu Toggle ----
    const menuToggle = document.getElementById('menuToggle');
    const navLinks = document.getElementById('navLinks');
    if (menuToggle && navLinks) {
        menuToggle.addEventListener('click', () => {
            navLinks.classList.toggle('open');
            menuToggle.classList.toggle('active');
        });
        navLinks.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('open');
                menuToggle.classList.remove('active');
            });
        });
    }

    // ---- Animated Counter ----
    const counters = document.querySelectorAll('.stat-number[data-count]');
    if (counters.length) {
        const animateCounter = (el) => {
            const target = parseFloat(el.dataset.count);
            const duration = 2000;
            const startTime = performance.now();
            const isDecimal = target % 1 !== 0;

            const update = (currentTime) => {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const eased = 1 - Math.pow(1 - progress, 3);
                const current = target * eased;
                el.textContent = isDecimal ? current.toFixed(1) : Math.floor(current);
                if (progress < 1) requestAnimationFrame(update);
            };
            requestAnimationFrame(update);
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });

        counters.forEach(c => observer.observe(c));
    }

    // ---- Scroll Reveal Animation ----
    const revealElements = document.querySelectorAll(
        '.feature-card, .value-card, .team-card, .service-block, .pricing-card, .info-card, .doc-step, .timeline-item'
    );

    if (revealElements.length) {
        const revealObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                    revealObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

        revealElements.forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(24px)';
            el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            revealObserver.observe(el);
        });
    }

    // ---- Terminal Typing Effect (Home page) ----
    const terminalBody = document.getElementById('terminalBody');
    if (terminalBody) {
        const lines = terminalBody.querySelectorAll('.terminal-line');
        lines.forEach((line, i) => {
            line.style.opacity = '0';
            line.style.transition = 'opacity 0.4s ease';
            setTimeout(() => { line.style.opacity = '1'; }, 300 + i * 400);
        });
    }

    // ---- Docs Sidebar Active State ----
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    if (sidebarLinks.length) {
        const docSections = document.querySelectorAll('.doc-section[id]');
        const updateSidebar = () => {
            let current = '';
            docSections.forEach(section => {
                const top = section.getBoundingClientRect().top;
                if (top < 200) current = section.id;
            });
            sidebarLinks.forEach(link => {
                link.classList.toggle('active', link.getAttribute('href') === '#' + current);
            });
        };
        window.addEventListener('scroll', updateSidebar);
        updateSidebar();
    }

    // ---- Contact Form ----
    const contactForm = document.getElementById('contactForm');
    const formSuccess = document.getElementById('formSuccess');
    if (contactForm && formSuccess) {
        contactForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const formData = new FormData(contactForm);
            const data = Object.fromEntries(formData.entries());
            console.log('Form submitted:', data);
            contactForm.style.display = 'none';
            formSuccess.style.display = 'block';
        });
    }

    // ---- Copy Code Button ----
    window.copyCode = function(btn) {
        const pre = btn.closest('.code-snippet').querySelector('pre');
        if (pre) {
            const text = pre.textContent;
            navigator.clipboard.writeText(text).then(() => {
                const original = btn.textContent;
                btn.textContent = 'Copied!';
                btn.style.color = '#28c840';
                btn.style.borderColor = '#28c840';
                setTimeout(() => {
                    btn.textContent = original;
                    btn.style.color = '';
                    btn.style.borderColor = '';
                }, 2000);
            });
        }
    };

    // ---- Smooth Scroll for anchor links ----
    document.querySelectorAll('a[href^="#"]').forEach(link => {
        link.addEventListener('click', (e) => {
            const target = document.querySelector(link.getAttribute('href'));
            if (target) {
                e.preventDefault();
                const offset = 100;
                const top = target.getBoundingClientRect().top + window.scrollY - offset;
                window.scrollTo({ top, behavior: 'smooth' });
            }
        });
    });

    // ---- Bar Fill Animation ----
    const barFills = document.querySelectorAll('.bar-fill');
    if (barFills.length) {
        const barObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const width = entry.target.style.width;
                    entry.target.style.width = '0';
                    setTimeout(() => { entry.target.style.width = width; }, 100);
                    barObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        barFills.forEach(b => barObserver.observe(b));
    }

});
