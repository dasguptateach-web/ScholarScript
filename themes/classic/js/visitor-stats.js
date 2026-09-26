/* ScholarScript live visitor counter.
 * Reads data/visitor-stats.json (kept fresh hourly by the Fetch Visitor Stats
 * workflow) and animates the #totalVisitors stat card on the homepage.
 */
(function() {
  var totalEl = document.getElementById('totalVisitors');
  if (!totalEl) return;

  var SOURCES = [
    'https://raw.githubusercontent.com/dasguptateach-web/ScholarScript/main/data/visitor-stats.json?' + Date.now(),
    '/ScholarScript/data/visitor-stats.json?' + Date.now()
  ];

  function animateTo(target) {
    var duration = Math.min(2000, 800 + target * 3);
    var t0 = null;
    function step(ts) {
      if (!t0) t0 = ts;
      var p = Math.min((ts - t0) / duration, 1);
      var e = 1 - Math.pow(1 - p, 3);
      totalEl.textContent = Math.floor(target * e).toLocaleString();
      if (p < 1) requestAnimationFrame(step);
      else totalEl.textContent = target.toLocaleString();
    }
    requestAnimationFrame(step);
  }

  function show(total) {
    totalEl.setAttribute('data-target', total);
    animateTo(total);
  }

  function load(i) {
    if (i >= SOURCES.length) return;
    var xhr = new XMLHttpRequest();
    xhr.open('GET', SOURCES[i], true);
    xhr.onload = function() {
      var total = null;
      if (xhr.status === 200) {
        try { total = JSON.parse(xhr.responseText).total; } catch (e) {}
      }
      if (total !== null && total !== undefined && total > 0) show(total);
      else load(i + 1);
    };
    xhr.onerror = function() { load(i + 1); };
    xhr.send();
  }

  load(0);
})();
