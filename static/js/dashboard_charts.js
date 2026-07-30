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

  function basePlugins(showLegend) {
    return {
      legend: {
        display: !!showLegend,
        position: 'bottom',
        labels: {
          usePointStyle: true,
          boxWidth: 10,
        },
      },
      tooltip: {
        enabled: true,
        callbacks: {
          label: tooltipLabel,
        },
      },
    };
  }

  function barScales() {
    return {
      x: {
        ticks: { autoSkip: false, maxRotation: 45, minRotation: 0 },
      },
      y: {
        beginAtZero: true,
        ticks: { precision: 0 },
      },
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
        data: (serie.values || []).map(asNullableNumber),
        backgroundColor: color,
        borderColor: color,
        borderWidth: 1,
      };
    });

    return {
      type: 'bar',
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: basePlugins(true),
        scales: barScales(),
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

    return {
      type: type,
      data: {
        labels: labels,
        datasets: [
          {
            label: payload.title || '',
            data: values,
            backgroundColor: isDoughnut ? colors : colors[0] || STATUS_TRIAD[0],
            borderColor: isDoughnut ? '#ffffff' : colors[0] || STATUS_TRIAD[0],
            borderWidth: isDoughnut ? 2 : 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: basePlugins(true),
        scales: isDoughnut ? undefined : barScales(),
      },
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
