(function () {
  'use strict';

  function activarCarga(formulario) {
    if (formulario.dataset.enviando === '1') return false;
    formulario.dataset.enviando = '1';

    formulario.querySelectorAll('button[type="submit"]').forEach(function (boton) {
      boton.disabled = true;
    });

    var indicador = formulario.querySelector('.ia-loading');
    if (indicador) indicador.classList.add('is-visible');
    formulario.setAttribute('aria-busy', 'true');
    return true;
  }

  document.querySelectorAll('form[data-ia-loading]').forEach(function (formulario) {
    formulario.addEventListener('submit', function (evento) {
      var disparador = evento.submitter;
      var mensaje = disparador && disparador.dataset.confirm;
      if (mensaje && !window.confirm(mensaje)) {
        evento.preventDefault();
        return;
      }
      activarCarga(formulario);
    });
  });

  document.querySelectorAll('[data-confirm]').forEach(function (control) {
    if (control.closest('form[data-ia-loading]')) return;
    control.addEventListener('click', function (evento) {
      if (!window.confirm(control.dataset.confirm)) evento.preventDefault();
    });
  });

  var chat = document.querySelector('[data-ia-chat]');
  if (chat) chat.scrollTop = chat.scrollHeight;

  window.addEventListener('pageshow', function (evento) {
    if (evento.persisted && document.body.classList.contains('ia-asistente-page')) {
      window.location.reload();
    }
  });
})();
