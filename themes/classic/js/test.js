(function(){
  var app = document.getElementById('testApp');
  if (!app) return;
  var slug = app.getAttribute('data-test-slug');
  var script = document.getElementById('testData');
  if (!script) return;
  var testData;
  try { testData = JSON.parse(script.textContent); } catch(e) {
    app.innerHTML = '<div class="test-error"><i class="fas fa-exclamation-triangle"></i> Failed to load test data.</div>';
    return;
  }

  var state = {
    candidate: null,
    answers: {},
    submitted: false,
    score: null,
    results: null,
  };

  function render() {
    if (state.submitted) {
      renderResults();
    } else if (!state.candidate) {
      renderIntro();
    } else {
      renderQuestions();
    }
  }

  function renderIntro() {
    var html = '<div class="test-header">';
    html += '<h2><i class="fas fa-clipboard-check"></i> ' + escapeHtml(testData.title) + '</h2>';
    html += '<p class="test-meta">' + testData.questions.length + ' questions &middot; auto-scored</p>';
    if (testData.description) html += '<p class="test-desc">' + escapeHtml(testData.description) + '</p>';
    html += '</div>';
    html += '<form id="candidateForm" class="test-candidate-card" data-aos="fade-up">';
    html += '<h3><i class="fas fa-user"></i> Candidate Details</h3>';
    html += '<p class="test-candidate-note">Enter your name and email ID to begin. Your result will be submitted with these details.</p>';
    html += '<div class="test-candidate-fields">';
    html += '<label class="test-candidate-field"><span>Full Name <em>*</em></span>';
    html += '<input type="text" id="candidateName" placeholder="Your full name" autocomplete="name" required></label>';
    html += '<label class="test-candidate-field"><span>Email ID <em>*</em></span>';
    html += '<input type="email" id="candidateEmail" placeholder="you@example.com" autocomplete="email" required></label>';
    html += '</div>';
    html += '<div class="test-actions">';
    html += '<button type="submit" class="btn btn-primary test-submit-btn"><i class="fas fa-play"></i> Start Test</button>';
    html += '</div>';
    html += '<div id="candidateError" class="test-candidate-error"></div>';
    html += '</form>';
    app.innerHTML = html;

    var form = document.getElementById('candidateForm');
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      var name = (document.getElementById('candidateName').value || '').trim();
      var email = (document.getElementById('candidateEmail').value || '').trim();
      var err = document.getElementById('candidateError');
      if (!name) { err.textContent = 'Please enter your full name.'; return; }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { err.textContent = 'Please enter a valid email address.'; return; }
      err.textContent = '';
      state.candidate = { name: name, email: email };
      renderQuestions();
    });
  }

  function renderQuestions() {
    var html = '<div class="test-header">';
    html += '<h2><i class="fas fa-check-circle"></i> ' + escapeHtml(testData.title) + '</h2>';
    html += '<p class="test-meta">' + testData.questions.length + ' questions';
    if (testData.marked_answers > 0) html += ' &middot; auto-scored';
    html += '</p>';
    html += '</div>';
    html += '<div class="test-progress-bar"><div class="test-progress-fill" id="testProgressFill" style="width:0%"></div></div>';
    html += '<form id="testForm" class="test-form">';

    var qs = testData.questions;
    for (var i = 0; i < qs.length; i++) {
      var q = qs[i];
      var answered = state.answers[q.id] || '';
      var labels = ['A', 'B', 'C', 'D'];
      html += '<div class="test-question" id="q-' + q.id + '" data-qid="' + q.id + '" data-aos="fade-up">';
      html += '<div class="test-q-header"><span class="test-q-num">' + q.id + '.</span>';
      html += '<div class="test-q-text">' + renderQText(q.question) + '</div></div>';
      html += '<div class="test-options">';
      for (var j = 0; j < q.options.length; j++) {
        var val = labels[j];
        var checked = answered === val ? ' checked' : '';
        html += '<label class="test-option' + (checked ? ' selected' : '') + '">';
        html += '<input type="radio" name="q_' + q.id + '" value="' + val + '"' + checked + '>';
        html += '<span class="test-opt-letter">' + val + '</span>';
        html += '<span class="test-opt-text">' + escapeHtml(q.options[j]) + '</span>';
        html += '</label>';
      }
      html += '</div></div>';
    }

    html += '<div class="test-actions">';
    html += '<button type="submit" class="btn btn-primary test-submit-btn"><i class="fas fa-check-circle"></i> Submit &amp; See Results</button>';
    html += '</div>';
    html += '</form>';

    // Add palette
    html += '<button class="test-palette-btn" id="testPaletteBtn" title="Question Navigator"><i class="fas fa-th"></i></button>';
    html += '<div class="test-palette" id="testPalette">';
    html += '<div class="test-palette-header"><span>Question Navigator</span><button id="testPaletteClose" class="test-palette-close"><i class="fas fa-times"></i></button></div>';
    html += '<div class="test-palette-grid" id="testPaletteGrid">';
    for (var i = 0; i < qs.length; i++) {
      var q = qs[i];
      var statusClass = state.answers[q.id] ? 'qp-answered' : 'qp-unanswered';
      html += '<button class="test-palette-num ' + statusClass + '" data-qid="' + q.id + '">' + q.id + '</button>';
    }
    html += '</div></div>';

    app.innerHTML = html;

    var form = document.getElementById('testForm');
    var radios = form.querySelectorAll('input[type="radio"]');
    for (var k = 0; k < radios.length; k++) {
      radios[k].addEventListener('change', function(e) {
        var name = e.target.name;
        var qid = parseInt(name.split('_')[1], 10);
        state.answers[qid] = e.target.value;
        updateProgress();
        updatePalette();
        var parent = e.target.closest('.test-options');
        if (parent) {
          parent.querySelectorAll('.test-option').forEach(function(lbl) {
            lbl.classList.toggle('selected', lbl.querySelector('input').checked);
          });
        }
      });
    }

    form.addEventListener('submit', function(e) {
      e.preventDefault();
      submitTest();
    });

    setupPalette();
    updateProgress();
  }

  function setupPalette() {
    var btn = document.getElementById('testPaletteBtn');
    var panel = document.getElementById('testPalette');
    var closeBtn = document.getElementById('testPaletteClose');
    var grid = document.getElementById('testPaletteGrid');
    if (!btn || !panel) return;

    btn.addEventListener('click', function() {
      panel.classList.toggle('active');
    });

    if (closeBtn) {
      closeBtn.addEventListener('click', function() {
        panel.classList.remove('active');
      });
    }

    if (grid) {
      grid.addEventListener('click', function(e) {
        var target = e.target.closest('.test-palette-num');
        if (!target) return;
        var qid = target.getAttribute('data-qid');
        var el = document.getElementById('q-' + qid);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          panel.classList.remove('active');
        }
      });
    }
  }

  function updatePalette() {
    var grid = document.getElementById('testPaletteGrid');
    if (!grid) return;
    var btns = grid.querySelectorAll('.test-palette-num');
    for (var i = 0; i < btns.length; i++) {
      var qid = btns[i].getAttribute('data-qid');
      btns[i].className = 'test-palette-num ' + (state.answers[qid] ? 'qp-answered' : 'qp-unanswered');
    }
  }

  function updateProgress() {
    var total = testData.questions.length;
    var answered = 0;
    for (var i = 0; i < total; i++) {
      if (state.answers[testData.questions[i].id]) answered++;
    }
    var pct = total > 0 ? Math.round((answered / total) * 100) : 0;
    var fill = document.getElementById('testProgressFill');
    if (fill) fill.style.width = pct + '%';
  }

  function submitTest() {
    var qs = testData.questions;
    var total = qs.length;
    var attempted = 0;
    var correct = 0;
    var results = [];

    for (var i = 0; i < total; i++) {
      var q = qs[i];
      var userAns = state.answers[q.id] || null;
      var isCorrect = userAns && userAns === q.answer;
      if (userAns) attempted++;
      if (isCorrect) correct++;
      results.push({
        id: q.id,
        question: q.question,
        options: q.options,
        userAnswer: userAns,
        correctAnswer: q.answer,
        isCorrect: isCorrect,
        hasAnswer: !!q.answer,
      });
    }

    state.submitted = true;
    state.score = correct;
    state.total = total;
    state.attempted = attempted;
    state.results = results;

    // Track test attempt in GoatCounter
    try {
      if (window.goatcounter && window.goatcounter.count) {
        window.goatcounter.count({
          event: true,
          path: '/test/' + slug + '/submit',
          title: testData.title + ' — Score: ' + correct + '/' + total,
        });
      }
    } catch(e) {}

    renderResults();
  }

  function renderResults() {
    var total = state.total;
    var correct = state.score;
    var attempted = state.attempted;
    var pct = total > 0 ? Math.round((correct / total) * 100) : 0;
    var grade = pct >= 90 ? 'A+' : pct >= 80 ? 'A' : pct >= 70 ? 'B' : pct >= 60 ? 'C' : pct >= 50 ? 'D' : 'F';
    var gradeClass = pct >= 70 ? 'grade-pass' : pct >= 50 ? 'grade-average' : 'grade-fail';

    var html = '<div class="test-results" data-aos="fade-up">';
    html += '<div class="test-results-header">';
    html += '<h2><i class="fas fa-check-circle"></i> Your Results</h2>';
    if (state.candidate) {
      html += '<p class="test-candidate-chip"><i class="fas fa-user"></i> ' + escapeHtml(state.candidate.name) + ' &lt;' + escapeHtml(state.candidate.email) + '&gt;</p>';
    }
    html += '</div>';

    html += '<div class="test-score-card ' + gradeClass + '" data-aos="fade-up">';
    html += '<div class="test-score-circle">';
    html += '<span class="test-score-pct">' + pct + '%</span>';
    html += '<span class="test-score-grade">' + grade + '</span>';
    html += '</div>';
    html += '<div class="test-score-details">';
    html += '<div class="test-score-row"><span>Correct</span><span class="score-green">' + correct + '</span></div>';
    html += '<div class="test-score-row"><span>Incorrect</span><span class="score-red">' + (attempted - correct) + '</span></div>';
    html += '<div class="test-score-row"><span>Unanswered</span><span class="score-gray">' + (total - attempted) + '</span></div>';
    html += '<div class="test-score-row test-score-total"><span>Total</span><span>' + total + '</span></div>';
    html += '</div>';
    html += '</div>';

    html += '<div class="test-review">';
    html += '<h3><i class="fas fa-list"></i> Review Answers</h3>';
    for (var i = 0; i < state.results.length; i++) {
      var r = state.results[i];
      var labels = ['A', 'B', 'C', 'D'];
      var statusClass = r.isCorrect ? 'q-correct' : (r.userAnswer ? 'q-incorrect' : 'q-unanswered');
      var statusIcon = r.isCorrect ? 'fa-check-circle' : (r.userAnswer ? 'fa-times-circle' : 'fa-minus-circle');
      html += '<div class="test-review-q ' + statusClass + '" data-aos="fade-up">';
      html += '<div class="test-review-q-header">';
      html += '<span class="test-review-q-num">' + r.id + '.</span>';
      html += '<span class="test-review-q-text">' + renderQText(r.question) + '</span>';
      html += '<span class="test-review-status"><i class="fas ' + statusIcon + '"></i></span>';
      html += '</div>';
      html += '<div class="test-review-options">';
      for (var j = 0; j < r.options.length; j++) {
        var val = labels[j];
        var optClass = '';
        if (val === r.correctAnswer) optClass = ' opt-correct';
        else if (val === r.userAnswer && val !== r.correctAnswer) optClass = ' opt-wrong';
        html += '<div class="test-review-opt' + optClass + '">';
        html += '<span class="test-opt-letter">' + val + '</span>';
        html += '<span class="test-opt-text">' + escapeHtml(r.options[j]) + '</span>';
        if (val === r.correctAnswer) html += ' <i class="fas fa-check" style="color:var(--green);font-size:0.75rem;"></i>';
        else if (val === r.userAnswer && val !== r.correctAnswer) html += ' <i class="fas fa-times" style="color:var(--red);font-size:0.75rem;"></i>';
        html += '</div>';
      }
      html += '</div></div>';
    }
    html += '</div>';

    html += '<div class="test-actions">';
    html += '<button class="btn btn-secondary" onclick="location.reload()"><i class="fas fa-redo"></i> Retake Test</button>';
    html += '</div>';
    html += '<div id="emailStatus" class="test-email-status"></div>';
    html += '</div>';

    app.innerHTML = html;
    app.scrollIntoView({ behavior: 'smooth', block: 'start' });

    sendResultsEmail();
  }

  function sendResultsEmail() {
    var email = app.getAttribute('data-email');
    if (!email) {
      document.getElementById('emailStatus').innerHTML = '<i class="fas fa-info-circle"></i> No email configured for test results. Set owner_email in config.yaml.';
      return;
    }

    var pct = Math.round((state.score / state.total) * 100);
    var cand = state.candidate || { name: 'Unknown Candidate', email: 'not-provided' };
    var message = 'Test Results\n';
    message += '=============\n';
    message += 'Candidate Name: ' + cand.name + '\n';
    message += 'Candidate Email: ' + cand.email + '\n';
    message += 'Test: ' + testData.title + '\n';
    message += 'URL: ' + window.location.href + '\n';
    message += 'Date: ' + new Date().toLocaleDateString() + '\n';
    message += 'Score: ' + state.score + '/' + state.total + ' (' + pct + '%)\n';
    message += 'Attempted: ' + state.attempted + '\n';
    message += 'Correct: ' + state.score + '\n';
    message += 'Incorrect: ' + (state.attempted - state.score) + '\n';
    message += 'Unanswered: ' + (state.total - state.attempted) + '\n\n';
    message += 'Detailed Results:\n';
    for (var i = 0; i < state.results.length; i++) {
      var r = state.results[i];
      message += r.id + '. ' + r.question + '\n';
      message += '   Your answer: ' + (r.userAnswer || '—') + '\n';
      if (r.hasAnswer) message += '   Correct: ' + r.correctAnswer + '\n';
      message += '   ' + (r.isCorrect ? 'Correct' : (r.userAnswer ? 'Incorrect' : 'Unanswered')) + '\n\n';
    }
    message += '— Sent from ScholarScript';

    var statusEl = document.getElementById('emailStatus');
    statusEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending results to ' + email + '...';

    var xhr = new XMLHttpRequest();
    xhr.open('POST', 'https://formsubmit.co/ajax/' + encodeURIComponent(email), true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.setRequestHeader('Accept', 'application/json');
    xhr.onload = function() {
      if (xhr.status === 200) {
        statusEl.innerHTML = '<i class="fas fa-check-circle" style="color:var(--green)"></i> Results sent to ' + email;
      } else {
        statusEl.innerHTML = '<i class="fas fa-exclamation-triangle" style="color:var(--gold)"></i> Could not auto-send. Please copy your score: ' + pct + '% (' + state.score + '/' + state.total + ')';
      }
    };
    xhr.onerror = function() {
      statusEl.innerHTML = '<i class="fas fa-exclamation-triangle" style="color:var(--gold)"></i> Could not auto-send. ' +
        'Please email your score manually: ' + pct + '% (' + state.score + '/' + state.total + ')';
    };
    xhr.send(JSON.stringify({
      _subject: 'Test Results: ' + testData.title + ' — ' + cand.name + ' (' + pct + '%)',
      _captcha: 'false',
      _replyto: cand.email,
      name: cand.name,
      email: cand.email,
      message: message,
      score: state.score + '/' + state.total,
      percentage: pct + '%',
      candidate_name: cand.name,
      candidate_email: cand.email,
    }));
  }

  function escapeHtml(text) {
    if (!text) return '';
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function renderQText(text) {
    return escapeHtml(text).replace(/\n/g, '<br>');
  }

  render();
})();
