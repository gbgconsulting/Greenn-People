/**
 * Init Chart.js a partir de payloads embutidos (json_script).
 * Carregado só em páginas de dashboard com gráfico (admin → team → personal).
 * Chart.js UMD (cdn) deve estar disponível como `Chart` global antes deste arquivo.
 *
 * Catálogo (contratos/chart-catalog.md · Freeze A):
 *   bar | doughnut | doughnut_or_bar | bar_grouped | bar_horizontal | area | radar
 * Histórico US3: type bar + stacked (100% categórico) + overlay line — sem lib nova.
 * Valor central no doughnut + datalabels em barras: plugins inline (afterDraw /
 * afterDatasetsDraw) — sem plugin npm / lib nova.
 * Barras limpas (DS): grid e ticks de valor off; leitura via datalabel / legend / KPI.
 * Radar (gap pessoal): Chart.js nativo; mesmo shape multi-série de bar_grouped.
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
  var COLOR_INK = '#0f172a';
  var COLOR_INK_MUTED = '#64748b';
  var COLOR_TOOLTIP_BG = '#1e293b';
  /* Acabamento mono teal (não-semântico) — área / séries sem cor no payload. */
  var COLOR_FINISH_TEAL = '#0d9488';
  var BAR_RADIUS = 6;
  var BAR_MAX_THICKNESS = 40;
  /* Barras verticais categóricas (histórico empilhado): ocupam a largura do slot. */
  var BAR_MAX_THICKNESS_DENSE = 72;
  var BAR_CATEGORY_PERCENTAGE = 0.82;
  var BAR_PERCENTAGE = 0.9;
  /* Altura do plot: barras horizontais cabem no nº de categorias; doughnut compacto. */
  var CANVAS_ROW_PX = 36;
  var CANVAS_PAD_PX = 16;
  var CANVAS_MIN_PX = 160;
  var CANVAS_MAX_PX = 304;
  var CANVAS_DOUGHNUT_PX = 208;
  var CANVAS_STACKED_PX = 300;
  var CANVAS_STACKED_PX_NARROW = 280;
  var CANVAS_RADAR_PX = 360;
  var CANVAS_RADAR_PX_NARROW = 300;
  var DOUGHNUT_CUTOUT = '68%';
  var AREA_TENSION = 0.35;
  var AREA_FILL_ALPHA = 0.22;

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

  /**
   * Mapeia type do payload → tipo Chart.js nativo.
   * bar_horizontal → bar (+ indexAxis y); area → line (+ fill); radar → radar.
   */
  function resolveChartType(payloadType) {
    if (payloadType === 'doughnut' || payloadType === 'doughnut_or_bar') {
      return 'doughnut';
    }
    if (payloadType === 'area') {
      return 'line';
    }
    if (payloadType === 'radar') {
      return 'radar';
    }
    return 'bar';
  }

  /** Quebra rótulos do radar em até 2 linhas (evita corte no canvas). */
  function wrapRadarLabel(label) {
    var text = String(label || '').trim();
    if (!text) {
      return [''];
    }
    var maxChars = isNarrowViewport() ? 14 : 18;
    if (text.length <= maxChars) {
      return [text];
    }
    var words = text.split(/\s+/);
    if (words.length === 1) {
      return [text.slice(0, maxChars - 1) + '…'];
    }
    var line1 = words[0];
    var i = 1;
    while (i < words.length && (line1 + ' ' + words[i]).length <= maxChars) {
      line1 += ' ' + words[i];
      i += 1;
    }
    var rest = words.slice(i).join(' ');
    if (!rest) {
      return [line1];
    }
    if (rest.length > maxChars) {
      rest = rest.slice(0, maxChars - 1) + '…';
    }
    return [line1, rest];
  }

  function hexToRgba(hex, alpha) {
    var raw = String(hex || '').replace('#', '');
    if (raw.length === 3) {
      raw = raw[0] + raw[0] + raw[1] + raw[1] + raw[2] + raw[2];
    }
    if (raw.length !== 6) {
      return 'rgba(13, 148, 136, ' + alpha + ')';
    }
    var r = parseInt(raw.slice(0, 2), 16);
    var g = parseInt(raw.slice(2, 4), 16);
    var b = parseInt(raw.slice(4, 6), 16);
    return 'rgba(' + r + ', ' + g + ', ' + b + ', ' + alpha + ')';
  }

  /** Texto do centro: center_text (opcional) ou total do payload — sem inventar %. */
  function resolveDoughnutCenterText(payload) {
    if (payload.center_text !== null && payload.center_text !== undefined && payload.center_text !== '') {
      return String(payload.center_text);
    }
    if (payload.total !== null && payload.total !== undefined && payload.total !== '') {
      return String(payload.total);
    }
    return '';
  }

  /**
   * Plugin inline Chart.js 4.x — valor central no doughnut (research R1).
   * Sem chartjs-plugin-datalabels / npm.
   */
  function doughnutCenterPlugin(centerText) {
    return {
      id: 'doughnutCenterValue',
      afterDraw: function (chart) {
        if (!centerText || chart.config.type !== 'doughnut') {
          return;
        }
        var meta = chart.getDatasetMeta(0);
        if (!meta || !meta.data || !meta.data.length) {
          return;
        }
        var anchor = meta.data[0];
        if (!anchor || anchor.x === undefined || anchor.y === undefined) {
          return;
        }
        var narrow = isNarrowViewport();
        var ctx = chart.ctx;
        ctx.save();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = COLOR_INK;
        ctx.font =
          (narrow ? '600 18px ' : '600 22px ') + FONT_UI;
        ctx.fillText(centerText, anchor.x, anchor.y);
        ctx.restore();
      },
    };
  }

  function asNullableNumber(value) {
    if (value === null || value === undefined) {
      return null;
    }
    return value;
  }

  function formatChartValue(raw, valueUnit) {
    if (raw === null || raw === undefined) {
      return '—';
    }
    var text = String(raw);
    if (valueUnit) {
      return text + valueUnit;
    }
    return text;
  }

  function chartValueUnit(chart) {
    return (chart && chart.options && chart.options.greennValueUnit) || '';
  }

  function tooltipLabel(ctx) {
    var datasetLabel = ctx.dataset && ctx.dataset.label ? ctx.dataset.label : '';
    var categoryLabel = ctx.label || '';
    var parsed = ctx.parsed;
    var value;
    var unit = chartValueUnit(ctx.chart);

    if (parsed === null || parsed === undefined) {
      return datasetLabel || categoryLabel || '';
    }
    if (typeof parsed === 'object') {
      // bar_horizontal (indexAxis y): valor em parsed.x
      if (ctx.chart && ctx.chart.options && ctx.chart.options.indexAxis === 'y') {
        value = parsed.x;
      } else {
        value = parsed.y !== undefined ? parsed.y : parsed.x;
      }
    } else {
      value = parsed;
    }

    if (value === null || value === undefined) {
      return (datasetLabel || categoryLabel) + ': —';
    }

    var formatted = formatChartValue(value, unit);
    if (datasetLabel && categoryLabel && ctx.chart.config.type === 'bar') {
      return datasetLabel + ': ' + formatted;
    }
    if (datasetLabel) {
      return datasetLabel + ': ' + formatted;
    }
    return categoryLabel + ': ' + formatted;
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
   * Barra única categórica: oculta (datalabel + figcaption cobrem).
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

  function axisBorderHidden() {
    return { display: false };
  }

  /**
   * Escalas “barras limpas” (DS Charts polish):
   * grid off; ticks de valor off (leitura via datalabel / legend / KPI);
   * eixo de categoria só com labels textuais.
   * `mode`: 'bar' | 'area' — area mantém o mesmo padrão limpo (grid mínimo = off).
   */
  function cleanScales(horizontal, mode) {
    var narrow = isNarrowViewport();
    var tickFont = chartFont({ size: narrow ? 10 : 12, weight: '400' });
    var isArea = mode === 'area';
    var categoryAxis = {
      grid: { display: false },
      border: axisBorderHidden(),
      ticks: {
        autoSkip: isArea ? true : false,
        maxRotation: horizontal ? 0 : narrow ? 45 : 0,
        minRotation: 0,
        color: COLOR_INK_MUTED,
        font: tickFont,
        padding: 6,
      },
    };
    var valueAxis = {
      beginAtZero: true,
      border: axisBorderHidden(),
      grid: { display: false },
      ticks: {
        display: false,
      },
      // Folga para datalabels não colarem na borda do canvas (barras baixas vs pico).
      grace: isArea ? '0%' : '18%',
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

  /**
   * Plugin inline — valor na barra (sem chartjs-plugin-datalabels / npm).
   * Substitui ticks do eixo de valor (DS: priorizar rótulos de dados).
   * Barras curtas (ex. 1 vs 138): mantém folga mínima do baseline para o
   * número não colidir com o eixo de categoria — o valor não depende da altura.
   */
  function barValueLabelsPlugin(horizontal) {
    return {
      id: 'barValueLabels',
      afterDatasetsDraw: function (chart) {
        if (chart.config.type !== 'bar') {
          return;
        }
        var ctx = chart.ctx;
        var narrow = isNarrowViewport();
        var fontSize = narrow ? 11 : 12;
        var unit = chartValueUnit(chart);
        // Folga mínima do baseline (barras verticais) para rótulos legíveis.
        var minClearanceFromBase = fontSize + 8;
        ctx.save();
        ctx.font = '600 ' + fontSize + 'px ' + FONT_UI;
        ctx.fillStyle = COLOR_INK;
        chart.data.datasets.forEach(function (dataset, datasetIndex) {
          var meta = chart.getDatasetMeta(datasetIndex);
          if (!meta || meta.hidden) {
            return;
          }
          meta.data.forEach(function (element, index) {
            var raw = dataset.data[index];
            if (raw === null || raw === undefined) {
              return;
            }
            var text = formatChartValue(raw, unit);
            var pos = element.tooltipPosition();
            if (horizontal) {
              ctx.textAlign = 'left';
              ctx.textBaseline = 'middle';
              ctx.fillText(text, pos.x + 8, pos.y);
            } else {
              ctx.textAlign = 'center';
              ctx.textBaseline = 'bottom';
              // Acima da barra; se a barra for baixa demais, sobe o rótulo
              // para não afundar no eixo — valor sempre legível.
              var base = element.base;
              var aboveBar = pos.y - 6;
              var labelY =
                typeof base === 'number'
                  ? Math.min(aboveBar, base - minClearanceFromBase)
                  : aboveBar;
              ctx.fillText(text, pos.x, labelY);
            }
          });
        });
        ctx.restore();
      },
    };
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

  function buildGroupedConfig(payload) {
    var labels = payload.labels || [];
    var seriesList = payload.series || [];
    var datasets = seriesList.map(function (serie, index) {
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
    // Datalabels em comparativos curtos (DS); muitos pontos → tooltip + figcaption.
    var showValueLabels = labels.length * Math.max(seriesList.length, 1) <= 12;

    return {
      type: 'bar',
      data: { labels: labels, datasets: datasets },
      options: {
        indexAxis: horizontal ? 'y' : 'x',
        responsive: true,
        // Altura vem de .dashboard-chart-canvas (SC-006).
        maintainAspectRatio: false,
        plugins: basePlugins(true),
        scales: cleanScales(horizontal, 'bar'),
        layout: {
          padding: horizontal
            ? { top: 4, right: 28, bottom: 4, left: 4 }
            : { top: 28, right: 8, bottom: 4, left: 4 },
        },
      },
      plugins: showValueLabels ? [barValueLabelsPlugin(horizontal)] : [],
    };
  }

  /**
   * Radar esperado × nota (gap pessoal) — Chart.js nativo; mesmo shape de
   * bar_grouped. null permanece null (não vira 0). Paleta GROUPED_DEFAULTS.
   */
  function buildRadarConfig(payload) {
    var labels = payload.labels || [];
    var seriesList = payload.series || [];
    var datasets = seriesList.map(function (serie, index) {
      var color =
        serie.color ||
        GROUPED_DEFAULTS[serie.key] ||
        STATUS_TRIAD[index % STATUS_TRIAD.length];
      return {
        label: serie.label || serie.key || 'Série ' + (index + 1),
        data: (serie.values || []).map(asNullableNumber),
        backgroundColor: hexToRgba(color, 0.18),
        borderColor: color,
        borderWidth: 2,
        pointBackgroundColor: color,
        pointBorderColor: '#ffffff',
        pointBorderWidth: 1,
        pointRadius: 3,
        pointHoverRadius: 4,
        fill: true,
        spanGaps: false,
      };
    });

    return {
      type: 'radar',
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: basePlugins(true),
        scales: {
          r: {
            beginAtZero: true,
            ticks: {
              display: false,
              backdropColor: 'transparent',
              showLabelBackdrop: false,
            },
            grid: {
              color: 'rgba(148, 163, 184, 0.35)',
            },
            angleLines: {
              color: 'rgba(148, 163, 184, 0.35)',
            },
            pointLabels: {
              color: COLOR_INK,
              font: chartFont({ size: isNarrowViewport() ? 10 : 11 }),
              padding: isNarrowViewport() ? 6 : 10,
              callback: function (label) {
                return wrapRadarLabel(label);
              },
            },
          },
        },
        // Padding generoso para pointLabels não serem clipados pelo canvas.
        layout: { padding: { top: 28, right: 32, bottom: 24, left: 32 } },
      },
    };
  }

  function buildSingleSeriesConfig(payload) {
    var type = resolveChartType(payload.type);
    var labels = payload.labels || [];
    var values = (payload.values || []).map(asNullableNumber);
    var isDoughnut = type === 'doughnut';
    var horizontal = payload.type === 'bar_horizontal';
    // Doughnut = Status Triad; bar / bar_horizontal = mono teal.
    // Amber no gargalo só quando o payload (highlight_max) traz colors.
    var defaultColors = isDoughnut ? STATUS_TRIAD : [COLOR_FINISH_TEAL];
    var colors =
      payload.colors && payload.colors.length ? payload.colors : defaultColors;
    var valueUnit = payload.value_unit || '';
    // Barra categórica: cores por faixa quando o payload traz triad/lista;
    // legenda Chart.js oculta (datalabel + figcaption). Doughnut: legenda com texto.
    var perCategoryColors =
      isDoughnut || (colors.length > 1 && colors.length >= labels.length);
    var fill = perCategoryColors
      ? colors
      : colors[0] || (isDoughnut ? STATUS_TRIAD[0] : COLOR_FINISH_TEAL);

    var dataset = {
      label: payload.title || '',
      data: values,
      backgroundColor: fill,
      borderColor: isDoughnut ? '#ffffff' : fill,
      borderWidth: isDoughnut ? 2 : 0,
    };
    if (!isDoughnut) {
      dataset.borderRadius = BAR_RADIUS;
      // Horizontal (pipeline / cobertura): espessura fixa — a altura do canvas
      // acompanha o nº de categorias. Vertical: preenche a largura do slot.
      dataset.maxBarThickness = horizontal
        ? BAR_MAX_THICKNESS
        : BAR_MAX_THICKNESS_DENSE;
      dataset.categoryPercentage = BAR_CATEGORY_PERCENTAGE;
      dataset.barPercentage = BAR_PERCENTAGE;
    }

    var options = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: basePlugins(isDoughnut),
      scales: isDoughnut ? undefined : cleanScales(horizontal, 'bar'),
      greennValueUnit: valueUnit,
    };
    if (horizontal) {
      options.indexAxis = 'y';
      // Folga extra quando o datalabel leva sufixo (ex. "100%").
      options.layout = {
        padding: {
          top: 4,
          right: valueUnit ? 44 : 32,
          bottom: 4,
          left: 4,
        },
      };
    } else if (!isDoughnut) {
      options.layout = { padding: { top: 28, right: 8, bottom: 4, left: 4 } };
    }
    if (isDoughnut) {
      options.cutout = DOUGHNUT_CUTOUT;
      options.layout = { padding: 4 };
    }

    // Painel do time: barras do pipeline filtram a tabela (toggle ?etapa=).
    if (
      !isDoughnut &&
      payload.id === 'chart-escopo-status' &&
      payload.keys &&
      payload.keys.length
    ) {
      attachTeamStageFilterHandlers(options, payload);
    }

    var config = {
      type: type,
      data: {
        labels: labels,
        datasets: [dataset],
      },
      options: options,
      plugins: [],
    };

    if (isDoughnut) {
      var centerText = resolveDoughnutCenterText(payload);
      if (centerText) {
        config.plugins.push(doughnutCenterPlugin(centerText));
      }
    } else {
      config.plugins.push(barValueLabelsPlugin(horizontal));
    }

    return config;
  }

  /**
   * Tendência temporal: Chart.js `line` + fill (type payload `area`).
   * Aceita `values` (série única) ou `series` (multi-área) — sem inventar pontos.
   */
  function buildAreaConfig(payload) {
    var labels = payload.labels || [];
    var seriesList = payload.series || [];
    var datasets;
    var showLegend;

    if (seriesList.length) {
      showLegend = true;
      datasets = seriesList.map(function (serie, index) {
        var color =
          serie.color ||
          GROUPED_DEFAULTS[serie.key] ||
          (payload.colors && payload.colors[index]) ||
          COLOR_FINISH_TEAL;
        return {
          label: serie.label || serie.key || 'Série ' + (index + 1),
          data: (serie.values || []).map(asNullableNumber),
          borderColor: color,
          backgroundColor: hexToRgba(color, AREA_FILL_ALPHA),
          fill: true,
          tension: AREA_TENSION,
          borderWidth: 2,
          pointRadius: isNarrowViewport() ? 2 : 3,
          pointHoverRadius: 5,
          pointBackgroundColor: color,
          spanGaps: false,
        };
      });
    } else {
      showLegend = false;
      var color =
        (payload.colors && payload.colors[0]) || COLOR_FINISH_TEAL;
      datasets = [
        {
          label: payload.title || '',
          data: (payload.values || []).map(asNullableNumber),
          borderColor: color,
          backgroundColor: hexToRgba(color, AREA_FILL_ALPHA),
          fill: true,
          tension: AREA_TENSION,
          borderWidth: 2,
          pointRadius: isNarrowViewport() ? 2 : 3,
          pointHoverRadius: 5,
          pointBackgroundColor: color,
          spanGaps: false,
        },
      ];
    }

    return {
      type: 'line',
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: basePlugins(showLegend),
        // Area: labels de categoria; eixo de valor e grid off (DS — limpo).
        scales: cleanScales(false, 'area'),
        layout: { padding: { top: 8, right: 8, bottom: 4, left: 4 } },
        elements: {
          line: { borderJoinStyle: 'round' },
        },
      },
    };
  }

  /**
   * Largura das barras empilhadas — alinhado ao mockup ciclo_historico (barThickness 40).
   * Poucos ciclos: barras largas + eixo com offset preenchem o plot horizontalmente.
   */
  function stackedBarLayout(labelCount) {
    if (labelCount <= 6) {
      return {
        barThickness: 40,
        categoryPercentage: 0.82,
        barPercentage: 0.9,
      };
    }
    return {
      maxBarThickness: 40,
      categoryPercentage: BAR_CATEGORY_PERCENTAGE,
      barPercentage: BAR_PERCENTAGE,
    };
  }

  function stackedCanvasHeight(labelCount) {
    var base = isNarrowViewport() ? CANVAS_STACKED_PX_NARROW : CANVAS_STACKED_PX;
    if (labelCount > 5) {
      return base + 28;
    }
    return base;
  }

  function stackedBorderRadius(datasetIndex, barDatasetCount) {
    if (barDatasetCount <= 1) {
      return BAR_RADIUS;
    }
    if (datasetIndex === 0) {
      return { bottomLeft: BAR_RADIUS, bottomRight: BAR_RADIUS, topLeft: 0, topRight: 0 };
    }
    if (datasetIndex === barDatasetCount - 1) {
      return { topLeft: BAR_RADIUS, topRight: BAR_RADIUS, bottomLeft: 0, bottomRight: 0 };
    }
    return 0;
  }

  function observeChartResize(canvas) {
    var wrap = canvas.parentElement;
    if (!wrap || typeof ResizeObserver === 'undefined') {
      return;
    }
    if (wrap._greennChartRo) {
      return;
    }
    var ro = new ResizeObserver(function () {
      if (canvas.chartInstance) {
        canvas.chartInstance.resize();
      }
    });
    ro.observe(wrap);
    wrap._greennChartRo = ro;
  }

  function formatIsoDatePt(iso) {
    if (!iso) {
      return '';
    }
    var parts = String(iso).split('-');
    if (parts.length < 3) {
      return String(iso);
    }
    var months = [
      'jan', 'fev', 'mar', 'abr', 'mai', 'jun',
      'jul', 'ago', 'set', 'out', 'nov', 'dez',
    ];
    var monthIndex = parseInt(parts[1], 10) - 1;
    var month = months[monthIndex] || parts[1];
    return parts[2] + ' ' + month + ' ' + parts[0];
  }

  /**
   * Barra 100% empilhada (ciclos categóricos) + linha de conclusão no mesmo eixo.
   * Sem segundo eixo; sem plugin npm. Legenda nativa off — HTML em _chart_block.
   */
  function buildStackedPercentConfig(payload) {
    var labels = payload.labels || [];
    var seriesList = payload.series || [];
    var unit = payload.value_unit || '%';
    var xMeta = payload.x_meta || [];
    var points = payload.points || [];
    var detalheLabels = payload.detalhe_labels || {};
    var barLayout = stackedBarLayout(labels.length);
    var barSeriesCount = seriesList.filter(function (s) {
      return s.kind !== 'line';
    }).length;
    var barDatasetIndex = 0;
    var datasets = seriesList.map(function (serie, index) {
      var color =
        serie.color ||
        (payload.colors && payload.colors[index]) ||
        COLOR_FINISH_TEAL;
      var isLine = serie.kind === 'line';
      var data = (serie.values || []).map(asNullableNumber);
      if (isLine) {
        return {
          type: 'line',
          label: serie.label || serie.key || 'Série ' + (index + 1),
          data: data,
          borderColor: color,
          backgroundColor: color,
          fill: false,
          tension: 0.25,
          borderWidth: 2,
          pointRadius: isNarrowViewport() ? 2 : 3,
          pointHoverRadius: 5,
          pointBackgroundColor: color,
          order: 0,
          yAxisID: 'y',
          spanGaps: false,
        };
      }
      var dsBarIndex = barDatasetIndex;
      barDatasetIndex += 1;
      return {
        type: 'bar',
        label: serie.label || serie.key || 'Série ' + (index + 1),
        data: data,
        backgroundColor: color,
        borderColor: color,
        borderWidth: 0,
        borderRadius: stackedBorderRadius(dsBarIndex, barSeriesCount),
        barThickness: barLayout.barThickness,
        maxBarThickness: barLayout.maxBarThickness,
        categoryPercentage: barLayout.categoryPercentage,
        barPercentage: barLayout.barPercentage,
        stack: 'stack0',
        order: 1,
        skipNull: true,
      };
    });

    var plugins = basePlugins(true);
    plugins.tooltip.callbacks.title = function (items) {
      if (!items || !items.length) {
        return '';
      }
      var idx = items[0].dataIndex;
      var meta = xMeta[idx] || {};
      var name = meta.ciclo || items[0].label || '';
      var when = formatIsoDatePt(meta.data);
      if (name && when) {
        return name + ' · ' + when;
      }
      return name || when;
    };
    plugins.tooltip.callbacks.afterBody = function (items) {
      if (!items || !items.length) {
        return [];
      }
      var idx = items[0].dataIndex;
      var point = points[idx] || {};
      var detalhe = point.detalhe_etapas || {};
      var lines = [];
      Object.keys(detalhe).forEach(function (key) {
        var count = detalhe[key];
        if (!count) {
          return;
        }
        var label = detalheLabels[key] || key;
        lines.push(label + ': ' + count);
      });
      return lines;
    };

    var narrow = isNarrowViewport();
    var tickFont = chartFont({ size: narrow ? 10 : 12, weight: '400' });

    return {
      type: 'bar',
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: plugins,
        greennValueUnit: unit,
        scales: {
          x: {
            stacked: true,
            offset: true,
            grid: { display: false },
            border: axisBorderHidden(),
            ticks: {
              autoSkip: true,
              maxRotation: narrow ? 45 : 0,
              minRotation: 0,
              color: COLOR_INK_MUTED,
              font: tickFont,
              padding: 6,
            },
          },
          y: {
            stacked: true,
            min: 0,
            max: 100,
            beginAtZero: true,
            border: axisBorderHidden(),
            grid: { display: false },
            ticks: {
              display: true,
              stepSize: 50,
              color: COLOR_INK_MUTED,
              font: tickFont,
              callback: function (value) {
                return String(value) + unit;
              },
            },
          },
        },
        layout: { padding: { top: 8, right: 8, bottom: 4, left: 4 } },
      },
    };
  }

  function buildConfig(payload) {
    if (payload.type === 'bar_grouped') {
      return buildGroupedConfig(payload);
    }
    if (payload.type === 'radar') {
      return buildRadarConfig(payload);
    }
    if (payload.type === 'area') {
      return buildAreaConfig(payload);
    }
    if (payload.stacked === true) {
      return buildStackedPercentConfig(payload);
    }
    return buildSingleSeriesConfig(payload);
  }

  /**
   * Clique nas barras de "Estágios do ciclo" → filtra Visão do time (?etapa=).
   * Valor 0: ignora. Mesma etapa ativa: limpa (toggle). Scroll suave à tabela.
   */
  function attachTeamStageFilterHandlers(options, payload) {
    var keys = payload.keys || [];
    var values = (payload.values || []).map(asNullableNumber);

    options.onHover = function (evt, elements) {
      var target =
        (evt && evt.native && evt.native.target) ||
        (evt && evt.chart && evt.chart.canvas) ||
        null;
      if (!target || !target.style) {
        return;
      }
      var cursor = 'default';
      if (elements && elements.length) {
        var idx = elements[0].index;
        var val = values[idx];
        if (typeof val === 'number' && val > 0) {
          cursor = 'pointer';
        }
      }
      target.style.cursor = cursor;
    };

    options.onClick = function (_evt, elements) {
      if (!elements || !elements.length) {
        return;
      }
      var idx = elements[0].index;
      var val = values[idx];
      if (typeof val !== 'number' || val <= 0) {
        return;
      }
      var key = keys[idx];
      if (!key) {
        return;
      }
      applyTeamStageFilter(key);
    };
  }

  function applyTeamStageFilter(etapaKey) {
    var url = new URL(window.location.href);
    var current = url.searchParams.get('etapa') || '';
    if (current === etapaKey) {
      url.searchParams.delete('etapa');
    } else {
      url.searchParams.set('etapa', etapaKey);
    }
    url.searchParams.delete('page');
    var path = url.pathname + url.search;
    var list = document.getElementById('list-container');

    function scrollToTeamList() {
      var heading = document.getElementById('team-drilldown-heading');
      if (heading && heading.scrollIntoView) {
        heading.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }

    if (list && typeof htmx !== 'undefined' && htmx.ajax) {
      htmx
        .ajax('GET', path, {
          target: '#list-container',
          swap: 'outerHTML',
        })
        .then(function () {
          if (window.history && window.history.pushState) {
            window.history.pushState({}, '', path);
          }
          scrollToTeamList();
        });
      return;
    }

    window.location.assign(path);
  }

  /**
   * Ajusta a altura do wrapper ao conteúdo — evita canvas 19rem com 5–7 barras.
   * Default CSS (15.5 / 17 / 19 rem) permanece como teto e fallback.
   */
  function fitCanvasFrame(canvas, payload) {
    var wrap = canvas.parentElement;
    if (!wrap) {
      return;
    }
    var heightPx = null;
    var type = payload.type;
    if (type === 'doughnut' || type === 'doughnut_or_bar') {
      heightPx = isNarrowViewport() ? 192 : CANVAS_DOUGHNUT_PX;
    } else if (type === 'radar') {
      heightPx = isNarrowViewport() ? CANVAS_RADAR_PX_NARROW : CANVAS_RADAR_PX;
    } else if (type === 'bar_horizontal') {
      var n = (payload.labels || []).length;
      heightPx = Math.min(
        CANVAS_MAX_PX,
        Math.max(CANVAS_MIN_PX, n * CANVAS_ROW_PX + CANVAS_PAD_PX),
      );
    } else if (payload.stacked === true) {
      var n = (payload.labels || []).length;
      heightPx = stackedCanvasHeight(n);
    }
    if (heightPx) {
      wrap.style.height = heightPx + 'px';
      wrap.style.minHeight = heightPx + 'px';
    }
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

    fitCanvasFrame(canvas, payload);
    canvas.chartInstance = new Chart(canvas, buildConfig(payload));
    observeChartResize(canvas);
    // Re-mede após o layout (grid/flex) assentar — evita canvas 0×N em branco.
    requestAnimationFrame(function () {
      if (canvas.chartInstance) {
        canvas.chartInstance.resize();
      }
    });
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        if (canvas.chartInstance) {
          canvas.chartInstance.resize();
        }
      });
    });
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
