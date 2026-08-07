/**
 * Init Chart.js a partir de payloads embutidos (json_script).
 * Carregado só em páginas de dashboard com gráfico (admin → team → personal).
 * Chart.js UMD (cdn) deve estar disponível como `Chart` global antes deste arquivo.
 *
 * Convenção DOM (com _chart_block.html):
 *   <canvas data-chart-payload="script-id"></canvas>
 *   {{ payload|json_script:"script-id" }}
 *
 * Cria Chart só se has_data === true; não inventa série zerada.
 */
(function () {
  'use strict';

  var STATUS_TRIAD = ['#059669', '#d97706', '#e11d48'];
  var GROUPED_DEFAULTS = {
    nivel_esperado: '#64748b',
    nota_atual: '#059669',
  };

  /* Tokens visuais DS v2 (espelham --font-ui / paleta em input.css) — só options Chart.js. */
  var FONT_UI = "'Source Sans 3', ui-sans-serif, system-ui, sans-serif";
  var COLOR_INK_MUTED = '#64748b';
  var COLOR_LINE = '#e2e8f0';
  var COLOR_TOOLTIP_BG = '#1e293b';
  var BAR_RADIUS = 6;
  var BAR_MAX_THICKNESS = 40;
  var DOUGHNUT_CUTOUT = '68%';

  function chartFont(overrides) {
    var base = { family: FONT_UI, size: 12, weight: '400' };
    if (!overrides) {
      return base;
    }
    return {
      family: overrides.family || base.family,
      size: overrides.size !== undefined ? overrides.size : base.size,
      weight: overrides.weight || base.weight,
    };
  }

  function readPayload(scriptId) {
    var el = document.getElementById(scriptId);
    if (!el) {
      return null;
    }
    try {
      return JSON.parse(el.textContent);
    } catch (err) {
      return null;
    }
  }

  function resolveChartType(payloadType) {
    if (payloadType === 'doughnut' || payloadType === 'doughnut_or_bar') {
      return 'doughnut';
    }
    return 'bar';
  }

  function asNullableNumber(value) {
    if (value === null || value === undefined) {
      return null;
    }
    return value;
  }

  function tooltipLabel(ctx) {
    var datasetLabel = ctx.dataset && ctx.dataset.label ? ctx.dataset.label : '';
    var categoryLabel = ctx.label || '';
    var parsed = ctx.parsed;
    var value;

    if (parsed === null || parsed === undefined) {
      return datasetLabel || categoryLabel || '';
    }
    if (typeof parsed === 'object') {
      value = parsed.y !== undefined ? parsed.y : parsed;
    } else {
      value = parsed;
    }

    if (value === null || value === undefined) {
      return (datasetLabel || categoryLabel) + ': —';
    }

    if (datasetLabel && categoryLabel && ctx.chart.config.type === 'bar') {
      return datasetLabel + ': ' + value;
    }
    if (datasetLabel) {
      return datasetLabel + ': ' + value;
    }
    return categoryLabel + ': ' + value;
  }

  function isNarrowViewport() {
    return (
      typeof window !== 'undefined' &&
      window.matchMedia &&
      window.matchMedia('(max-width: 639px)').matches
    );
  }

  function formatLegendValue(value) {
    if (value === null || value === undefined) {
      return '—';
    }
    return String(value);
  }

  /**
   * Legenda Chart.js com texto + valor (FR-007): não depende só da cor.
   * Doughnut/pie: um item por faixa (labels).
   * Multi-série (grouped): um item por série.
   * Barra única categórica: oculta (eixo + figcaption cobrem).
   */
  function legendLabelWithValue(chart) {
    var data = chart.data || {};
    var labels = data.labels || [];
    var datasets = data.datasets || [];
    var type = chart.config && chart.config.type;

    if (type === 'doughnut' || type === 'pie') {
      var ds = datasets[0] || {};
      var values = ds.data || [];
      var bg = ds.backgroundColor;
      return labels.map(function (label, i) {
        var fill = Array.isArray(bg) ? bg[i] : bg;
        return {
          text: label + ': ' + formatLegendValue(values[i]),
          fillStyle: fill,
          strokeStyle: fill,
          hidden: false,
          index: i,
          datasetIndex: 0,
        };
      });
    }

    // Default Chart.js (séries agrupadas): label da série + sem forçar valor agregado.
    var defaults =
      Chart.defaults &&
      Chart.defaults.plugins &&
      Chart.defaults.plugins.legend &&
      Chart.defaults.plugins.legend.labels &&
      Chart.defaults.plugins.legend.labels.generateLabels;
    if (typeof defaults === 'function') {
      return defaults(chart);
    }
    return datasets.map(function (dataset, datasetIndex) {
      return {
        text: dataset.label || 'Série ' + (datasetIndex + 1),
        fillStyle: dataset.backgroundColor,
        strokeStyle: dataset.borderColor || dataset.backgroundColor,
        hidden: !!dataset.hidden,
        datasetIndex: datasetIndex,
      };
    });
  }

  function subtleGrid() {
    return {
      color: COLOR_LINE,
      lineWidth: 1,
      drawTicks: false,
    };
  }

  function axisBorderHidden() {
    return { display: false };
  }

  function basePlugins(showLegend) {
    var narrow = isNarrowViewport();
    return {
      legend: {
        display: !!showLegend,
        position: 'bottom',
        labels: {
          usePointStyle: true,
          boxWidth: 8,
          boxHeight: 8,
          // Fonte UI v2 legível em ~375px; texto + valor (FR-007 / SC-006).
          color: COLOR_INK_MUTED,
          font: chartFont({ size: narrow ? 11 : 12, weight: '500' }),
          padding: narrow ? 10 : 14,
          generateLabels: legendLabelWithValue,
        },
      },
      tooltip: {
        enabled: true,
        backgroundColor: COLOR_TOOLTIP_BG,
        titleColor: '#ffffff',
        bodyColor: '#e2e8f0',
        borderColor: 'rgba(255, 255, 255, 0.08)',
        borderWidth: 1,
        cornerRadius: 8,
        padding: narrow ? 8 : 10,
        displayColors: true,
        boxPadding: 4,
        titleFont: chartFont({ size: narrow ? 11 : 12, weight: '600' }),
        bodyFont: chartFont({ size: narrow ? 11 : 12, weight: '400' }),
        callbacks: {
          label: tooltipLabel,
        },
      },
    };
  }

  function barScales(horizontal) {
    var narrow = isNarrowViewport();
    var tickFont = chartFont({ size: narrow ? 10 : 12, weight: '400' });
    var categoryAxis = {
      grid: { display: false },
      border: axisBorderHidden(),
      ticks: {
        autoSkip: false,
        maxRotation: horizontal ? 0 : narrow ? 60 : 45,
        minRotation: horizontal ? 0 : narrow ? 45 : 0,
        color: COLOR_INK_MUTED,
        font: tickFont,
      },
    };
    var valueAxis = {
      beginAtZero: true,
      border: axisBorderHidden(),
      grid: subtleGrid(),
      ticks: {
        precision: 0,
        color: COLOR_INK_MUTED,
        font: tickFont,
      },
    };

    if (horizontal) {
      return {
        x: valueAxis,
        y: categoryAxis,
      };
    }
    return {
      x: categoryAxis,
      y: valueAxis,
    };
  }

  function buildGroupedConfig(payload) {
    var labels = payload.labels || [];
    var datasets = (payload.series || []).map(function (serie, index) {
      var color =
        serie.color ||
        GROUPED_DEFAULTS[serie.key] ||
        STATUS_TRIAD[index % STATUS_TRIAD.length];
      return {
        label: serie.label || serie.key || 'Série ' + (index + 1),
        // null permanece null — Chart.js omite a barra (não inventa 0).
        data: (serie.values || []).map(asNullableNumber),
        backgroundColor: color,
        borderColor: color,
        borderWidth: 0,
        borderRadius: BAR_RADIUS,
        maxBarThickness: BAR_MAX_THICKNESS,
        skipNull: true,
      };
    });
    // Gaps com vários nomes: eixo Y no mobile (~375px) mantém rótulos legíveis.
    var horizontal = isNarrowViewport() && labels.length > 2;

    return {
      type: 'bar',
      data: { labels: labels, datasets: datasets },
      options: {
        indexAxis: horizontal ? 'y' : 'x',
        responsive: true,
        // Altura vem de .dashboard-chart-canvas (SC-006).
        maintainAspectRatio: false,
        plugins: basePlugins(true),
        scales: barScales(horizontal),
      },
    };
  }

  function buildSingleSeriesConfig(payload) {
    var type = resolveChartType(payload.type);
    var labels = payload.labels || [];
    var values = (payload.values || []).map(asNullableNumber);
    var colors =
      payload.colors && payload.colors.length ? payload.colors : STATUS_TRIAD;
    var isDoughnut = type === 'doughnut';
    // Barra categórica: cores por faixa quando o payload traz triad/lista;
    // legenda Chart.js oculta (eixo + figcaption). Doughnut: legenda com texto.
    var perCategoryColors =
      isDoughnut || (colors.length > 1 && colors.length >= labels.length);
    var fill = perCategoryColors ? colors : colors[0] || STATUS_TRIAD[0];

    var dataset = {
      label: payload.title || '',
      data: values,
      backgroundColor: fill,
      borderColor: isDoughnut ? '#ffffff' : fill,
      borderWidth: isDoughnut ? 2 : 0,
    };
    if (!isDoughnut) {
      dataset.borderRadius = BAR_RADIUS;
      dataset.maxBarThickness = BAR_MAX_THICKNESS;
    }

    var options = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: basePlugins(isDoughnut),
      scales: isDoughnut ? undefined : barScales(),
    };
    if (isDoughnut) {
      options.cutout = DOUGHNUT_CUTOUT;
      options.layout = { padding: 4 };
    }

    return {
      type: type,
      data: {
        labels: labels,
        datasets: [dataset],
      },
      options: options,
    };
  }

  function buildConfig(payload) {
    if (payload.type === 'bar_grouped') {
      return buildGroupedConfig(payload);
    }
    return buildSingleSeriesConfig(payload);
  }

  function initCanvas(canvas) {
    var scriptId = canvas.getAttribute('data-chart-payload');
    if (!scriptId) {
      return;
    }

    var payload = readPayload(scriptId);
    if (!payload || payload.has_data !== true) {
      return;
    }

    if (typeof Chart === 'undefined') {
      return;
    }

    if (canvas.chartInstance) {
      canvas.chartInstance.destroy();
    }

    canvas.chartInstance = new Chart(canvas, buildConfig(payload));
  }

  function initAll() {
    var canvases = document.querySelectorAll('canvas[data-chart-payload]');
    for (var i = 0; i < canvases.length; i += 1) {
      initCanvas(canvases[i]);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
