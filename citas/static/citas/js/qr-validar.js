/**
 * Parsea payload de QR de citas (HU-4): /citas/validar/{id}/{token}/
 */
window.parseQrCita = function (decodedText) {
  if (!decodedText) return null;
  const withToken = String(decodedText).match(/validar\/(\d+)\/([^/\s?#]+)/i);
  if (withToken) {
    return { citaId: withToken[1], token: withToken[2] };
  }
  return null;
};

window.enviarValidacionQr = function (citaId, token, csrfToken) {
  const body = new URLSearchParams();
  body.set('token', token);
  return fetch('/citas/validar-qr/' + citaId + '/', {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrfToken,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: body.toString(),
  }).then(function (r) { return r.json(); });
};
