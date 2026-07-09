/**
 * Escáner QR ligero (video + jsQR). Sin UI extra de librerías externas.
 */
window.RegistroQR = (function () {
  let stream = null;
  let video = null;
  let animId = null;
  let canvas = null;
  let ctx = null;
  let running = false;
  let lastScan = 0;

  function stop() {
    running = false;
    if (animId) {
      cancelAnimationFrame(animId);
      animId = null;
    }
    if (stream) {
      stream.getTracks().forEach(function (t) { t.stop(); });
      stream = null;
    }
    if (video) {
      video.srcObject = null;
      video = null;
    }
    canvas = null;
    ctx = null;
  }

  function start(container, onSuccess, onError) {
    if (!container) return;
    stop();
    container.innerHTML = '';

    video = document.createElement('video');
    video.setAttribute('playsinline', 'true');
    video.setAttribute('muted', 'true');
    video.className = 'qr-video';
    container.appendChild(video);

    canvas = document.createElement('canvas');
    ctx = canvas.getContext('2d', { willReadFrequently: true });

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      container.innerHTML = '<p class="qr-cam-error">Tu navegador no soporta acceso a la cámara.</p>';
      if (onError) onError(new Error('no mediaDevices'));
      return;
    }

    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
      .then(function (s) {
        stream = s;
        video.srcObject = s;
        return video.play();
      })
      .then(function () {
        running = true;
        tick(onSuccess);
      })
      .catch(function (err) {
        container.innerHTML = '<p class="qr-cam-error">No se pudo acceder a la cámara.<br>Verifica los permisos del navegador.</p>';
        if (onError) onError(err);
      });
  }

  function tick(onSuccess) {
    if (!running || !video) return;
    animId = requestAnimationFrame(function () { tick(onSuccess); });

    if (video.readyState !== video.HAVE_ENOUGH_DATA) return;
    var now = Date.now();
    if (now - lastScan < 200) return;
    lastScan = now;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    var img = ctx.getImageData(0, 0, canvas.width, canvas.height);
    if (typeof jsQR === 'undefined') return;
    var code = jsQR(img.data, img.width, img.height, { inversionAttempts: 'dontInvert' });
    if (code && code.data) {
      running = false;
      stop();
      onSuccess(code.data);
    }
  }

  return { start: start, stop: stop };
})();
