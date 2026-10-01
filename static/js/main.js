// VietTravel — Main JavaScript
'use strict';

// Navbar scroll
const navbar = document.getElementById('navbar');
const scrollTop = document.getElementById('scrollTop');
window.addEventListener('scroll', () => {
  if(window.scrollY > 60) { navbar.style.boxShadow='0 4px 30px rgba(0,0,0,0.4)'; scrollTop?.classList.add('visible'); }
  else { navbar.style.boxShadow=''; scrollTop?.classList.remove('visible'); }
});
scrollTop?.addEventListener('click', () => window.scrollTo({top:0, behavior:'smooth'}));

// User dropdown
const userBtn = document.getElementById('userMenuBtn');
const userDropdown = document.getElementById('userDropdown');
userBtn?.addEventListener('click', (e) => { e.stopPropagation(); userDropdown.classList.toggle('open'); });
document.addEventListener('click', () => userDropdown?.classList.remove('open'));

// Mobile menu
const mobileBtn = document.getElementById('mobileMenuBtn');
const mobileMenu = document.getElementById('mobileMenu');
mobileBtn?.addEventListener('click', () => mobileMenu.classList.toggle('open'));

// Auto-dismiss toasts
setTimeout(() => {
  document.querySelectorAll('.toast').forEach(t => { t.style.opacity='0'; t.style.transition='opacity 0.5s'; setTimeout(()=>t.remove(),500); });
}, 5000);

// Intersection Observer animations
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => { if(e.isIntersecting) { e.target.style.opacity='1'; e.target.style.transform='translateY(0)'; observer.unobserve(e.target); } });
}, {threshold:0.1, rootMargin:'0px 0px -50px 0px'});

document.querySelectorAll('.tour-card, .dep-card, .mybooking-card, .check-item').forEach((el, i) => {
  el.style.opacity='0'; el.style.transform='translateY(24px)';
  el.style.transition = `opacity 0.5s ease ${i*0.07}s, transform 0.5s ease ${i*0.07}s`;
  observer.observe(el);
});
