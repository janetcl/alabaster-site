// Alabaster Group: small, dependency-free page behaviour.

(function () {
  // Current time in New York, regardless of the visitor's time zone.
  function nowInNewYork() {
    return new Date(new Date().toLocaleString('en-US', { timeZone: 'America/New_York' }));
  }

  // Next Sunday (today, if it is Sunday) and the Sunday before it.
  var ny = nowInNewYork();
  var next = new Date(ny);
  next.setDate(ny.getDate() + ((7 - ny.getDay()) % 7));
  var last = new Date(next);
  last.setDate(next.getDate() - 7);

  var formats = {
    long: { month: 'long', day: 'numeric' },
    short: { month: 'short', day: 'numeric' },
    full: { weekday: 'long', month: 'long', day: 'numeric' }
  };

  document.querySelectorAll('[data-sunday]').forEach(function (el) {
    var fmt = formats[el.getAttribute('data-sunday')] || formats.long;
    el.textContent = next.toLocaleDateString('en-US', fmt);
  });

  // Livestream: use this Sunday's link once it is filled in (site.json),
  // otherwise keep the channel's /live link.
  document.querySelectorAll('[data-live-url]').forEach(function (el) {
    var url = el.getAttribute('data-live-url');
    var date = el.getAttribute('data-live-date');
    var nextIso = next.getFullYear() + '-' + String(next.getMonth() + 1).padStart(2, '0') + '-' + String(next.getDate()).padStart(2, '0');
    if (url && date === nextIso) el.setAttribute('href', url);
  });

  // Retreat registration deadline countdown.
  document.querySelectorAll('[data-deadline]').forEach(function (el) {
    var deadline = new Date(el.getAttribute('data-deadline'));
    if (deadline - new Date() < 0) {
      el.textContent = 'Registration open while space remains';
      return;
    }
    // Count calendar days in New York time, so "tomorrow" means tomorrow.
    var dayOf = function (d) {
      var x = new Date(d.toLocaleString('en-US', { timeZone: 'America/New_York' }));
      return Date.UTC(x.getFullYear(), x.getMonth(), x.getDate());
    };
    var days = Math.round((dayOf(deadline) - dayOf(new Date())) / 864e5);
    var when = days === 0 ? 'today' : days === 1 ? 'tomorrow' : 'in ' + days + ' days';
    el.textContent = 'Registration closes ' + when;
  });

  document.querySelectorAll('[data-year]').forEach(function (el) {
    el.textContent = String(new Date().getFullYear());
  });

  // Mobile menu.
  var toggle = document.querySelector('.menu-toggle');
  var nav = document.getElementById('site-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    });
  }
})();
