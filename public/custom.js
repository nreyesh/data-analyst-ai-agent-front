/**
 * Self-service Password Reset Integration for Comunidad Sierra Plaza
 * Injects a "¿Olvidó su contraseña?" link into the login form and handles
 * the modal prompt to send an official password reset email via Firebase Auth.
 */

(function () {
  function initPasswordResetLink() {
    // Only execute on login page
    if (!window.location.pathname.includes('/login') && window.location.pathname !== '/') {
      return;
    }

    const passwordInput = document.querySelector('input[type="password"]');
    if (!passwordInput) {
      setTimeout(initPasswordResetLink, 300);
      return;
    }

    // Check if the link is already injected
    if (document.getElementById('forgot-password-container')) {
      return;
    }

    // Find the password field wrapper or container
    const parentContainer = passwordInput.closest('div');
    if (!parentContainer) return;

    // Create container for the reset link
    const resetContainer = document.createElement('div');
    resetContainer.id = 'forgot-password-container';
    resetContainer.style.cssText = 'display: flex; justify-content: flex-end; margin-top: 6px; margin-bottom: 12px;';

    const resetLink = document.createElement('a');
    resetLink.id = 'forgot-password-link';
    resetLink.href = '#';
    resetLink.innerText = '¿Olvidó su contraseña?';
    resetLink.style.cssText = 'color: #00E599; font-size: 0.85rem; text-decoration: none; font-weight: 500; cursor: pointer; transition: opacity 0.2s;';
    
    resetLink.onmouseover = function () { this.style.textDecoration = 'underline'; };
    resetLink.onmouseout = function () { this.style.textDecoration = 'none'; };

    resetLink.addEventListener('click', function (e) {
      e.preventDefault();
      showResetPasswordModal();
    });

    resetContainer.appendChild(resetLink);
    parentContainer.insertAdjacentElement('afterend', resetContainer);
  }

  function showResetPasswordModal() {
    if (document.getElementById('reset-modal-overlay')) {
      return;
    }

    // Pre-populate with whatever the user might have already typed in email field
    const emailInput = document.querySelector('input[type="email"]') || document.querySelector('input[type="text"]');
    const initialEmail = emailInput ? emailInput.value.trim() : '';

    const overlay = document.createElement('div');
    overlay.id = 'reset-modal-overlay';
    overlay.style.cssText = `
      position: fixed; inset: 0; background: rgba(8, 12, 20, 0.82);
      backdrop-filter: blur(8px); display: flex; align-items: center; justify-content: center;
      z-index: 99999; padding: 20px;
    `;

    const modal = document.createElement('div');
    modal.style.cssText = `
      background: #111827; border: 1px solid rgba(0, 229, 153, 0.3); border-radius: 12px;
      padding: 28px; max-width: 440px; width: 100%; box-shadow: 0 12px 36px rgba(0, 0, 0, 0.6);
      color: #F3F6FA; font-family: 'Plus Jakarta Sans', sans-serif;
    `;

    modal.innerHTML = `
      <h3 style="margin-top: 0; margin-bottom: 8px; font-size: 1.25rem; font-weight: 700; color: #F3F6FA;">Restablecer Contraseña</h3>
      <p style="margin-bottom: 20px; font-size: 0.875rem; color: #94A3B8; line-height: 1.4;">
        Ingrese su correo electrónico registrado en <strong>Comunidad Sierra Plaza</strong>. Le enviaremos un enlace seguro para generar una nueva clave.
      </p>
      <div style="margin-bottom: 16px;">
        <label style="display: block; font-size: 0.8rem; font-weight: 600; margin-bottom: 6px; color: #E2E8F0;">Correo electrónico</label>
        <input type="email" id="reset-email-field" value="${initialEmail}" placeholder="ej: residente504@sierraplaza.cl" style="
          width: 100%; box-sizing: border-box; padding: 10px 14px; background: rgba(15, 23, 42, 0.85);
          border: 1px solid rgba(148, 163, 184, 0.25); border-radius: 8px; color: #F3F6FA; font-size: 0.95rem; outline: none;
        " />
      </div>
      <div id="reset-modal-status" style="display: none; margin-bottom: 16px; font-size: 0.85rem; padding: 10px; border-radius: 6px;"></div>
      <div style="display: flex; justify-content: flex-end; gap: 10px;">
        <button id="reset-cancel-btn" style="
          background: transparent; border: 1px solid rgba(148, 163, 184, 0.3); color: #94A3B8;
          padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; cursor: pointer; font-weight: 500;
        ">Cancelar</button>
        <button id="reset-submit-btn" style="
          background: linear-gradient(135deg, #00E599 0%, #059669 100%); border: none; color: #020806;
          padding: 8px 18px; border-radius: 6px; font-size: 0.875rem; cursor: pointer; font-weight: 700;
        ">Enviar enlace</button>
      </div>
    `;

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    const emailField = document.getElementById('reset-email-field');
    const statusDiv = document.getElementById('reset-modal-status');
    const submitBtn = document.getElementById('reset-submit-btn');
    const cancelBtn = document.getElementById('reset-cancel-btn');

    cancelBtn.onclick = function () {
      overlay.remove();
    };

    submitBtn.onclick = async function () {
      const targetEmail = emailField.value.trim();
      if (!targetEmail || !targetEmail.includes('@')) {
        statusDiv.style.display = 'block';
        statusDiv.style.background = 'rgba(239, 68, 68, 0.15)';
        statusDiv.style.color = '#F87171';
        statusDiv.style.border = '1px solid rgba(239, 68, 68, 0.3)';
        statusDiv.innerText = 'Por favor ingrese un correo válido.';
        return;
      }

      submitBtn.disabled = true;
      submitBtn.innerText = 'Enviando...';
      submitBtn.style.opacity = '0.7';

      try {
        const response = await fetch('/auth/reset-password', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: targetEmail }),
        });
        const data = await response.json();

        statusDiv.style.display = 'block';
        if (data.success) {
          statusDiv.style.background = 'rgba(0, 229, 153, 0.15)';
          statusDiv.style.color = '#00E599';
          statusDiv.style.border = '1px solid rgba(0, 229, 153, 0.3)';
          statusDiv.innerText = data.message;
          submitBtn.style.display = 'none';
          cancelBtn.innerText = 'Cerrar';
        } else {
          statusDiv.style.background = 'rgba(239, 68, 68, 0.15)';
          statusDiv.style.color = '#F87171';
          statusDiv.style.border = '1px solid rgba(239, 68, 68, 0.3)';
          statusDiv.innerText = data.message || 'Error al procesar la solicitud.';
          submitBtn.disabled = false;
          submitBtn.innerText = 'Reintentar';
          submitBtn.style.opacity = '1';
        }
      } catch (err) {
        statusDiv.style.display = 'block';
        statusDiv.style.background = 'rgba(239, 68, 68, 0.15)';
        statusDiv.style.color = '#F87171';
        statusDiv.style.border = '1px solid rgba(239, 68, 68, 0.3)';
        statusDiv.innerText = 'Error de conexión. Intente nuevamente.';
        submitBtn.disabled = false;
        submitBtn.innerText = 'Reintentar';
        submitBtn.style.opacity = '1';
      }
    };
  }

  // Observe DOM modifications to inject the link once Chainlit finishes rendering the login form
  const observer = new MutationObserver(function () {
    if (document.querySelector('input[type="password"]') && !document.getElementById('forgot-password-container')) {
      initPasswordResetLink();
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });
  window.addEventListener('DOMContentLoaded', initPasswordResetLink);
  initPasswordResetLink();
})();
