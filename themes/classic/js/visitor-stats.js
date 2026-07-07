/* ScholarScript Impact Stats
 * Animated counters for content stats (already in HTML) +
 * live total visitors from GoatCounter (footer).
 * 100% real data — no fake numbers, no projections.
 */
(function() {
  // Animate all .stat-number elements counting up from 0
  var numbers = document.querySelectorAll('.stat-number[data-target]');
  numbers.forEach(function(el) {
    var target = parseFloat(el.getAttribute('data-target'));
    if (isNaN(target) || target === 0) return;
    var isFloat = target % 1 !== 0;
    var duration = Math.min(2000, 800 + target * 3);
    var t0 = null;
    function step(ts) {
      if (!t0) t0 = ts;
      var p = Math.min((ts - t0) / duration, 1);
      var e = 1 - Math.pow(1 - p, 3);
      var val = start + (target - start) * e;
      el.textContent = isFloat ? val.toFixed(1) : Math.floor(val).toLocaleString();
      if (p < 1) requestAnimationFrame(step);
    }
    var start = 0;
    requestAnimationFrame(step);
  });

  // Fetch total unique visitors from GoatCounter
  var totalEl = document.getElementById('totalVisitors');
  var updatedEl = document.getElementById('statsUpdated');
  if (!totalEl) return;

  function displayTotal(count) {
    if (count !== null && count !== undefined) {
      totalEl.textContent = count.toLocaleString() + ' total visitors';
    } else {
      totalEl.textContent = 'tracking with GoatCounter';
    }
  }

  function setUpdated() {
    if (updatedEl) updatedEl.textContent = new Date().toLocaleDateString();
  }

  // Try cached build stats first
  var xhr = new XMLHttpRequest();
  xhr.open('GET', '/ScholarScript/data/visitor-stats.json?' + Date.now(), true);
  xhr.onload = function() {
    if (xhr.status === 200) {
      try {
        var data = JSON.parse(xhr.responseText);
        displayTotal(data.total);
        if (data.updated) updatedEl.textContent = new Date(data.updated).toLocaleDateString();
        return;
      } catch(e) {}
    }
    // Fallback: try GoatCounter API
    fetchGoatCounter();
  };
  xhr.onerror = function() { fetchGoatCounter(); };
  xhr.send();

  function fetchGoatCounter() {
    fetch('https://scholar.goatcounter.com/api/v0/stats/total')
      .then(function(r) { return r.ok ? r.json() : null; })
      .then(function(d) { displayTotal(d ? d.count : null); setUpdated(); })
      .catch(function() { displayTotal(null); setUpdated(); });
  }
})();
