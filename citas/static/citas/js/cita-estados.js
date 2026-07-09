/**
 * Etiquetas y pills para los 4 estados operativos de una cita (+ cancelada).
 */
(function () {
  var CONFIG = {
    PENDIENTE: { label: 'Pendiente', cls: 'pill-pend' },
    ASISTIDA: { label: 'Asistida', cls: 'pill-asist' },
    PAGADA: { label: 'Pagada', cls: 'pill-pagada' },
    FINALIZADA: { label: 'Finalizada', cls: 'pill-fin' },
    CANCELADA: { label: 'Cancelada', cls: 'pill-cancel' },
  };

  function pillHtml(estado) {
    var c = CONFIG[estado] || { label: estado, cls: 'pill-fin' };
    return '<span class="pill ' + c.cls + '">' + c.label + '</span>';
  }

  function actualizarPillEnFila(fila, estado) {
    if (!fila) return;
    fila.setAttribute('data-estado', estado);
    var holder = fila.querySelector('.pill-estado');
    if (holder) {
      holder.innerHTML = pillHtml(estado);
      return;
    }
    var celda = fila.querySelector('td:last-child');
    if (celda) celda.innerHTML = pillHtml(estado);
  }

  window.CitaEstados = {
    CONFIG: CONFIG,
    pillHtml: pillHtml,
    actualizarPillEnFila: actualizarPillEnFila,
  };
})();
