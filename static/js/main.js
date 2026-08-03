/* ── Palkay main.js ─────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {

  // ── Sticky nav shadow on scroll ──────────────────────────────
  const headerEl = document.querySelector('header');
  if (headerEl) {
    const onScroll = () => headerEl.classList.toggle('scrolled', window.scrollY > 10);
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  // ── Dismiss messages ─────────────────────────────────────────
  document.querySelectorAll('.message-close').forEach(btn => {
    btn.addEventListener('click', () => btn.closest('.message-item').remove());
  });
  // Auto-dismiss after 5s
  setTimeout(() => {
    document.querySelectorAll('.message-item').forEach(el => {
      el.style.transition = 'opacity .4s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    });
  }, 5000);

  // ── Scroll to Top Button ─────────────────────────────────────
  const scrollTopBtn = document.getElementById('scroll-to-top');
  if (scrollTopBtn) {
    window.addEventListener('scroll', () => {
      if (window.scrollY > 300) {
        scrollTopBtn.style.display = 'flex';
        setTimeout(() => {
          scrollTopBtn.style.opacity = '1';
          scrollTopBtn.style.transform = 'translateY(0)';
        }, 10);
      } else {
        scrollTopBtn.style.opacity = '0';
        scrollTopBtn.style.transform = 'translateY(10px)';
        setTimeout(() => {
          if (scrollTopBtn.style.opacity === '0') {
            scrollTopBtn.style.display = 'none';
          }
        }, 300);
      }
    });
    scrollTopBtn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // ── AJAX Add to Cart ─────────────────────────────────────────
  document.querySelectorAll('[data-ajax-cart]').forEach(form => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = form.querySelector('button[type=submit]');
      const original = btn.textContent;
      btn.textContent = '...';
      btn.disabled = true;

      try {
        const res = await fetch(form.action, {
          method: 'POST',
          body: new FormData(form),
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
        });
        const data = await res.json();
        if (data.status === 'ok') {
          // Update cart count badge
          document.querySelectorAll('.cart-count-badge').forEach(el => {
            el.textContent = data.cart_count;
          });
          btn.textContent = '✓ Added';
          setTimeout(() => { btn.textContent = original; btn.disabled = false; }, 1800);
          showToast(data.message, 'success');
        } else {
          btn.textContent = original;
          btn.disabled = false;
          showToast(data.message || 'Error adding to cart.', 'error');
        }
      } catch {
        btn.textContent = original;
        btn.disabled = false;
      }
    });
  });

  // ── Wishlist toggle ───────────────────────────────────────────
  document.querySelectorAll('[data-wishlist-toggle]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const url = btn.dataset.wishlistToggle;
      const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                   getCookie('csrftoken');
      try {
        const res = await fetch(url, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrf,
            'X-Requested-With': 'XMLHttpRequest',
          },
        });
        const data = await res.json();
        if (data.status === 'added') {
          btn.classList.add('active');
          btn.title = 'Remove from wishlist';
          showToast('Added to wishlist', 'success');
        } else {
          btn.classList.remove('active');
          btn.title = 'Add to wishlist';
          showToast('Removed from wishlist', 'info');
        }
      } catch {
        showToast('Please sign in to use wishlist.', 'warning');
      }
    });
  });

  // ── Product gallery thumbs ────────────────────────────────────
  const mainImg = document.querySelector('.gallery-main-img');
  document.querySelectorAll('.gallery-thumb').forEach(thumb => {
    thumb.addEventListener('click', () => {
      document.querySelectorAll('.gallery-thumb').forEach(t => t.classList.remove('active'));
      thumb.classList.add('active');
      if (mainImg) {
        mainImg.src = thumb.dataset.full;
        mainImg.alt = thumb.dataset.alt || '';
      }
    });
  });

  // ── Quantity stepper ─────────────────────────────────────────
  document.querySelectorAll('.qty-input').forEach(wrap => {
    const input = wrap.querySelector('input');
    const dec   = wrap.querySelector('[data-qty="dec"]');
    const inc   = wrap.querySelector('[data-qty="inc"]');
    if (!input) return;
    dec?.addEventListener('click', () => {
      const v = parseInt(input.value, 10);
      if (v > 1) input.value = v - 1;
    });
    inc?.addEventListener('click', () => {
      const v   = parseInt(input.value, 10);
      const max = parseInt(input.max, 10) || 100;
      if (v < max) input.value = v + 1;
    });
  });

  // ── Variant selector ─────────────────────────────────────────
  document.querySelectorAll('.variant-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const group = btn.closest('.variant-options');
      group.querySelectorAll('.variant-btn').forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      const hiddenInput = document.querySelector('#variant-id-input');
      if (hiddenInput) hiddenInput.value = btn.dataset.variantId || '';
    });
  });

  // ── Address radio cards ───────────────────────────────────────
  document.querySelectorAll('.address-radio-card').forEach(card => {
    card.addEventListener('click', () => {
      document.querySelectorAll('.address-radio-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      const radio = card.querySelector('input[type=radio]');
      if (radio) radio.checked = true;
    });
  });

  // ── Subscribe form (cosmetic) ─────────────────────────────────
  const subBtn = document.querySelector('.subscribe-row button');
  const subInput = document.querySelector('.subscribe-row input');
  if (subBtn && subInput) {
    subBtn.addEventListener('click', () => {
      if (!subInput.value || !subInput.value.includes('@')) {
        subInput.style.borderColor = '#C75D3A';
        return;
      }
      showToast('You\'re subscribed! Welcome to Palkay.', 'success');
      subInput.value = '';
    });
  }

});

// ── Toast notification helper ─────────────────────────────────
function showToast(msg, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `message-item ${type}`;
  toast.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;min-width:260px;max-width:380px;box-shadow:0 8px 24px rgba(0,0,0,.12);transform:translateX(120%);opacity:0;transition:transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.4s;';
  toast.innerHTML = `<span>${msg}</span><button class="message-close" style="background:none;border:none;cursor:pointer;font-size:16px;opacity:.5;padding-left:12px;" onclick="this.closest('div').remove()">✕</button>`;
  document.body.appendChild(toast);
  
  // Trigger slide-in
  requestAnimationFrame(() => {
    toast.style.transform = 'translateX(0)';
    toast.style.opacity = '1';
  });

  // Slide-out and remove
  setTimeout(() => {
    toast.style.transform = 'translateX(120%)';
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 450);
  }, 3500);
}

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? match[2] : '';
}
