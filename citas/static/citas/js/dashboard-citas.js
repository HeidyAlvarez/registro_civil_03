/**
 * Actualización en tiempo real de citas del día en dashboards admin/oficial.
 */
(function () {
  function escHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function getCookie(name) {
    if (!document.cookie) return null;
    var parts = document.cookie.split(';');
    for (var i = 0; i < parts.length; i++) {
      var part = parts[i].trim();
      if (part.indexOf(name + '=') === 0) {
        return decodeURIComponent(part.substring(name.length + 1));
      }
    }
    return null;
  }

  function btnCancelarHtml(c) {
    if (!c.puede_cancelar) return '';
    return (
      '<button type="button" class="btn-cancelar-cita" data-cita-id="' + c.id + '" title="Cancelar cita">' +
      'Cancelar</button>'
    );
  }

  function renderFilasAdmin(citas, contenedor) {
    if (!contenedor) return;
    if (!citas.length) {
      contenedor.innerHTML = '<span class="pill-empty">No hay citas registradas para hoy.</span>';
      return;
    }
    contenedor.innerHTML = citas.map(function (c) {
      return (
        '<div class="cita-row" data-cita-id="' + c.id + '" data-estado="' + c.estado + '">' +
          '<span class="cita-hora">' + escHtml(c.hora) + '</span>' +
          '<span class="cita-nombre">' + escHtml(c.nombre) + '</span>' +
          '<span class="cita-tramite">' + escHtml(c.tramite) + '</span>' +
          '<span class="pill-estado">' + window.CitaEstados.pillHtml(c.estado) + '</span>' +
          btnCancelarHtml(c) +
        '</div>'
      );
    }).join('');
  }

  function renderTablaOficial(citas, tbody, emptyEl) {
    if (!tbody) return;
    if (!citas.length) {
      tbody.innerHTML = '';
      if (emptyEl) emptyEl.style.display = 'block';
      return;
    }
    if (emptyEl) emptyEl.style.display = 'none';
    tbody.innerHTML = citas.map(function (c) {
      return (
        '<tr data-cita-id="' + c.id + '" data-estado="' + c.estado + '">' +
          '<td><span class="folio">#' + c.id + '</span></td>' +
          '<td><span class="hora-badge">' + escHtml(c.hora) + '</span></td>' +
          '<td><div class="nombre">' + escHtml(c.nombre) + '</div><div class="curp">' + escHtml(c.curp) + '</div></td>' +
          '<td>' + escHtml(c.tramite) + '</td>' +
          '<td>' + window.CitaEstados.pillHtml(c.estado) + '</td>' +
          '<td>' + (btnCancelarHtml(c) || '<span class="cita-sin-accion">—</span>') + '</td>' +
        '</tr>'
      );
    }).join('');
  }

  function actualizarContadores(d) {
    var map = {
      'stat-citas-hoy': d.total_citas_hoy,
      'stat-pendientes': d.citas_pendientes,
      'stat-caja': d.citas_en_caja,
      'stat-pagadas': d.citas_pagadas,
      'stat-finalizadas': d.citas_finalizadas,
      'stat-ingresos': d.ingresos_hoy != null ? '$' + Number(d.ingresos_hoy).toFixed(2) : null,
    };
    Object.keys(map).forEach(function (id) {
      var el = document.getElementById(id);
      if (el && map[id] != null) el.textContent = map[id];
    });
  }

  function refrescarDashboard(opts) {
    var ts = Date.now();
    Promise.all([
      fetch('/citas/api/dashboard/?_=' + ts).then(function (r) { return r.json(); }),
      fetch('/citas/api/citas/?_=' + ts).then(function (r) { return r.json(); }),
    ]).then(function (results) {
      actualizarContadores(results[0]);
      if (opts.modo === 'admin') {
        if (opts.tbodyId) {
          renderTablaOficial(
            results[1].citas || [],
            document.getElementById(opts.tbodyId),
            document.getElementById(opts.emptyId)
          );
        } else {
          renderFilasAdmin(results[1].citas || [], document.getElementById(opts.listId));
        }
      } else if (opts.modo === 'oficial') {
        renderTablaOficial(
          results[1].citas || [],
          document.getElementById(opts.tbodyId),
          document.getElementById(opts.emptyId)
        );
      }
    }).catch(function () {});
  }

  function iniciarPolling(opts) {
    refrescarDashboard(opts);
    setInterval(function () { refrescarDashboard(opts); }, opts.intervalo || 8000);
  }

  function cancelarCita(citaId, opts, estado) {
    const esPagada = estado === 'PAGADA';
    const msg = esPagada
      ? '¿Cancelar la cita #' + citaId + '? Se descontará el pago registrado de los ingresos.'
      : '¿Cancelar la cita #' + citaId + '? El horario quedará disponible de nuevo.';
    if (!confirm(msg)) {
      return Promise.resolve(false);
    }
    return fetch('/citas/citas/cancelar/' + citaId + '/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
        'X-Requested-With': 'XMLHttpRequest',
      },
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (res.ok && res.data.ok) {
          if (res.data.message) alert(res.data.message);
          if (opts) refrescarDashboard(opts);
          return true;
        }
        alert(res.data.error || res.data.message || 'No se pudo cancelar la cita.');
        return false;
      })
      .catch(function () {
        alert('Error de conexión al cancelar la cita.');
        return false;
      });
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.btn-cancelar-cita');
    if (!btn) return;
    var citaId = btn.getAttribute('data-cita-id');
    var fila = btn.closest('[data-cita-id]');
    var estado = fila ? fila.getAttribute('data-estado') : null;
    var root = btn.closest('[data-dashboard-citas]');
    var opts = null;
    if (root) {
      opts = {
        modo: root.getAttribute('data-dashboard-modo'),
        listId: root.getAttribute('data-list-id') || undefined,
        tbodyId: root.getAttribute('data-tbody-id') || undefined,
        emptyId: root.getAttribute('data-empty-id') || undefined,
      };
    }
    cancelarCita(citaId, opts, estado);
  });

  window.DashboardCitas = {
    refrescarDashboard: refrescarDashboard,
    iniciarPolling: iniciarPolling,
    cancelarCita: cancelarCita,
    actualizarFilaEstado: function (citaId, estado) {
      var fila = document.querySelector('[data-cita-id="' + citaId + '"]');
      if (window.CitaEstados) window.CitaEstados.actualizarPillEnFila(fila, estado);
      if (fila) {
        var btn = fila.querySelector('.btn-cancelar-cita');
        if (btn && !['PENDIENTE', 'ASISTIDA', 'PAGADA'].includes(estado)) btn.remove();
      }
    },
  };
})();
