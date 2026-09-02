(function () {
  "use strict";

  const searchForm = document.getElementById("search-form");
  const sourceInput = document.getElementById("source");
  const destinationInput = document.getElementById("destination");
  const sourceList = document.getElementById("source-list");
  const destinationList = document.getElementById("destination-list");

  const resultsSection = document.getElementById("results-section");
  const resultsSummary = document.getElementById("results-summary");
  const resultsList = document.getElementById("results-list");

  const observationForm = document.getElementById("observation-form");
  const obsRouteSelect = document.getElementById("obs-route");
  const observationStatus = document.getElementById("observation-status");

  const MODE_LABELS = {
    bus: "Bus",
    tempo: "Tempo",
    metro: "Metro",
    "shared-auto": "Shared auto",
  };

  const STATUS_LABELS = {
    running: "In service",
    upcoming: "Starts later today",
    ended_for_today: "Next departure tomorrow",
  };

  init();

  function init() {
    loadRouteOptions();
    searchForm.addEventListener("submit", handleSearch);
    observationForm.addEventListener("submit", handleObservationSubmit);
  }

  // ---------- /routes/options ----------

  function loadRouteOptions() {
    fetch("/routes/options")
      .then((res) => res.json())
      .then((data) => {
        if (data.status !== "success") return;
        fillDatalist(sourceList, data.sources);
        fillDatalist(destinationList, data.destinations);
      })
      .catch(() => { // Autocomplete is a nice-to-have; searching still works without it.
      });
  }

  function fillDatalist(listEl, values) {
    listEl.innerHTML = "";
    (values || []).forEach((value) => {
      const opt = document.createElement("option");
      opt.value = value;
      listEl.appendChild(opt);
    });
  }

  // ---------- /search ----------

  function handleSearch(event) {
    event.preventDefault();

    const source = sourceInput.value.trim();
    const destination = destinationInput.value.trim();
    if (!source || !destination) return;

    const submitBtn = searchForm.querySelector("button[type=submit]");
    submitBtn.disabled = true;
    submitBtn.textContent = "Searching…"; 
    
 const params = new URLSearchParams({ source, destination });

    fetch(`/search?${params.toString()}`)
      .then((res) => res.json())
      .then((data) => {
        resultsSection.hidden = false;
        if (data.status !== "success") {
          renderError(data.message || "Something went wrong while searching.");
          return;
        }
        renderResults(data.routes, source, destination);
      })
      .catch(() => {
        resultsSection.hidden = false;
        renderError("Couldn't reach the server. Check your connection and try again.");
      })
      .finally(() => {
        submitBtn.disabled = false;
        submitBtn.textContent = "Search routes";
      });
  }

  function renderError(message) {
    resultsSummary.textContent = "";
    resultsList.innerHTML = `<p class="error-state">${escapeHtml(message)}</p>`;
  }

  function renderResults(routes, source, destination) {
    populateRouteSelect([]);

    if (!routes || routes.length === 0) {
      resultsSummary.textContent = "";
      resultsList.innerHTML = `<p class="empty-state">No routes found between "${escapeHtml(
        source
      )}" and "${escapeHtml(destination)}". Try a broader term, like just the area name.</p>`;
      return;
    }

    resultsSummary.textContent = `${routes.length} route${routes.length === 1 ? "" : "s"} found`;
    resultsList.innerHTML = "";

    routes.forEach((route) => {
      resultsList.appendChild(buildTicket(route));
    });

    populateRouteSelect(routes);
  }

  function buildTicket(route) {
    const ticket = document.createElement("article");
    ticket.className = "ticket";
    ticket.setAttribute("data-status", route.service_status);

    const modeLabel = MODE_LABELS[route.mode] || route.mode;
    const statusLabel = STATUS_LABELS[route.service_status] || route.service_status;
    const timetableLabel = (route.timetable || []).join(" · ") || "No timetable available";

    ticket.innerHTML = `
      <div class="ticket-route">
        <p class="ticket-name">${escapeHtml(route.route_name)}</p>
        <p class="ticket-mode">${escapeHtml(modeLabel)} &middot; scheduled service</p>
        <p class="ticket-timetable"><strong>Timetable:</strong> ${escapeHtml(timetableLabel)}</p>
        <button type="button" class="ticket-report" data-route-id="${route.id}" data-route-name="${escapeHtml(route.route_name
    )}">Report a delay</button>
      </div>
      <div class="ticket-time">
        <span class="ticket-clock">${escapeHtml(route.next_departure)}</span>
        <span class="ticket-status">${escapeHtml(statusLabel)}</span>
      </div>
    `;

    ticket.querySelector(".ticket-report").addEventListener("click", (e) => {
      const btn = e.currentTarget;
      obsRouteSelect.value = btn.getAttribute("data-route-id");
      document.getElementById("observation-section").scrollIntoView({ behavior: "smooth", block: "start" });
      document.getElementById("obs-delay").focus();
    });

    return ticket;
  }
  // ---------- observation form ----------

  function populateRouteSelect(routes) {
    obsRouteSelect.innerHTML = "";

    if (!routes || routes.length === 0) return;
    routes.forEach((route, index) => {
      const opt = document.createElement("option");
      opt.value = route.id;
      opt.textContent = route.route_name;
      if (index === 0) opt.selected = true;
      obsRouteSelect.appendChild(opt);
    });
  }

  function handleObservationSubmit(event) {
    event.preventDefault();

    const routeId = parseInt(obsRouteSelect.value, 10);
    const delayInput = document.getElementById("obs-delay");
    const delayMinutes = parseInt(delayInput.value, 10);
    const note = document.getElementById("obs-note").value.trim();

    if (!routeId || Number.isNaN(delayMinutes)) {
      setObservationStatus("Pick a route and enter a delay in minutes.", "error");
      return;
    }

    const submitBtn = observationForm.querySelector("button[type=submit]");
    submitBtn.disabled = true;
    submitBtn.textContent = "Submitting…";
    setObservationStatus("", null);

    fetch("/submit-observation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ route_id: routeId, delay_minutes: delayMinutes, note }),
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (ok && data.status === "success") {
          setObservationStatus("Report submitted.", "success");
          observationForm.reset();
        } else {
          setObservationStatus(data.message || "Couldn't submit that observation.", "error");
        }
      })
      .catch(() => {
        setObservationStatus("Couldn't reach the server. Check your connection and try again.", "error");
      })
      .finally(() => {
        submitBtn.disabled = false;
        submitBtn.textContent = "Submit report";
      });
  }

  function setObservationStatus(message, kind) {
    observationStatus.textContent = message;
    if (kind) {
      observationStatus.setAttribute("data-kind", kind);
    } else {
      observationStatus.removeAttribute("data-kind");
    }
  }

  // ---------- utils ----------

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
})();