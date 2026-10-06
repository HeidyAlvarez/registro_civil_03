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

  var mascota = document.querySelector('[data-mascota]');
  if (mascota) {
    var textoMascota = mascota.querySelector('[data-mascota-texto]');
    var frasesMascota = {
      idle: mascota.dataset.fraseIdle,
      pensando: mascota.dataset.frasePensando,
      hablando: mascota.dataset.fraseHablando,
      saludo: mascota.dataset.fraseSaludo,
    };
    var temporizadorMascota = 0;
    function fijarMascota(estado) {
      window.clearTimeout(temporizadorMascota);
      mascota.dataset.estado = estado;
      mascota.classList.toggle('is-saludo', estado === 'saludo');
      if (textoMascota && frasesMascota[estado]) {
        textoMascota.firstChild.textContent = frasesMascota[estado];
      }
      if (estado === 'hablando' || estado === 'saludo') {
        temporizadorMascota = window.setTimeout(function () { fijarMascota('idle'); }, 2800);
      }
    }
    window.addEventListener('ia-mascota-estado', function (evento) {
      fijarMascota(evento.detail || 'idle');
    });
    var robot = mascota.querySelector('[data-mascota-saludo]');
    if (robot) robot.addEventListener('click', function () { fijarMascota('saludo'); });
    var escena = mascota.querySelector('.rc-mascota-escena');
    var pupilas = mascota.querySelectorAll('.rc-pupila');
    if (escena) {
      escena.addEventListener('mousemove', function (evento) {
        var rect = escena.getBoundingClientRect();
        var x = ((evento.clientX - rect.left) / rect.width - 0.5) * 5;
        var y = ((evento.clientY - rect.top) / rect.height - 0.5) * 4;
        pupilas.forEach(function (pupila) {
          pupila.setAttribute('transform', 'translate(' + x + ' ' + y + ')');
        });
      });
      escena.addEventListener('mouseleave', function () {
        pupilas.forEach(function (pupila) { pupila.removeAttribute('transform'); });
      });
    }
    var campo = document.querySelector('.ia-asistente-page textarea');
    if (campo) {
      campo.addEventListener('focus', function () { mascota.classList.add('is-atento'); });
      campo.addEventListener('blur', function () { mascota.classList.remove('is-atento'); });
    }
    if (document.querySelector('.ia-burbuja--ciudadano, .ia-burbuja--personal')) fijarMascota('hablando');
    document.querySelectorAll('.ia-asistente-page form').forEach(function (formulario) {
      formulario.addEventListener('submit', function () { fijarMascota('pensando'); });
    });
  }

  window.addEventListener('pageshow', function (evento) {
    if (evento.persisted && document.body.classList.contains('ia-asistente-page')) {
      window.location.reload();
    }
  });
})();
