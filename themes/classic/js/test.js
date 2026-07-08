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
    answers: {},
    submitted: false,
    score: null,
    results: null,
  };

  function render() {
    if (state.submitted) {
      renderResults();
    } else {
      renderQuestions();
    }
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
      html += '<div class="test-question" data-qid="' + q.id + '" data-aos="fade-up">';
      html += '<div class="test-q-header"><span class="test-q-num">' + q.id + '.</span>';
      html += '<div class="test-q-text">' + escapeHtml(q.question) + '</div></div>';
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
    app.innerHTML = html;

    var form = document.getElementById('testForm');
    var radios = form.querySelectorAll('input[type="radio"]');
    for (var k = 0; k < radios.length; k++) {
      radios[k].addEventListener('change', function(e) {
        var name = e.target.name;
        var qid = parseInt(name.split('_')[1], 10);
        state.answers[qid] = e.target.value;
        updateProgress();
        var labels = form.querySelectorAll('.test-option');
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

    updateProgress();
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
      html += '<span class="test-review-q-text">' + escapeHtml(r.question) + '</span>';
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
    if (testData.marked_answers > 0) {
      html += '<button class="btn btn-primary" id="emailResultsBtn"><i class="fas fa-envelope"></i> Email Results</button>';
    }
    html += '</div>';
    html += '</div>';

    app.innerHTML = html;

    var emailBtn = document.getElementById('emailResultsBtn');
    if (emailBtn) {
      emailBtn.addEventListener('click', function() {
        emailResults();
      });
    }

    app.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function emailResults() {
    var subject = 'Test Results: ' + testData.title;
    var body = 'Test Results\n';
    body += '=============\n';
    body += 'Test: ' + testData.title + '\n';
    body += 'Date: ' + new Date().toLocaleDateString() + '\n';
    body += 'Score: ' + state.score + '/' + state.total + ' (' + Math.round((state.score/state.total)*100) + '%)\n';
    body += 'Attempted: ' + state.attempted + '\n';
    body += 'Correct: ' + state.score + '\n';
    body += 'Incorrect: ' + (state.attempted - state.score) + '\n';
    body += 'Unanswered: ' + (state.total - state.attempted) + '\n\n';
    body += 'Detailed Results:\n';
    for (var i = 0; i < state.results.length; i++) {
      var r = state.results[i];
      body += r.id + '. ' + r.question + '\n';
      body += '   Your answer: ' + (r.userAnswer || '—') + '\n';
      if (r.hasAnswer) body += '   Correct: ' + r.correctAnswer + '\n';
      body += '   ' + (r.isCorrect ? '✓ Correct' : (r.userAnswer ? '✗ Incorrect' : '— Unanswered')) + '\n\n';
    }
    body += '— Sent from ScholarScript';

    var mailto = 'mailto:?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
    window.open(mailto);
  }

  function escapeHtml(text) {
    if (!text) return '';
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  render();
})();
