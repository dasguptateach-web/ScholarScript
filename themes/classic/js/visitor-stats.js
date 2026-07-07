/* ScholarScript Real Visitor Stats
 * Live counter: today, this month, projected, this year, total.
 * Uses GoatCounter API + build-cached JSON fallback.
 * 100% real data — no fake numbers.
 */
(function() {
  var container = document.getElementById('visitorStats');
  if (!container) return;

  var API = 'https://scholar.goatcounter.com/api/v0';
  var CACHE_KEY = 'ss_visitor_cache';
  var CACHE_TTL = 3600000;

  function animate(el, start, end, duration) {
    if (!el) return;
    var t0 = null;
    function step(ts) {
      if (!t0) t0 = ts;
      var p = Math.min((ts - t0) / duration, 1);
      var e = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.floor(start + (end - start) * e).toLocaleString();
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function display(data) {
    if (!data) {
      container.innerHTML = '<div class="stat-placeholder">Loading visitor data...</div>';
      return;
    }
    var items = [
      { label: "Today", val: data.today || 0, icon: "users" },
      { label: "This Month", val: data.month || 0, icon: "calendar-day" },
      { label: "Projected", val: data.month_projection || 0, icon: "chart-line", note: "est." },
      { label: "This Year", val: data.year || 0, icon: "calendar" },
      { label: "All Time", val: data.total || 0, icon: "globe" },
    ];
    container.innerHTML = '';
    items.forEach(function(item) {
      var card = document.createElement('div');
      card.className = 'stat-item';
      card.innerHTML = '<div class="stat-icon"><i class="fas fa-' + item.icon + '"></i></div>' +
        '<div class="stat-number" data-target="' + item.val + '">0</div>' +
        '<div class="stat-label">' + item.label +
        (item.note ? ' <span class="stat-badge">' + item.note + '</span>' : '') + '</div>';
      container.appendChild(card);
      var num = card.querySelector('.stat-number');
      if (num) animate(num, 0, item.val, 1400);
    });
    if (data.daily_average) {
      var info = document.createElement('div');
      info.className = 'stat-footer';
      info.innerHTML = 'Based on real GoatCounter analytics &middot; avg ' +
        data.daily_average.toLocaleString() + ' visitors/day';
      container.appendChild(info);
    }
  }

  function loadBuildStats() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/ScholarScript/data/visitor-stats.json?' + Date.now(), true);
    xhr.onload = function() {
      if (xhr.status === 200) {
        try { display(JSON.parse(xhr.responseText)); return; } catch(e) {}
      }
      fetchLive();
    };
    xhr.onerror = fetchLive;
    xhr.send();
  }

  function fetchLive() {
    try {
      var cached = JSON.parse(localStorage.getItem(CACHE_KEY));
      if (cached && Date.now() - cached.ts < CACHE_TTL) { display(cached.data); return; }
    } catch(e) {}

    var today = new Date().toISOString().split('T')[0];
    var ms = new Date(); ms.setDate(1);
    var m = ms.toISOString().split('T')[0];
    var ys = new Date(new Date().getFullYear(), 0, 1);
    var y = ys.toISOString().split('T')[0];

    Promise.all([
      fetch(API + '/stats/total').then(function(r) { return r.ok ? r.json() : null; }).catch(function() { return null; }),
      fetch(API + '/stats?period=' + today).then(function(r) { return r.ok ? r.json() : null; }).catch(function() { return null; }),
      fetch(API + '/stats?period=' + m).then(function(r) { return r.ok ? r.json() : null; }).catch(function() { return null; }),
    ]).then(function(res) {
      var total = res[0] ? res[0].count : null;
      var td = res[1] ? res[1].count : null;
      var mo = res[2] ? res[2].count : null;
      if (total === null && td === null) { display(null); return; }

      var dom = new Date().getDate();
      var dim = new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).getDate();
      var doy = Math.floor((new Date() - ys) / 86400000) + 1;
      var diy = Math.floor((new Date(new Date().getFullYear() + 1, 0, 1) - ys) / 86400000);
      var avg = mo ? Math.round(mo / dom) : 0;
      var yr = mo && doy > 0 ? Math.round(mo / doy * diy) : 0;

      var data = {
        today: td || 0,
        month: mo || 0,
        year: yr || 0,
        total: total || 0,
        daily_average: avg,
        month_projection: avg * dim,
      };
      display(data);
      try { localStorage.setItem(CACHE_KEY, JSON.stringify({ data: data, ts: Date.now() })); } catch(e) {}
    }).catch(function() { display(null); });
  }

  loadBuildStats();
})();
