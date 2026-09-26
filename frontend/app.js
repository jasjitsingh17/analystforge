(() => {
  "use strict";

  const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
  const panels = tabs.map((tab) => document.getElementById(tab.getAttribute("aria-controls"))).filter(Boolean);
  const homeView = document.getElementById("home-view");
  const sidebar = document.getElementById("tool-sidebar");
  const sidebarBackdrop = document.getElementById("sidebar-backdrop");
  const menuToggle = document.getElementById("menu-toggle");
  const sidebarClose = document.getElementById("sidebar-close");
  const sidebarHome = document.getElementById("sidebar-home");
  const topbarToolsButton = document.getElementById("topbar-tools-button");
  const heroExploreTools = document.getElementById("hero-explore-tools");
  const brandHomeLink = document.getElementById("brand-home-link");
  let activeViewId = "home-view";

  const routeMap = {
    "#valuation": "panel-ib",
    "#ma-execution": "panel-ma",
    "#equity-research": "panel-er",
    "#home": "home-view",
  };
  const hashMap = {
    "panel-ib": "#valuation",
    "panel-ma": "#ma-execution",
    "panel-er": "#equity-research",
    "home-view": "#home",
  };

  let sidebarCloseTimer = null;
  let sidebarOpenedAt = 0;

  function setSidebar(open) {
    if (!sidebar || !sidebarBackdrop || !menuToggle) return;

    if (sidebarCloseTimer !== null) {
      window.clearTimeout(sidebarCloseTimer);
      sidebarCloseTimer = null;
    }

    sidebar.classList.toggle("is-open", open);
    sidebar.setAttribute("aria-hidden", String(!open));
    menuToggle.setAttribute("aria-expanded", String(open));
    document.body.classList.toggle("sidebar-open", open);

    if (open) {
      sidebarOpenedAt = performance.now();
      sidebarBackdrop.hidden = false;
      requestAnimationFrame(() => {
        sidebarBackdrop.classList.add("is-visible");
        sidebarClose?.focus({ preventScroll: true });
      });
    } else {
      sidebarBackdrop.classList.remove("is-visible");
      sidebarCloseTimer = window.setTimeout(() => {
        if (!sidebar.classList.contains("is-open")) sidebarBackdrop.hidden = true;
        sidebarCloseTimer = null;
      }, 220);
    }
  }

  function applyView(viewId, moveFocus = false) {
    activeViewId = viewId;
    const isHome = viewId === "home-view";
    homeView.hidden = !isHome;
    panels.forEach((panel) => { panel.hidden = panel.id !== viewId; });
    tabs.forEach((tab) => {
      const isActive = tab.getAttribute("aria-controls") === viewId;
      tab.classList.toggle("is-active", isActive);
      tab.setAttribute("aria-selected", String(isActive));
      tab.tabIndex = isHome ? 0 : (isActive ? 0 : -1);
      if (isActive && moveFocus) tab.focus();
    });
    sidebarHome.classList.toggle("is-active", isHome);
    document.body.dataset.view = isHome ? "home" : viewId;
  }

  async function transitionTo(viewId, { moveFocus = false, pushHistory = true, preserveScroll = false } = {}) {
    if (!document.getElementById(viewId)) return;
    setSidebar(false);
    const current = activeViewId === "home-view" ? homeView : document.getElementById(activeViewId);
    const next = viewId === "home-view" ? homeView : document.getElementById(viewId);
    const swap = () => applyView(viewId, moveFocus);

    if (document.startViewTransition) {
      document.startViewTransition(swap);
    } else if (current && next && current !== next && current.animate) {
      try {
        await current.animate([
          { opacity: 1, transform: "translateY(0) scale(1)" },
          { opacity: 0, transform: "translateY(-8px) scale(.995)" },
        ], { duration: 160, easing: "ease-out" }).finished;
      } catch { /* animation cancellation is harmless */ }
      swap();
      try {
        next.animate([
          { opacity: 0, transform: "translateY(12px) scale(.992)" },
          { opacity: 1, transform: "translateY(0) scale(1)" },
        ], { duration: 330, easing: "cubic-bezier(.2,.8,.2,1)" });
      } catch { /* keep functional fallback */ }
    } else {
      swap();
    }

    if (!preserveScroll) window.scrollTo({ top: 0, behavior: "smooth" });
    if (pushHistory) history.pushState({ viewId }, "", hashMap[viewId] || "#home");
  }

  function activateTab(selected, moveFocus) {
    transitionTo(selected.getAttribute("aria-controls"), { moveFocus, pushHistory: true });
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activateTab(tab, false));
    tab.addEventListener("keydown", (event) => {
      const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
      if (!step) return;
      event.preventDefault();
      activateTab(tabs[(index + step + tabs.length) % tabs.length], true);
    });
  });

  [menuToggle, topbarToolsButton, heroExploreTools].filter(Boolean).forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      setSidebar(true);
    });
  });

  sidebar?.addEventListener("click", (event) => event.stopPropagation());
  sidebarClose?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    setSidebar(false);
    menuToggle?.focus({ preventScroll: true });
  });
  sidebarBackdrop?.addEventListener("click", () => {
    // Guard against Safari treating the opening click as a backdrop click.
    if (performance.now() - sidebarOpenedAt < 450) return;
    setSidebar(false);
  });
  sidebarHome.addEventListener("click", () => transitionTo("home-view"));
  brandHomeLink.addEventListener("click", (event) => { event.preventDefault(); transitionTo("home-view"); });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") setSidebar(false); });

  document.querySelectorAll("[data-open-tool]").forEach((button) => {
    button.addEventListener("click", () => transitionTo(button.dataset.openTool));
  });

  document.querySelectorAll("[data-home-anchor]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (activeViewId !== "home-view") await transitionTo("home-view");
      document.getElementById(button.dataset.homeAnchor)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  document.querySelectorAll("[data-scroll-rail]").forEach((button) => {
    button.addEventListener("click", () => {
      const rail = document.getElementById(button.dataset.scrollRail);
      if (!rail) return;
      const direction = Number(button.dataset.direction || 1);
      rail.scrollBy({ left: direction * Math.min(620, rail.clientWidth * .82), behavior: "smooth" });
    });
  });

  document.querySelectorAll(".tool-jump").forEach((button) => {
    button.addEventListener("click", () => document.getElementById(button.dataset.scrollTarget)?.scrollIntoView({ behavior: "smooth", block: "start" }));
  });

  const lightbox = document.getElementById("image-lightbox");
  const lightboxImage = document.getElementById("lightbox-image");
  const lightboxCaption = document.getElementById("lightbox-caption");
  const lightboxClose = document.getElementById("lightbox-close");
  function openLightbox(trigger) {
    lightboxImage.src = trigger.dataset.image;
    lightboxImage.alt = trigger.dataset.caption || "Illustrative output screenshot";
    lightboxCaption.textContent = trigger.dataset.caption || "Illustrative output";
    lightbox.hidden = false;
    lightbox.setAttribute("aria-hidden", "false");
    requestAnimationFrame(() => lightbox.classList.add("is-open"));
    lightboxClose.focus();
  }
  function closeLightbox() {
    lightbox.classList.remove("is-open");
    lightbox.setAttribute("aria-hidden", "true");
    window.setTimeout(() => { lightbox.hidden = true; lightboxImage.src = ""; }, 190);
  }
  document.querySelectorAll(".screenshot-open").forEach((trigger) => {
    trigger.addEventListener("click", () => openLightbox(trigger));
    trigger.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openLightbox(trigger); } });
  });
  lightboxClose.addEventListener("click", closeLightbox);
  lightbox.addEventListener("click", (event) => { if (event.target === lightbox) closeLightbox(); });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !lightbox.hidden) closeLightbox(); });

  window.addEventListener("popstate", () => {
    const viewId = routeMap[location.hash] || "home-view";
    transitionTo(viewId, { pushHistory: false });
  });

  const initialView = routeMap[location.hash] || "home-view";
  applyView(initialView, false);
  const form = document.getElementById("dcf-form");
  const runButton = document.getElementById("run-dcf");
  const downloadButton = document.getElementById("download-excel");
  const status = document.getElementById("dcf-status");
  const outputSubtitle = document.getElementById("output-subtitle");
  const analyticsSection = document.getElementById("analytics-section");
  const chartsSection = document.getElementById("charts-section");
  const forecastCard = document.getElementById("forecast-card");
  const sensitivityStatus = document.getElementById("sensitivity-status");
  let lastSuccessfulPayload = null;

  const outputs = {
    impliedSharePrice: document.getElementById("out-implied-price"),
    upsideDownside: document.getElementById("out-upside"),
    enterpriseValue: document.getElementById("out-enterprise-value"),
    equityValue: document.getElementById("out-equity-value"),
    currentPrice: document.getElementById("out-current-price"),
    wacc: document.getElementById("out-wacc"),
    terminalGrowth: document.getElementById("out-terminal-growth"),
    forecastPeriod: document.getElementById("out-forecast-period"),
    terminalValue: document.getElementById("out-terminal-value"),
    pvTerminal: document.getElementById("out-pv-terminal"),
  };

  function numberValue(id) { return Number(document.getElementById(id).value); }

  function buildPayload() {
    return {
      company_name: document.getElementById("company-name").value.trim(),
      ticker: document.getElementById("ticker").value.trim(),
      share_price: numberValue("share-price"),
      forecast_years: numberValue("forecast-years"),
      revenue_growth: numberValue("revenue-growth") / 100,
      ebitda_margin: numberValue("ebitda-margin") / 100,
      tax_rate: numberValue("tax-rate") / 100,
      wacc: numberValue("wacc") / 100,
      terminal_growth: numberValue("terminal-growth") / 100,
      net_debt: numberValue("net-debt"),
      shares_outstanding: numberValue("shares-outstanding"),
    };
  }

  const fmt = {
    price(value) {
      return Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    },
    whole(value) {
      return Number(value).toLocaleString(undefined, { maximumFractionDigits: 0 });
    },
    oneDecimal(value) {
      return Number(value).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    },
    percent(value, digits = 1) {
      return `${(Number(value) * 100).toFixed(digits)}%`;
    },
    upside(value) {
      const pct = Number(value) * 100;
      return pct < 0 ? `(${Math.abs(pct).toFixed(1)}%)` : `${pct.toFixed(1)}%`;
    },
    factor(value) { return Number(value).toFixed(3); },
  };

  function setStatus(message, kind = "") {
    status.textContent = message;
    status.classList.remove("is-success", "is-error");
    if (kind) status.classList.add(`is-${kind}`);
  }

  function setLoading(isLoading) {
    runButton.disabled = isLoading;
    runButton.textContent = isLoading ? "Running Valuation..." : "Run DCF Valuation";
  }

  function clearResults() {
    lastSuccessfulPayload = null;
    downloadButton.disabled = true;
    Object.values(outputs).forEach((el) => {
      el.textContent = "—";
      el.classList.remove("has-value", "value-positive", "value-negative");
    });
    outputSubtitle.textContent = "Run the DCF valuation to generate results.";
    analyticsSection.hidden = true;
    chartsSection.hidden = true;
    forecastCard.hidden = true;
    document.getElementById("dcf-bridge").replaceChildren();
    document.getElementById("sensitivity-wrap").replaceChildren();
    document.getElementById("operating-chart").replaceChildren();
    document.getElementById("discount-chart").replaceChildren();
    document.getElementById("forecast-table-body").replaceChildren();
    sensitivityStatus.textContent = "—";
  }

  function markValue(el) { el.classList.add("has-value"); }

  function renderHeadline(data, payload) {
    outputs.impliedSharePrice.textContent = fmt.price(data.implied_share_price);
    outputs.upsideDownside.textContent = fmt.upside(data.upside_downside);
    outputs.enterpriseValue.textContent = fmt.whole(data.enterprise_value);
    outputs.equityValue.textContent = fmt.whole(data.equity_value);
    outputs.currentPrice.textContent = fmt.price(data.current_share_price);
    outputs.wacc.textContent = fmt.percent(payload.wacc, 2);
    outputs.terminalGrowth.textContent = fmt.percent(payload.terminal_growth, 2);
    outputs.forecastPeriod.textContent = `${data.forecast_years} years`;
    outputs.terminalValue.textContent = fmt.whole(data.terminal_value);
    outputs.pvTerminal.textContent = fmt.whole(data.pv_terminal_value);

    Object.values(outputs).forEach(markValue);
    outputs.upsideDownside.classList.add(data.upside_downside >= 0 ? "value-positive" : "value-negative");
    outputSubtitle.textContent = `DCF valuation completed for ${data.company_name} (${data.ticker}) using the submitted assumptions.`;
  }

  function renderBridge(data) {
    const container = document.getElementById("dcf-bridge");
    const items = [
      ["PV of explicit UFCF", data.sum_pv_ufcf, ""],
      ["PV of terminal value", data.pv_terminal_value, "is-terminal"],
      ["Enterprise value", data.enterprise_value, ""],
      ["Less: net debt", Math.abs(data.net_debt), "is-net-debt"],
      ["Equity value", data.equity_value, "is-equity"],
    ];
    const maxValue = Math.max(...items.map((item) => Number(item[1])), 1);

    container.innerHTML = items.map(([label, value, className], index) => {
      const width = Math.max(2, Math.min(100, (Number(value) / maxValue) * 100));
      const divider = index === 2 || index === 3 ? '<hr class="bridge-divider">' : "";
      return `${divider}<div class="bridge-row ${className}">
        <div class="bridge-label">${label}</div>
        <div class="bridge-bar-track"><div class="bridge-bar" style="width:${width}%"></div></div>
        <div class="bridge-value">${fmt.whole(value)}</div>
      </div>`;
    }).join("");
  }

  function renderForecastTable(forecast) {
    document.getElementById("forecast-table-body").innerHTML = forecast.map((row) => `
      <tr>
        <td class="strong">Year ${row.year}</td>
        <td>${fmt.whole(row.revenue)}</td>
        <td>${fmt.whole(row.ebitda)}</td>
        <td>${fmt.whole(row.ebit)}</td>
        <td class="strong">${fmt.whole(row.ufcf)}</td>
        <td>${fmt.factor(row.discount_factor)}</td>
        <td class="strong">${fmt.whole(row.pv_ufcf)}</td>
      </tr>`).join("");
  }

  function chartGeometry(values, width = 640, height = 280) {
    const margin = { top: 18, right: 18, bottom: 38, left: 48 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;
    const max = Math.max(...values, 1) * 1.12;
    const y = (value) => margin.top + innerHeight - (Number(value) / max) * innerHeight;
    return { width, height, margin, innerWidth, innerHeight, max, y };
  }

  function svgGrid(g, tickCount = 4) {
    let markup = "";
    for (let i = 0; i <= tickCount; i += 1) {
      const value = g.max * (1 - i / tickCount);
      const y = g.margin.top + (g.innerHeight * i / tickCount);
      markup += `<line class="chart-gridline" x1="${g.margin.left}" y1="${y}" x2="${g.width - g.margin.right}" y2="${y}"></line>`;
      markup += `<text class="chart-label" x="${g.margin.left - 8}" y="${y + 4}" text-anchor="end">${compactNumber(value)}</text>`;
    }
    markup += `<line class="chart-axis" x1="${g.margin.left}" y1="${g.margin.top + g.innerHeight}" x2="${g.width - g.margin.right}" y2="${g.margin.top + g.innerHeight}"></line>`;
    return markup;
  }

  function compactNumber(value) {
    const abs = Math.abs(value);
    if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}m`;
    if (abs >= 1_000) return `${(value / 1_000).toFixed(abs >= 100_000 ? 0 : 1)}k`;
    return Math.round(value).toString();
  }

  function renderOperatingChart(forecast) {
    const container = document.getElementById("operating-chart");
    const values = forecast.flatMap((row) => [row.revenue, row.ebitda, row.ufcf]);
    const g = chartGeometry(values);
    const step = g.innerWidth / forecast.length;
    const barWidth = Math.min(48, step * 0.46);

    let bars = "";
    const ebitdaPoints = [];
    const ufcfPoints = [];
    forecast.forEach((row, i) => {
      const xCenter = g.margin.left + step * i + step / 2;
      const revY = g.y(row.revenue);
      bars += `<rect class="chart-bar-revenue" x="${xCenter - barWidth / 2}" y="${revY}" width="${barWidth}" height="${g.margin.top + g.innerHeight - revY}" rx="2"><title>Year ${row.year} Revenue: ${fmt.whole(row.revenue)}</title></rect>`;
      ebitdaPoints.push([xCenter, g.y(row.ebitda), row.ebitda]);
      ufcfPoints.push([xCenter, g.y(row.ufcf), row.ufcf]);
      bars += `<text class="chart-label" x="${xCenter}" y="${g.height - 14}" text-anchor="middle">Y${row.year}</text>`;
    });

    const path = (points) => points.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x},${y}`).join(" ");
    const dots = (points, cls, label) => points.map(([x, y, value], i) => `<circle class="${cls}" cx="${x}" cy="${y}" r="3.5"><title>Year ${forecast[i].year} ${label}: ${fmt.whole(value)}</title></circle>`).join("");

    container.innerHTML = `<svg viewBox="0 0 ${g.width} ${g.height}" role="img" aria-label="Operating forecast chart showing revenue, EBITDA and UFCF by year">
      ${svgGrid(g)}${bars}
      <path class="chart-line-ebitda" d="${path(ebitdaPoints)}"></path>
      <path class="chart-line-ufcf" d="${path(ufcfPoints)}"></path>
      ${dots(ebitdaPoints, "chart-dot-ebitda", "EBITDA")}
      ${dots(ufcfPoints, "chart-dot-ufcf", "UFCF")}
    </svg>`;
  }

  function renderDiscountChart(forecast) {
    const container = document.getElementById("discount-chart");
    const values = forecast.flatMap((row) => [row.ufcf, row.pv_ufcf]);
    const g = chartGeometry(values);
    const step = g.innerWidth / forecast.length;
    const groupWidth = Math.min(64, step * 0.68);
    const barWidth = groupWidth / 2 - 3;
    let markup = svgGrid(g);

    forecast.forEach((row, i) => {
      const xCenter = g.margin.left + step * i + step / 2;
      const uY = g.y(row.ufcf);
      const pY = g.y(row.pv_ufcf);
      markup += `<rect class="chart-bar-ufcf" x="${xCenter - groupWidth / 2}" y="${uY}" width="${barWidth}" height="${g.margin.top + g.innerHeight - uY}" rx="2"><title>Year ${row.year} UFCF: ${fmt.whole(row.ufcf)}</title></rect>`;
      markup += `<rect class="chart-bar-pv" x="${xCenter + 3}" y="${pY}" width="${barWidth}" height="${g.margin.top + g.innerHeight - pY}" rx="2"><title>Year ${row.year} PV of UFCF: ${fmt.whole(row.pv_ufcf)}</title></rect>`;
      markup += `<text class="chart-label" x="${xCenter}" y="${g.height - 14}" text-anchor="middle">Y${row.year}</text>`;
    });

    container.innerHTML = `<svg viewBox="0 0 ${g.width} ${g.height}" role="img" aria-label="Cash flow discounting chart comparing UFCF with present value of UFCF by year">${markup}</svg>`;
  }

  function heatClass(value, min, max) {
    if (value == null || max <= min) return "heat-3";
    const ratio = (value - min) / (max - min);
    if (ratio < 0.2) return "heat-1";
    if (ratio < 0.4) return "heat-2";
    if (ratio < 0.6) return "heat-3";
    if (ratio < 0.8) return "heat-4";
    return "heat-5";
  }

  function renderSensitivity(data) {
    const values = data.implied_share_prices.flat().filter((value) => value != null);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const header = data.wacc_values.map((value) => `<th>${fmt.percent(value, 1)}</th>`).join("");
    const rows = data.terminal_growth_values.map((growth, rowIndex) => {
      const cells = data.implied_share_prices[rowIndex].map((value, columnIndex) => {
        if (value == null) return '<td class="is-na">N/A</td>';
        const base = rowIndex === data.base_row && columnIndex === data.base_column ? " is-base" : "";
        return `<td class="${heatClass(value, min, max)}${base}">${fmt.price(value)}</td>`;
      }).join("");
      return `<tr><th>${fmt.percent(growth, 1)}</th>${cells}</tr>`;
    }).join("");

    document.getElementById("sensitivity-wrap").innerHTML = `<table class="sensitivity-table">
      <thead><tr><th class="axis-title">g \ WACC</th>${header}</tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  }

  async function loadSensitivity(payload) {
    sensitivityStatus.textContent = "Calculating...";
    try {
      const response = await fetch("/api/dcf/sensitivity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error("Sensitivity request failed");
      renderSensitivity(await response.json());
      sensitivityStatus.textContent = "5 × 5 matrix";
    } catch {
      document.getElementById("sensitivity-wrap").innerHTML = '<p class="chart-note">Sensitivity analysis could not be generated.</p>';
      sensitivityStatus.textContent = "Unavailable";
    }
  }

  function renderResults(data, payload) {
    renderHeadline(data, payload);
    renderBridge(data);
    renderForecastTable(data.forecast);
    renderOperatingChart(data.forecast);
    renderDiscountChart(data.forecast);
    analyticsSection.hidden = false;
    chartsSection.hidden = false;
    forecastCard.hidden = false;
    loadSensitivity(payload);
  }

  function extractValidationMessage(body) {
    if (!body || !Array.isArray(body.detail) || body.detail.length === 0) {
      return "Unable to run valuation. Please review the assumptions and try again.";
    }
    const message = body.detail[0]?.msg;
    return typeof message === "string" && message.length
      ? message.replace(/^Value error,\s*/i, "")
      : "Unable to run valuation. Please review the assumptions and try again.";
  }

  function filenameFromDisposition(disposition) {
    if (!disposition) return "DCF_Model.xlsx";
    const utf8 = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8) {
      try { return decodeURIComponent(utf8[1].replace(/["']/g, "")); } catch { /* fall through */ }
    }
    const basic = disposition.match(/filename="?([^";]+)"?/i);
    return basic ? basic[1] : "DCF_Model.xlsx";
  }

  async function downloadExcelModel() {
    if (!lastSuccessfulPayload) {
      setStatus("Run the DCF valuation before downloading the Excel model.", "error");
      return;
    }

    downloadButton.disabled = true;
    downloadButton.textContent = "Generating Excel...";
    setStatus("Generating professional Excel DCF model...");

    try {
      const response = await fetch("/api/dcf/excel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(lastSuccessfulPayload),
      });

      if (!response.ok) {
        if (response.status === 422) {
          let body = null;
          try { body = await response.json(); } catch { /* use generic message */ }
          setStatus(extractValidationMessage(body), "error");
          return;
        }
        setStatus("Unable to generate the Excel model. Please try again.", "error");
        return;
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filenameFromDisposition(response.headers.get("Content-Disposition"));
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setStatus("Excel DCF model downloaded successfully.", "success");
    } catch {
      setStatus("Unable to connect to the Excel generation service.", "error");
    } finally {
      downloadButton.textContent = "Download Excel Model";
      downloadButton.disabled = !lastSuccessfulPayload;
    }
  }

  downloadButton.addEventListener("click", downloadExcelModel);

  form.addEventListener("input", () => {
    if (!lastSuccessfulPayload) return;
    lastSuccessfulPayload = null;
    downloadButton.disabled = true;
    setStatus("Assumptions changed — rerun the DCF valuation before downloading Excel.");
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) { setStatus(""); return; }

    clearResults();
    setLoading(true);
    setStatus("Calculating DCF valuation...");
    const payload = buildPayload();

    try {
      const response = await fetch("/api/dcf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        if (response.status === 422) {
          let body = null;
          try { body = await response.json(); } catch { /* use generic validation message */ }
          setStatus(extractValidationMessage(body), "error");
          return;
        }
        setStatus("The valuation service returned an error. Please try again.", "error");
        return;
      }

      const data = await response.json();
      renderResults(data, payload);
      lastSuccessfulPayload = payload;
      downloadButton.disabled = false;
      setStatus("DCF valuation completed successfully. Excel model is ready to download.", "success");
    } catch {
      clearResults();
      setStatus("Unable to connect to the valuation service.", "error");
    } finally {
      setLoading(false);
    }
  });


  // ------------------------------------------------------------------------
  // Equity Research earnings-review workflow
  // ------------------------------------------------------------------------
  const erForm = document.getElementById("er-form");
  const erRunButton = document.getElementById("run-er");
  const erDownloadButton = document.getElementById("download-er-excel");
  const erReportButton = document.getElementById("open-er-report");
  const erStatus = document.getElementById("er-status");
  const erReport = document.getElementById("er-report");
  let lastSuccessfulERPayload = null;

  function erNumber(id) { return Number(document.getElementById(id).value); }
  function erText(id) { return document.getElementById(id).value.trim(); }

  function buildERPayload() {
    return {
      company_name: erText("er-company-name"),
      ticker: erText("er-ticker"),
      currency: erText("er-currency"),
      period: erText("er-period"),
      share_price: erNumber("er-share-price"),
      shares_outstanding: erNumber("er-shares-outstanding"),
      net_debt: erNumber("er-net-debt"),
      prior_revenue: erNumber("er-prior-revenue"),
      consensus_revenue: erNumber("er-consensus-revenue"),
      actual_revenue: erNumber("er-actual-revenue"),
      prior_ebitda: erNumber("er-prior-ebitda"),
      consensus_ebitda: erNumber("er-consensus-ebitda"),
      actual_ebitda: erNumber("er-actual-ebitda"),
      prior_eps: erNumber("er-prior-eps"),
      consensus_eps: erNumber("er-consensus-eps"),
      actual_eps: erNumber("er-actual-eps"),
      prior_fcf: erNumber("er-prior-fcf"),
      consensus_fcf: erNumber("er-consensus-fcf"),
      actual_fcf: erNumber("er-actual-fcf"),
      forward_revenue: erNumber("er-forward-revenue"),
      forward_ebitda: erNumber("er-forward-ebitda"),
      forward_eps: erNumber("er-forward-eps"),
      previous_revenue_guidance_low: erNumber("er-prev-rev-low"),
      previous_revenue_guidance_high: erNumber("er-prev-rev-high"),
      new_revenue_guidance_low: erNumber("er-new-rev-low"),
      new_revenue_guidance_high: erNumber("er-new-rev-high"),
      previous_ebitda_guidance_low: erNumber("er-prev-ebitda-low"),
      previous_ebitda_guidance_high: erNumber("er-prev-ebitda-high"),
      new_ebitda_guidance_low: erNumber("er-new-ebitda-low"),
      new_ebitda_guidance_high: erNumber("er-new-ebitda-high"),
    };
  }

  function setERStatus(message, kind = "") {
    erStatus.textContent = message;
    erStatus.classList.remove("is-success", "is-error");
    if (kind) erStatus.classList.add(`is-${kind}`);
  }

  function setERLoading(isLoading) {
    erRunButton.disabled = isLoading;
    erRunButton.textContent = isLoading ? "Analysing Earnings..." : "Run Earnings Review";
  }

  function currencySymbol(code) {
    return { GBP: "£", USD: "$", EUR: "€" }[String(code).toUpperCase()] || `${String(code).toUpperCase()} `;
  }

  function erMoney(value, currency, suffix = "m") {
    return `${currencySymbol(currency)}${Number(value).toLocaleString(undefined, { maximumFractionDigits: 0 })}${suffix}`;
  }

  function erPrice(value, currency) {
    return `${currencySymbol(currency)}${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  function erEPS(value, currency) {
    return `${currencySymbol(currency)}${Number(value).toFixed(2)}`;
  }

  function signedPercent(value, digits = 1) {
    const pct = Number(value) * 100;
    return `${pct > 0 ? "+" : ""}${pct.toFixed(digits)}%`;
  }

  function signedBps(value) {
    const n = Number(value);
    return `${n > 0 ? "+" : ""}${Math.round(n)} bps`;
  }

  function classificationClass(value) {
    if (value === "BEAT" || value === "RAISED") return "beat";
    if (value === "MISS" || value === "LOWERED") return "miss";
    return "inline";
  }

  function valueDirectionClass(value) {
    const n = Number(value);
    if (n > 0) return "er-positive";
    if (n < 0) return "er-negative";
    return "";
  }

  function renderERKpis(data) {
    const metrics = [
      ["Revenue", data.revenue, (v) => erMoney(v, data.currency)],
      ["EBITDA", data.ebitda, (v) => erMoney(v, data.currency)],
      ["EPS", data.eps, (v) => erEPS(v, data.currency)],
      ["Free Cash Flow", data.fcf, (v) => erMoney(v, data.currency)],
    ];
    document.getElementById("er-kpi-grid").innerHTML = metrics.map(([label, metric, formatter]) => {
      const cls = classificationClass(metric.classification);
      return `<div class="er-kpi is-${cls}">
        <div class="er-kpi-title"><span>${label}</span><span class="er-result-pill ${cls}">${metric.classification}</span></div>
        <div class="er-kpi-actual">${formatter(metric.actual)}</div>
        <div class="er-kpi-subline"><span>vs consensus</span><strong class="${valueDirectionClass(metric.surprise)}">${signedPercent(metric.surprise)}</strong></div>
        <div class="er-kpi-subline"><span>YoY</span><strong class="${valueDirectionClass(metric.yoy_growth)}">${signedPercent(metric.yoy_growth)}</strong></div>
      </div>`;
    }).join("");
  }

  function renderERSurpriseChart(data) {
    const metrics = [
      ["Revenue", data.revenue.surprise],
      ["EBITDA", data.ebitda.surprise],
      ["EPS", data.eps.surprise],
      ["FCF", data.fcf.surprise],
    ];
    const maxAbs = Math.max(...metrics.map(([, v]) => Math.abs(Number(v))), 0.01);
    document.getElementById("er-surprise-chart").innerHTML = metrics.map(([label, value]) => {
      const n = Number(value);
      const width = Math.max(2, Math.min(50, Math.abs(n) / maxAbs * 48));
      return `<div class="er-surprise-row">
        <div class="er-surprise-label">${label}</div>
        <div class="er-surprise-track"><div class="er-surprise-bar ${n >= 0 ? "positive" : "negative"}" style="width:${width}%"></div></div>
        <div class="er-surprise-value ${valueDirectionClass(n)}">${signedPercent(n)}</div>
      </div>`;
    }).join("");
  }

  function renderERResultsTable(data) {
    const rows = [
      ["Revenue", data.revenue, (v) => erMoney(v, data.currency)],
      ["EBITDA", data.ebitda, (v) => erMoney(v, data.currency)],
      ["EPS", data.eps, (v) => erEPS(v, data.currency)],
      ["Free Cash Flow", data.fcf, (v) => erMoney(v, data.currency)],
    ];
    document.getElementById("er-results-table-body").innerHTML = rows.map(([label, metric, formatter]) => {
      const cls = classificationClass(metric.classification);
      return `<tr>
        <td class="strong">${label}</td><td>${formatter(metric.prior)}</td><td>${formatter(metric.consensus)}</td><td class="strong">${formatter(metric.actual)}</td>
        <td class="${valueDirectionClass(metric.yoy_growth)}">${signedPercent(metric.yoy_growth)}</td>
        <td class="${valueDirectionClass(metric.surprise)}">${signedPercent(metric.surprise)}</td>
        <td><span class="er-result-pill ${cls}">${metric.classification}</span></td>
      </tr>`;
    }).join("");
  }

  function renderERQuality(data) {
    const mapping = {
      "er-prior-margin": fmt.percent(data.prior_ebitda_margin, 1),
      "er-consensus-margin": fmt.percent(data.consensus_ebitda_margin, 1),
      "er-actual-margin": fmt.percent(data.actual_ebitda_margin, 1),
      "er-margin-surprise": signedBps(data.ebitda_margin_surprise_bps),
      "er-margin-yoy": signedBps(data.ebitda_margin_yoy_change_bps),
      "er-fcf-conversion": fmt.percent(data.fcf_conversion, 1),
    };
    Object.entries(mapping).forEach(([id, value]) => { document.getElementById(id).textContent = value; });
    document.getElementById("er-margin-surprise").className = valueDirectionClass(data.ebitda_margin_surprise_bps);
    document.getElementById("er-margin-yoy").className = valueDirectionClass(data.ebitda_margin_yoy_change_bps);
  }

  function guidanceBlock(label, guidance, currency) {
    const min = Math.min(guidance.previous_low, guidance.new_low);
    const max = Math.max(guidance.previous_high, guidance.new_high);
    const padding = Math.max((max - min) * 0.18, 1);
    const axisMin = min - padding;
    const axisMax = max + padding;
    const span = axisMax - axisMin;
    const pos = (v) => (Number(v) - axisMin) / span * 100;
    const prevLeft = pos(guidance.previous_low);
    const prevWidth = Math.max(2, pos(guidance.previous_high) - prevLeft);
    const currLeft = pos(guidance.new_low);
    const currWidth = Math.max(2, pos(guidance.new_high) - currLeft);
    const cls = classificationClass(guidance.classification);
    return `<div class="er-guidance-block">
      <div class="er-guidance-heading"><strong>${label}</strong><span class="er-result-pill ${cls}">${guidance.classification} ${signedPercent(guidance.midpoint_revision)}</span></div>
      <div class="er-guidance-axis">
        <div class="er-guidance-track"></div>
        <div class="er-guidance-range previous" style="left:${prevLeft}%;width:${prevWidth}%"></div>
        <div class="er-guidance-range current" style="left:${currLeft}%;width:${currWidth}%"></div>
      </div>
      <div class="er-guidance-legend"><span><i class="er-guidance-swatch"></i>Previous</span><span><i class="er-guidance-swatch current"></i>Current</span></div>
      <div class="er-guidance-detail"><span>Previous ${erMoney(guidance.previous_low, currency)} – ${erMoney(guidance.previous_high, currency)}</span><span>Current <strong>${erMoney(guidance.new_low, currency)} – ${erMoney(guidance.new_high, currency)}</strong></span></div>
    </div>`;
  }

  function renderERGuidance(data) {
    document.getElementById("er-guidance-wrap").innerHTML =
      guidanceBlock("Revenue Guidance", data.revenue_guidance, data.currency) +
      guidanceBlock("EBITDA Guidance", data.ebitda_guidance, data.currency);
  }

  function renderERValuation(data) {
    const mapping = {
      "er-val-share-price": erPrice(data.share_price, data.currency),
      "er-market-cap": erMoney(data.market_cap, data.currency),
      "er-enterprise-value": erMoney(data.enterprise_value, data.currency),
      "er-forward-pe": `${Number(data.forward_pe).toFixed(1)}x`,
      "er-forward-ev-ebitda": `${Number(data.forward_ev_ebitda).toFixed(1)}x`,
      "er-forward-ev-revenue": `${Number(data.forward_ev_revenue).toFixed(1)}x`,
      "er-net-debt-ebitda": `${Number(data.net_debt_ebitda).toFixed(1)}x`,
    };
    Object.entries(mapping).forEach(([id, value]) => { document.getElementById(id).textContent = value; });
  }

  function fillList(id, items) {
    document.getElementById(id).innerHTML = items.map((item) => `<li>${item}</li>`).join("");
  }

  function renderERReport(data) {
    document.getElementById("er-report-company").textContent = data.company_name;
    document.getElementById("er-report-meta").textContent = `${data.ticker} | ${data.period} | ${data.currency} | Controlled sample data`;
    document.getElementById("er-scorecard").textContent = data.earnings_scorecard;
    document.getElementById("er-strongest-surprise").textContent = `${data.strongest_surprise_metric}: ${signedPercent(data.strongest_surprise)}`;
    renderERKpis(data);
    renderERSurpriseChart(data);
    renderERQuality(data);
    renderERResultsTable(data);
    renderERGuidance(data);
    renderERValuation(data);
    fillList("er-takeaways", data.takeaways);
    fillList("er-catalysts", data.catalysts);
    fillList("er-risks", data.risks);
    erReport.hidden = false;
  }

  function extractERValidationMessage(body) {
    if (!body || !Array.isArray(body.detail) || body.detail.length === 0) {
      return "Unable to run the earnings review. Please check the submitted inputs.";
    }
    const message = body.detail[0]?.msg;
    return typeof message === "string" && message.length
      ? message.replace(/^Value error,\s*/i, "")
      : "Unable to run the earnings review. Please check the submitted inputs.";
  }

  erForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!erForm.reportValidity()) { setERStatus(""); return; }
    erReport.hidden = true;
    lastSuccessfulERPayload = null;
    erDownloadButton.disabled = true;
    erReportButton.disabled = true;
    setERLoading(true);
    setERStatus("Analysing reported results against consensus and prior-period performance...");
    try {
      const response = await fetch("/api/equity-research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildERPayload()),
      });
      if (!response.ok) {
        let body = null;
        try { body = await response.json(); } catch { /* generic error below */ }
        setERStatus(response.status === 422 ? extractERValidationMessage(body) : "The equity-research service returned an error. Please try again.", "error");
        return;
      }
      const data = await response.json();
      renderERReport(data);
      lastSuccessfulERPayload = buildERPayload();
      erDownloadButton.disabled = false;
      erReportButton.disabled = false;
      setERStatus("Earnings review completed successfully.", "success");
    } catch {
      setERStatus("Unable to connect to the equity-research service.", "error");
    } finally {
      setERLoading(false);
    }
  });

  erForm.addEventListener("input", () => {
    if (lastSuccessfulERPayload !== null) {
      lastSuccessfulERPayload = null;
      erDownloadButton.disabled = true;
      erReportButton.disabled = true;
      setERStatus("Inputs changed — run the earnings review again before opening or downloading research outputs.");
    }
  });

  erReportButton.addEventListener("click", async () => {
    if (!lastSuccessfulERPayload) {
      setERStatus("Run the earnings review before opening the research note.", "error");
      return;
    }

    const reportWindow = window.open("", "_blank");
    if (!reportWindow) {
      setERStatus("Safari blocked the research-note window. Allow pop-ups for this local site and try again.", "error");
      return;
    }
    reportWindow.document.write("<p style='font-family:Arial,sans-serif;padding:24px'>Generating research note…</p>");

    const originalText = erReportButton.textContent;
    erReportButton.disabled = true;
    erReportButton.textContent = "Opening Research Note...";
    setERStatus("Generating print-ready Equity Research note...");

    try {
      const response = await fetch("/api/equity-research/report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(lastSuccessfulERPayload),
      });

      if (!response.ok) {
        let body = null;
        try { body = await response.json(); } catch { /* generic error below */ }
        reportWindow.close();
        setERStatus(response.status === 422 ? extractERValidationMessage(body) : "Unable to generate the research note. Please try again.", "error");
        return;
      }

      const html = await response.text();
      reportWindow.document.open();
      reportWindow.document.write(html);
      reportWindow.document.close();
      setERStatus("Research note opened in a new tab. Use Print / Save as PDF when ready.", "success");
    } catch {
      reportWindow.close();
      setERStatus("Unable to connect to the research-note service.", "error");
    } finally {
      erReportButton.textContent = originalText;
      erReportButton.disabled = lastSuccessfulERPayload === null;
    }
  });

  erDownloadButton.addEventListener("click", async () => {
    if (!lastSuccessfulERPayload) {
      setERStatus("Run the earnings review before downloading the research model.", "error");
      return;
    }

    const originalText = erDownloadButton.textContent;
    erDownloadButton.disabled = true;
    erDownloadButton.textContent = "Generating Research Model...";
    setERStatus("Generating analyst-style Excel research model...");

    try {
      const response = await fetch("/api/equity-research/excel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(lastSuccessfulERPayload),
      });

      if (!response.ok) {
        let body = null;
        try { body = await response.json(); } catch { /* generic error below */ }
        if (response.status === 422) {
          setERStatus(extractERValidationMessage(body), "error");
        } else {
          setERStatus("Unable to generate the research model. Please try again.", "error");
        }
        return;
      }

      const blob = await response.blob();
      const disposition = response.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename="?([^";]+)"?/i);
      const filename = match ? match[1] : "Equity_Research_Model.xlsx";
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setERStatus("Equity Research Excel model downloaded successfully.", "success");
    } catch {
      setERStatus("Unable to connect to the research-model service.", "error");
    } finally {
      erDownloadButton.textContent = originalText;
      erDownloadButton.disabled = lastSuccessfulERPayload === null;
    }
  });

  // ------------------------------------------------------------------------
  // M&A execution workflow
  // ------------------------------------------------------------------------
  const maForm = document.getElementById("ma-form");
  const maRunButton = document.getElementById("run-ma");
  const maStatus = document.getElementById("ma-status");
  const maDashboard = document.getElementById("ma-dashboard");
  const maExcelButton = document.getElementById("download-ma-excel");
  let lastSuccessfulMAPayload = null;

  function maNumber(id) { return Number(document.getElementById(id).value); }
  function maText(id) { return document.getElementById(id).value.trim(); }

  function buildMAPayload() {
    return {
      acquirer_name: maText("ma-acquirer-name"),
      acquirer_ticker: maText("ma-acquirer-ticker"),
      target_name: maText("ma-target-name"),
      target_ticker: maText("ma-target-ticker"),
      currency: maText("ma-currency"),
      acquirer_share_price: maNumber("ma-acquirer-share-price"),
      acquirer_shares_outstanding: maNumber("ma-acquirer-shares"),
      acquirer_net_income: maNumber("ma-acquirer-net-income"),
      target_share_price: maNumber("ma-target-share-price"),
      target_shares_outstanding: maNumber("ma-target-shares"),
      target_net_income: maNumber("ma-target-net-income"),
      target_ltm_revenue: maNumber("ma-target-revenue"),
      target_ltm_ebitda: maNumber("ma-target-ebitda"),
      target_debt: maNumber("ma-target-debt"),
      target_cash: maNumber("ma-target-cash"),
      target_book_equity: maNumber("ma-target-book-equity"),
      offer_price_per_share: maNumber("ma-offer-price"),
      cash_consideration_pct: maNumber("ma-cash-pct") / 100,
      stock_consideration_pct: maNumber("ma-stock-pct") / 100,
      cash_on_hand_used: maNumber("ma-cash-on-hand"),
      new_debt_interest_rate: maNumber("ma-new-debt-rate") / 100,
      cash_interest_rate: maNumber("ma-cash-interest-rate") / 100,
      tax_rate: maNumber("ma-tax-rate") / 100,
      annual_pre_tax_synergies: maNumber("ma-synergies"),
      identifiable_intangible_write_up: maNumber("ma-intangible-writeup"),
      amortization_years: maNumber("ma-amortization-years"),
    };
  }

  function maCurrencySymbol(code) {
    return { GBP: "£", USD: "$", EUR: "€" }[String(code).toUpperCase()] || `${String(code).toUpperCase()} `;
  }

  function maMoney(value, currency, digits = 0) {
    return `${maCurrencySymbol(currency)}${Number(value).toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })}m`;
  }

  function maPerShare(value, currency) {
    return `${maCurrencySymbol(currency)}${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  function maPct(value, digits = 1) { return `${(Number(value) * 100).toFixed(digits)}%`; }
  function maMultiple(value) { return `${Number(value).toFixed(1)}x`; }

  function maSignedPct(value) {
    const pct = Number(value) * 100;
    return pct < 0 ? `(${Math.abs(pct).toFixed(1)}%)` : `+${pct.toFixed(1)}%`;
  }

  function setMAStatus(message, kind = "") {
    if (!maStatus) return;
    maStatus.textContent = message;
    maStatus.classList.remove("is-success", "is-error");
    if (kind) maStatus.classList.add(`is-${kind}`);
  }

  function maClassificationClass(value) {
    const normalized = String(value).toLowerCase();
    if (normalized === "accretive") return "is-accretive";
    if (normalized === "dilutive") return "is-dilutive";
    return "is-neutral";
  }

  function renderMAHeadline(data) {
    const t = data.transaction;
    const a = data.accretion_dilution;
    document.getElementById("ma-deal-title").textContent = `${data.acquirer_name} → ${data.target_name}`;
    document.getElementById("ma-deal-subtitle").textContent =
      `${data.acquirer_ticker} acquiring ${data.target_ticker} | ${maCurrencySymbol(data.currency)}m unless stated otherwise`;
    const classification = document.getElementById("ma-classification");
    classification.textContent = a.classification;
    classification.className = maClassificationClass(a.classification);
    document.getElementById("ma-accretion-badge").textContent = `${maSignedPct(a.accretion_dilution)} EPS impact`;
    document.getElementById("ma-out-offer-price").textContent = maPerShare(t.offer_price_per_share, data.currency);
    document.getElementById("ma-out-premium").textContent = maPct(t.offer_premium);
    document.getElementById("ma-out-equity-value").textContent = maMoney(t.equity_purchase_price, data.currency);
    document.getElementById("ma-out-enterprise-value").textContent = maMoney(t.target_enterprise_value, data.currency);
    document.getElementById("ma-out-ev-ebitda").textContent = maMultiple(t.target_ev_ebitda);
    const accretion = document.getElementById("ma-out-accretion");
    accretion.textContent = maSignedPct(a.accretion_dilution);
    accretion.className = maClassificationClass(a.classification);
  }

  function renderMAConsideration(data) {
    const f = data.financing;
    const total = Math.max(Number(f.cash_consideration) + Number(f.stock_consideration), 1);
    const cashWidth = Number(f.cash_consideration) / total * 100;
    const stockWidth = Number(f.stock_consideration) / total * 100;
    document.getElementById("ma-consideration-bars").innerHTML = `
      <div class="ma-consideration-row"><div class="ma-consideration-label"><span>Cash Consideration</span><strong>${maMoney(f.cash_consideration, data.currency)}</strong></div><div class="ma-bar-track"><div class="ma-bar cash" style="width:${cashWidth}%"></div></div></div>
      <div class="ma-consideration-row"><div class="ma-consideration-label"><span>Stock Consideration</span><strong>${maMoney(f.stock_consideration, data.currency)}</strong></div><div class="ma-bar-track"><div class="ma-bar stock" style="width:${stockWidth}%"></div></div></div>`;
    document.getElementById("ma-funding-strip").innerHTML = `
      <div><span>Cash on Hand</span><strong>${maMoney(f.cash_on_hand_used, data.currency)}</strong></div>
      <div><span>New Debt</span><strong>${maMoney(f.new_debt_raised, data.currency)}</strong></div>`;
  }

  function renderMAOwnership(data) {
    const f = data.financing;
    const sellerPct = Math.max(0, Math.min(100, Number(f.target_seller_ownership) * 100));
    const donut = document.getElementById("ma-ownership-donut");
    donut.style.background = `conic-gradient(var(--blue) 0 ${100 - sellerPct}%, #9bb6d9 ${100 - sellerPct}% 100%)`;
    document.getElementById("ma-ownership-center").textContent = `${sellerPct.toFixed(1)}% sellers`;
    document.getElementById("ma-existing-ownership").textContent = maPct(f.existing_acquirer_ownership);
    document.getElementById("ma-seller-ownership").textContent = maPct(f.target_seller_ownership);
    document.getElementById("ma-new-shares").textContent = `${Number(f.new_shares_issued).toFixed(2)}m`;
    document.getElementById("ma-exchange-ratio").textContent = `${Number(f.exchange_ratio).toFixed(4)}x`;
  }

  function renderMAAccretion(data) {
    const a = data.accretion_dilution;
    document.getElementById("ma-standalone-eps").textContent = maPerShare(a.acquirer_standalone_eps, data.currency);
    document.getElementById("ma-proforma-eps").textContent = maPerShare(a.pro_forma_eps, data.currency);
    document.getElementById("ma-proforma-net-income").textContent = maMoney(a.pro_forma_net_income, data.currency, 1);
    document.getElementById("ma-break-even-synergies").textContent = maMoney(a.break_even_pre_tax_synergies, data.currency, 1);
    const items = [
      ["After-Tax Synergies", a.after_tax_synergies, "positive"],
      ["New Debt Interest", -Number(a.after_tax_new_debt_interest), "negative"],
      ["Foregone Cash Interest", -Number(a.after_tax_foregone_cash_interest), "negative"],
      ["Incremental Amortization", -Number(a.after_tax_incremental_amortization), "negative"],
    ];
    const maxAbs = Math.max(...items.map((item) => Math.abs(Number(item[1]))), 1);
    document.getElementById("ma-earnings-bridge").innerHTML = items.map(([label, value, cls]) => {
      const width = Math.max(4, Math.abs(Number(value)) / maxAbs * 100);
      return `<div class="ma-earnings-row"><span>${label}</span><div class="ma-earnings-track"><div class="ma-earnings-bar ${cls}" style="width:${width}%"></div></div><strong class="${cls}">${value >= 0 ? "+" : "−"}${maMoney(Math.abs(value), data.currency, 1)}</strong></div>`;
    }).join("");
  }

  function renderMAPurchaseAccounting(data) {
    const p = data.purchase_accounting;
    document.getElementById("ma-book-equity").textContent = maMoney(p.target_book_equity, data.currency);
    document.getElementById("ma-intangible-writeup-out").textContent = maMoney(p.identifiable_intangible_write_up, data.currency);
    document.getElementById("ma-goodwill").textContent = maMoney(p.goodwill_created, data.currency);
    document.getElementById("ma-amortization").textContent = maMoney(p.annual_incremental_amortization, data.currency, 1);
    const components = [
      ["Book Equity", Number(p.target_book_equity), "book"],
      ["Intangibles", Number(p.identifiable_intangible_write_up), "intangibles"],
      ["Goodwill", Number(p.goodwill_created), "goodwill"],
    ];
    const total = Math.max(...[components.reduce((sum, item) => sum + Math.max(item[1], 0), 0), 1]);
    document.getElementById("ma-purchase-stack").innerHTML = components.map(([label, value, cls]) => `<div class="ma-purchase-segment ${cls}" style="width:${Math.max(0, value) / total * 100}%"><span>${label}</span><strong>${maMoney(value, data.currency)}</strong></div>`).join("");
  }

  function renderMADealTable(data) {
    const t = data.transaction;
    const f = data.financing;
    const a = data.accretion_dilution;
    const rows = [
      ["Transaction", "Offer Premium", maPct(t.offer_premium), "Premium to unaffected target price"],
      ["Transaction", "EV / Revenue", maMultiple(t.target_ev_revenue), "Purchase multiple on target LTM revenue"],
      ["Transaction", "EV / EBITDA", maMultiple(t.target_ev_ebitda), "Purchase multiple on target LTM EBITDA"],
      ["Financing", "New Debt Raised", maMoney(f.new_debt_raised, data.currency), "Incremental acquisition financing"],
      ["Financing", "New Shares Issued", `${Number(f.new_shares_issued).toFixed(2)}m`, "Shares issued to fund stock consideration"],
      ["Financing", "Target Seller Ownership", maPct(f.target_seller_ownership), "Pro forma ownership of target sellers"],
      ["EPS", "Standalone EPS", maPerShare(a.acquirer_standalone_eps, data.currency), "Acquirer pre-transaction EPS"],
      ["EPS", "Pro Forma EPS", maPerShare(a.pro_forma_eps, data.currency), `${a.classification} transaction outcome`],
      ["EPS", "Break-Even Synergies", maMoney(a.break_even_pre_tax_synergies, data.currency, 1), "Pre-tax synergies required for EPS neutrality"],
    ];
    document.getElementById("ma-deal-table-body").innerHTML = rows.map((row) => `<tr><td>${row[0]}</td><td class="strong">${row[1]}</td><td class="strong">${row[2]}</td><td>${row[3]}</td></tr>`).join("");
  }

  function renderMACommentary(data) {
    document.getElementById("ma-takeaways").innerHTML = data.key_takeaways.map((item) => `<li>${item}</li>`).join("");
    document.getElementById("ma-risks").innerHTML = data.execution_risks.map((item) => `<li>${item}</li>`).join("");
  }

  function renderMADashboard(data) {
    renderMAHeadline(data);
    renderMAConsideration(data);
    renderMAOwnership(data);
    renderMAAccretion(data);
    renderMAPurchaseAccounting(data);
    renderMADealTable(data);
    renderMACommentary(data);
    maDashboard.hidden = false;
  }

  if (maForm) {
    maForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = buildMAPayload();
      maRunButton.disabled = true;
      maRunButton.textContent = "Running Deal Analysis...";
      setMAStatus("Running purchase price, financing and accretion / dilution analysis...");
      try {
        const response = await fetch("/api/ma-execution", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          let message = "The M&A service returned an error. Please review the transaction assumptions.";
          try {
            const error = await response.json();
            if (Array.isArray(error.detail) && error.detail[0]?.msg) message = error.detail[0].msg;
          } catch { /* keep readable fallback */ }
          setMAStatus(message, "error");
          return;
        }
        const data = await response.json();
        lastSuccessfulMAPayload = payload;
        if (maExcelButton) maExcelButton.disabled = false;
        renderMADashboard(data);
        setMAStatus("Deal analysis completed successfully.", "success");
      } catch {
        setMAStatus("Unable to connect to the M&A execution service.", "error");
      } finally {
        maRunButton.disabled = false;
        maRunButton.textContent = "Run Deal Analysis";
      }
    });

    maForm.addEventListener("input", () => {
      if (lastSuccessfulMAPayload !== null) {
        lastSuccessfulMAPayload = null;
        if (maExcelButton) maExcelButton.disabled = true;
        maDashboard.hidden = true;
        setMAStatus("Inputs changed — run the deal analysis again before downloading or refreshing transaction outputs.");
      }
    });
  }


  if (maExcelButton) {
    maExcelButton.addEventListener("click", async () => {
      if (!lastSuccessfulMAPayload) {
        setMAStatus("Run the deal analysis before downloading the merger model.", "error");
        return;
      }

      const originalText = maExcelButton.textContent;
      maExcelButton.disabled = true;
      maExcelButton.textContent = "Generating...";
      setMAStatus("Generating banker-style merger model workbook...");

      try {
        const response = await fetch("/api/ma-execution/excel", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(lastSuccessfulMAPayload),
        });

        if (!response.ok) {
          let message = "Unable to generate the merger model workbook.";
          try {
            const error = await response.json();
            if (Array.isArray(error.detail) && error.detail[0]?.msg) message = error.detail[0].msg;
            else if (typeof error.detail === "string") message = error.detail;
          } catch { /* keep readable fallback */ }
          setMAStatus(message, "error");
          return;
        }

        const blob = await response.blob();
        const disposition = response.headers.get("content-disposition") || "";
        const utf8 = disposition.match(/filename\*=UTF-8''([^;]+)/i);
        const basic = disposition.match(/filename=\"?([^\";]+)\"?/i);
        const filename = utf8 ? decodeURIComponent(utf8[1]) : (basic ? basic[1] : "Merger_Model.xlsx");
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
        setMAStatus("Merger model downloaded successfully.", "success");
      } catch {
        setMAStatus("Unable to connect to the merger-model service.", "error");
      } finally {
        maExcelButton.textContent = originalText;
        maExcelButton.disabled = lastSuccessfulMAPayload === null;
      }
    });
  }


  // ------------------------------------------------------------------------
  // AnalystForge interactive homepage layer
  // ------------------------------------------------------------------------
  const siteTopbar = document.getElementById("site-topbar");
  const closingOpenTools = document.getElementById("closing-open-tools");
  if (closingOpenTools) closingOpenTools.addEventListener("click", () => setSidebar(true));

  // Scroll progress + compact header state.
  function updatePageProgress() {
    const max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    const progress = Math.min(1, Math.max(0, window.scrollY / max));
    document.documentElement.style.setProperty("--page-progress", String(progress));
    if (siteTopbar) siteTopbar.classList.toggle("is-scrolled", window.scrollY > 24);
  }
  updatePageProgress();
  window.addEventListener("scroll", updatePageProgress, { passive: true });

  // Scroll-reveal sections. Content remains visible when JS is unavailable.
  const revealItems = Array.from(document.querySelectorAll(".reveal"));
  if ("IntersectionObserver" in window && revealItems.length) {
    document.body.classList.add("js-reveal-ready");
    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-revealed");
          revealObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
    revealItems.forEach((item) => revealObserver.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add("is-revealed"));
  }

  // Pointer-driven hero glow and restrained 3D movement.
  const afHero = document.querySelector(".af-hero");
  const heroStage = document.getElementById("hero-stage");
  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
  if (afHero && !reduceMotion) {
    afHero.addEventListener("pointermove", (event) => {
      const rect = afHero.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / rect.width) * 100;
      const y = ((event.clientY - rect.top) / rect.height) * 100;
      afHero.style.setProperty("--af-glow-x", `${x}%`);
      afHero.style.setProperty("--af-glow-y", `${y}%`);
      if (heroStage) {
        heroStage.style.setProperty("--tilt-x", ((x - 50) / 14).toFixed(2));
        heroStage.style.setProperty("--tilt-y", ((50 - y) / 18).toFixed(2));
      }
    });
    afHero.addEventListener("pointerleave", () => {
      if (heroStage) {
        heroStage.style.setProperty("--tilt-x", "0");
        heroStage.style.setProperty("--tilt-y", "0");
      }
    });
  }

  // Hero workflow cards cycle gently to keep the landing page alive.
  const heroFlowCards = Array.from(document.querySelectorAll(".hero-flow-card"));
  let heroFlowIndex = 0;
  let heroFlowTimer = null;
  function setActiveHeroFlow(index) {
    if (!heroFlowCards.length) return;
    heroFlowIndex = (index + heroFlowCards.length) % heroFlowCards.length;
    heroFlowCards.forEach((card, i) => card.classList.toggle("is-active", i === heroFlowIndex));
  }
  heroFlowCards.forEach((card, index) => {
    card.addEventListener("mouseenter", () => setActiveHeroFlow(index));
    card.addEventListener("focus", () => setActiveHeroFlow(index));
  });
  if (heroFlowCards.length && !reduceMotion) {
    heroFlowTimer = window.setInterval(() => setActiveHeroFlow(heroFlowIndex + 1), 3200);
    heroStage?.addEventListener("mouseenter", () => { if (heroFlowTimer) window.clearInterval(heroFlowTimer); });
    heroStage?.addEventListener("mouseleave", () => {
      heroFlowTimer = window.setInterval(() => setActiveHeroFlow(heroFlowIndex + 1), 3200);
    });
  }

  // Cards that behave like links remain keyboard-accessible.
  document.querySelectorAll('[role="button"][data-open-tool]').forEach((card) => {
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        transitionTo(card.dataset.openTool, { pushHistory: true });
      }
    });
  });

})();
