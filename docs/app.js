const MANIFEST_URL = "./data/manifest.json";

const SIGNIFICANT_EVENTS = new Set([
  "network-built",
  "trivial-check",
  "search-start",
  "level-built",
  "path-found",
  "augment",
  "blocking-flow",
  "min-cut",
  "completed",
]);

const PSEUDOCODE = {
  "edmonds-karp": [
    ["bfs-search", "while BFS 在残量网络中能到达汇点"],
    ["bfs-discover", "  记录每个新节点的父边"],
    ["find-bottleneck", "  bottleneck ← 路径最小剩余容量"],
    ["augment", "  沿路径增加流量并更新反向边"],
    ["terminate", "return 最大流"],
  ],
  dinic: [
    ["build-levels", "while BFS 能构造到达汇点的分层图"],
    ["level-discover", "  level[v] ← level[u] + 1"],
    ["level-complete", "  初始化 current_arc"],
    ["dfs-send", "  DFS 只沿相邻层正残量边推流"],
    ["blocking-flow", "  累加本阶段阻塞流"],
    ["terminate", "return 最大流"],
  ],
};

const state = {
  manifest: null,
  trace: null,
  dataset: null,
  step: 0,
  playing: false,
  timer: null,
  speed: 700,
  edgeState: [],
  transform: { x: 0, y: 0, scale: 1 },
  drag: null,
};

const $ = (id) => document.getElementById(id);

const elements = {
  dataset: $("dataset-select"),
  team: $("team-select"),
  algorithm: $("algorithm-select"),
  speed: $("speed-select"),
  reload: $("reload-button"),
  first: $("first-button"),
  previous: $("previous-button"),
  play: $("play-button"),
  next: $("next-button"),
  last: $("last-button"),
  resetView: $("reset-view-button"),
  stepLabel: $("step-label"),
  progressPercent: $("progress-percent"),
  progressFill: $("progress-fill"),
  metricFlow: $("metric-flow"),
  metricStep: $("metric-step"),
  metricAlgorithm: $("metric-algorithm"),
  metricResult: $("metric-result"),
  stage: $("network-stage"),
  networkEmpty: $("network-empty"),
  stageCaption: $("stage-caption"),
  layoutBadge: $("layout-badge"),
  eventType: $("event-type"),
  eventTitle: $("event-title"),
  eventDetail: $("event-detail"),
  eventMetrics: $("event-metrics"),
  resultCard: $("result-card"),
  pseudocode: $("pseudocode-list"),
  algorithmState: $("algorithm-state"),
  timeline: $("timeline"),
  timelineCount: $("timeline-count"),
  toast: $("toast"),
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(
    () => elements.toast.classList.remove("visible"),
    2400,
  );
}

function activeDataset() {
  return state.manifest.datasets.find(
    (dataset) => dataset.id === elements.dataset.value,
  );
}

function traceFile() {
  const dataset = activeDataset();
  return dataset.trace_index[elements.team.value][elements.algorithm.value];
}

async function loadManifest() {
  const response = await fetch(MANIFEST_URL);
  if (!response.ok) throw new Error(`无法载入 manifest：${response.status}`);
  state.manifest = await response.json();
  elements.dataset.innerHTML = state.manifest.datasets
    .map(
      (dataset) =>
        `<option value="${escapeHtml(dataset.id)}">${escapeHtml(dataset.label)} · ${dataset.team_count} 队</option>`,
    )
    .join("");
  elements.dataset.value = state.manifest.default_dataset;
  populateTeams();
  if ([...elements.team.options].some((option) => option.value === "Philadelphia")) {
    elements.team.value = "Philadelphia";
  }
  elements.algorithm.value = state.manifest.default_algorithm;
}

function populateTeams() {
  const dataset = activeDataset();
  state.dataset = dataset;
  const previous = elements.team.value;
  elements.team.innerHTML = dataset.teams
    .map(
      (team) =>
        `<option value="${escapeHtml(team)}">${escapeHtml(team)}</option>`,
    )
    .join("");
  elements.team.value = dataset.teams.includes(previous)
    ? previous
    : dataset.teams[0];
}

async function loadTrace() {
  stopPlayback();
  setLoading(true);
  try {
    const response = await fetch(`./data/${traceFile()}`);
    if (!response.ok) throw new Error(`轨迹文件载入失败：${response.status}`);
    state.trace = await response.json();
    state.step = 0;
    resetView();
    renderAll();
  } catch (error) {
    showToast(error.message);
    elements.networkEmpty.hidden = false;
    elements.networkEmpty.textContent = error.message;
  } finally {
    setLoading(false);
  }
}

function setLoading(loading) {
  elements.reload.disabled = loading;
  elements.play.disabled = loading;
  if (loading) {
    elements.eventTitle.textContent = "正在载入 Python 轨迹…";
    elements.eventDetail.textContent = "轨迹仅包含预生成的内置数据。";
  }
}

function currentEvent() {
  return state.trace?.events[state.step] ?? null;
}

function deriveFrame() {
  let edges = [];
  for (let index = 0; index <= state.step; index += 1) {
    const eventEdges = state.trace.events[index].payload.edges;
    if (eventEdges) edges = eventEdges;
  }
  return { event: currentEvent(), edges };
}

function setStep(nextStep) {
  if (!state.trace) return;
  state.step = Math.max(0, Math.min(nextStep, state.trace.events.length - 1));
  renderAll();
  if (state.step >= state.trace.events.length - 1) stopPlayback();
}

function stopPlayback() {
  state.playing = false;
  window.clearInterval(state.timer);
  state.timer = null;
  elements.play.textContent = "播放";
}

function startPlayback() {
  if (!state.trace) return;
  if (state.step >= state.trace.events.length - 1) state.step = 0;
  state.playing = true;
  elements.play.textContent = "暂停";
  window.clearInterval(state.timer);
  state.timer = window.setInterval(() => {
    if (state.step >= state.trace.events.length - 1) {
      stopPlayback();
      return;
    }
    state.step += 1;
    renderAll();
  }, state.speed);
}

function togglePlayback() {
  if (state.playing) stopPlayback();
  else startPlayback();
}

function renderAll() {
  if (!state.trace) return;
  const frame = deriveFrame();
  renderHeader(frame);
  renderNetwork(frame);
  renderCurrent(frame);
  renderPseudocode(frame);
  renderAlgorithmState(frame);
  renderTimeline();
  renderPlayback();
}

function renderHeader({ event }) {
  const result = state.trace.result;
  const currentFlow = event.payload.current_flow ?? result.max_flow ?? 0;
  const required = result.required_flow;
  elements.metricFlow.textContent = `${currentFlow} / ${required}`;
  elements.metricStep.textContent = `${state.step + 1} / ${state.trace.events.length}`;
  elements.metricAlgorithm.textContent =
    state.trace.algorithm === "dinic" ? "Dinic" : "E–K";
  elements.metricResult.textContent = result.eliminated ? "已淘汰" : "未淘汰";
  elements.metricResult.style.color = result.eliminated
    ? "var(--red)"
    : "var(--green)";
}

function renderPlayback() {
  const total = state.trace.events.length;
  const percent = total <= 1 ? 100 : (state.step / (total - 1)) * 100;
  elements.stepLabel.textContent = `步骤 ${state.step + 1} / ${total}`;
  elements.progressPercent.textContent = `${Math.round(percent)}%`;
  elements.progressFill.style.width = `${percent}%`;
  elements.first.disabled = state.step === 0;
  elements.previous.disabled = state.step === 0;
  elements.next.disabled = state.step >= total - 1;
  elements.last.disabled = state.step >= total - 1;
}

function activeNodeIds(event) {
  const values = [
    ...(event.payload.path ?? []),
    ...(event.payload.active_path ?? []),
  ];
  if (Number.isInteger(event.payload.from_vertex)) values.push(event.payload.from_vertex);
  if (Number.isInteger(event.payload.to_vertex)) values.push(event.payload.to_vertex);
  return new Set(values);
}

function activeEdgePairs(event) {
  const pairs = new Set();
  for (const edge of event.payload.path_edges ?? []) {
    pairs.add(`${edge.start}:${edge.end}`);
  }
  const path = event.payload.path ?? event.payload.active_path ?? [];
  for (let index = 0; index < path.length - 1; index += 1) {
    pairs.add(`${path[index]}:${path[index + 1]}`);
  }
  if (
    Number.isInteger(event.payload.from_vertex) &&
    Number.isInteger(event.payload.to_vertex)
  ) {
    pairs.add(`${event.payload.from_vertex}:${event.payload.to_vertex}`);
  }
  return pairs;
}

function spreadPositions(count, minY = 70, maxY = 610) {
  if (count <= 1) return [(minY + maxY) / 2];
  return Array.from(
    { length: count },
    (_, index) => minY + ((maxY - minY) * index) / (count - 1),
  );
}

function visibleGraph(frame) {
  const network = state.trace.network;
  const nodes = network.nodes;
  const active = activeNodeIds(frame.event);
  const allGames = nodes.filter((node) => node.kind === "game");
  const complete = nodes.length <= 24;
  let games = allGames;
  let hiddenGames = [];

  if (!complete) {
    const positiveSourceEdges = network.edges
      .filter((edge) => edge.kind === "source-game" && edge.capacity > 0)
      .map((edge) => edge.end);
    const preferred = new Set([
      ...[...active].filter((id) => allGames.some((node) => node.id === id)),
      ...positiveSourceEdges.slice(0, 8),
    ]);
    games = allGames.filter((node) => preferred.has(node.id)).slice(0, 10);
    hiddenGames = allGames.filter(
      (node) => !games.some((visible) => visible.id === node.id),
    );
  }

  const visibleNodes = [
    ...nodes.filter((node) => node.kind === "source"),
    ...games,
    ...nodes.filter((node) => node.kind === "team"),
    ...nodes.filter((node) => node.kind === "sink"),
  ];
  if (hiddenGames.length) {
    visibleNodes.splice(1 + games.length, 0, {
      id: "aggregate-games",
      kind: "aggregate",
      label: `其余比赛 × ${hiddenGames.length}`,
    });
  }
  return { visibleNodes, hiddenGames, complete };
}

function nodeDimensions(node) {
  if (node.kind === "source" || node.kind === "sink") return { width: 58, height: 58 };
  if (node.kind === "aggregate") return { width: 170, height: 52 };
  if (node.kind === "game") return { width: 178, height: 46 };
  return { width: 150, height: 48 };
}

function renderNetwork(frame) {
  const network = state.trace.network;
  if (!network) {
    elements.stage.innerHTML = "";
    elements.networkEmpty.hidden = false;
    elements.networkEmpty.innerHTML =
      `<div><strong>${escapeHtml(state.trace.target_team)} 被直接淘汰</strong><br>` +
      `已有球队胜场超过其最大可能胜场，无需构造流网络。</div>`;
    elements.layoutBadge.textContent = "直接淘汰";
    elements.stageCaption.textContent = "直接比较胜场即可得出结论";
    return;
  }

  elements.networkEmpty.hidden = true;
  const { visibleNodes, hiddenGames, complete } = visibleGraph(frame);
  elements.layoutBadge.textContent = complete
    ? "完整四层网络"
    : `聚合 ${hiddenGames.length} 个比赛节点`;
  elements.stageCaption.textContent =
    "拖动画布或滚轮缩放；橙色表示当前搜索或增广路径。";

  const groups = {
    source: visibleNodes.filter((node) => node.kind === "source"),
    game: visibleNodes.filter(
      (node) => node.kind === "game" || node.kind === "aggregate",
    ),
    team: visibleNodes.filter((node) => node.kind === "team"),
    sink: visibleNodes.filter((node) => node.kind === "sink"),
  };
  const xMap = { source: 75, game: 390, team: 805, sink: 1125 };
  const positions = new Map();
  for (const [kind, group] of Object.entries(groups)) {
    const ys = spreadPositions(group.length);
    group.forEach((node, index) => positions.set(node.id, { x: xMap[kind], y: ys[index] }));
  }

  const edgeState = new Map(
    frame.edges.map((edge) => [`${edge.start}:${edge.edge_index}`, edge]),
  );
  const activePairs = activeEdgePairs(frame.event);
  const sourceSide = new Set(frame.event.payload.source_side ?? []);
  const visibleIds = new Set(visibleNodes.map((node) => node.id));
  const graphEdges = state.trace.network.edges.filter(
    (edge) => visibleIds.has(edge.start) && visibleIds.has(edge.end),
  );

  const defs = `
    <defs>
      <marker id="arrow-default" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0 L0 9 L9 4.5 z" fill="#808995"/></marker>
      <marker id="arrow-warm" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0 L0 9 L9 4.5 z" fill="#f28f3b"/></marker>
      <marker id="arrow-red" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0 0 L0 9 L9 4.5 z" fill="#b42318"/></marker>
    </defs>`;

  const edgeSvg = graphEdges
    .map((edge) => {
      const start = positions.get(edge.start);
      const end = positions.get(edge.end);
      const snapshot = edgeState.get(`${edge.start}:${edge.edge_index}`) ?? {
        flow: 0,
        residual: edge.capacity,
      };
      const pairKey = `${edge.start}:${edge.end}`;
      const active = activePairs.has(pairKey);
      const saturated = snapshot.residual === 0 && edge.capacity > 0;
      const className = active
        ? "network-edge active"
        : saturated
          ? "network-edge saturated"
          : "network-edge available";
      const startDim = nodeDimensions(
        visibleNodes.find((node) => node.id === edge.start),
      );
      const endDim = nodeDimensions(
        visibleNodes.find((node) => node.id === edge.end),
      );
      const x1 = start.x + startDim.width / 2;
      const x2 = end.x - endDim.width / 2;
      const midX = (x1 + x2) / 2;
      const midY = (start.y + end.y) / 2;
      return `
        <g>
          <path class="${className}" d="M ${x1} ${start.y} L ${x2} ${end.y}">
            <title>流量 ${snapshot.flow} / 容量 ${edge.capacity}；剩余 ${snapshot.residual}</title>
          </path>
          <g class="edge-label" transform="translate(${midX - 25} ${midY - 11})">
            <rect width="50" height="22" rx="7"></rect>
            <text x="25" y="15" text-anchor="middle">${snapshot.flow} / ${edge.capacity}</text>
          </g>
        </g>`;
    })
    .join("");

  let aggregateEdges = "";
  const aggregate = positions.get("aggregate-games");
  if (aggregate) {
    const sourceNode = groups.source[0];
    const source = positions.get(sourceNode.id);
    aggregateEdges += `<path class="network-edge available" stroke-dasharray="8 6" d="M ${source.x + 29} ${source.y} L ${aggregate.x - 85} ${aggregate.y}"></path>`;
  }

  const activeNodes = activeNodeIds(frame.event);
  const nodeSvg = visibleNodes
    .map((node) => {
      const { x, y } = positions.get(node.id);
      const dimensions = nodeDimensions(node);
      const active = activeNodes.has(node.id);
      const cut = sourceSide.has(node.id);
      const classes = [
        "network-node",
        node.kind,
        node.kind === "source" || node.kind === "sink" ? "endpoint" : "",
        active ? "active" : "",
        cut ? "cut" : "",
      ]
        .filter(Boolean)
        .join(" ");
      if (node.kind === "source" || node.kind === "sink") {
        return `<g class="${classes}" transform="translate(${x} ${y})"><circle r="29"></circle><text text-anchor="middle" y="6">${node.kind === "source" ? "s" : "t"}</text><title>${escapeHtml(node.label)}</title></g>`;
      }
      return `<g class="${classes}" transform="translate(${x - dimensions.width / 2} ${y - dimensions.height / 2})"><rect width="${dimensions.width}" height="${dimensions.height}" rx="${node.kind === "team" ? 21 : 13}"></rect><text x="${dimensions.width / 2}" y="${dimensions.height / 2 + 5}" text-anchor="middle">${escapeHtml(node.label)}</text><title>${escapeHtml(node.label)}</title></g>`;
    })
    .join("");

  elements.stage.innerHTML = `${defs}<g id="viewport-layer" transform="translate(${state.transform.x} ${state.transform.y}) scale(${state.transform.scale})">${edgeSvg}${aggregateEdges}${nodeSvg}</g>`;
}

function metricCard(label, value) {
  return `<div class="event-metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function renderCurrent({ event }) {
  elements.eventType.textContent = event.type.replaceAll("-", " ");
  elements.eventTitle.textContent = event.title;
  elements.eventDetail.textContent = event.detail || "当前事件没有补充说明。";
  const payloadMetrics = event.payload.metrics ?? state.trace.metrics;
  elements.eventMetrics.innerHTML = [
    metricCard(
      "当前流量",
      `${event.payload.current_flow ?? state.trace.result.max_flow} / ${state.trace.result.required_flow}`,
    ),
    metricCard("边检查次数", String(payloadMetrics.edge_inspections ?? 0)),
    metricCard("BFS 轮次", String(payloadMetrics.bfs_rounds ?? 0)),
    metricCard(
      state.trace.algorithm === "dinic" ? "DFS 调用" : "增广次数",
      String(
        state.trace.algorithm === "dinic"
          ? payloadMetrics.dfs_calls ?? 0
          : payloadMetrics.augmentations ?? 0,
      ),
    ),
  ].join("");

  const result = state.trace.result;
  if (event.type === "completed" || result.trivial) {
    const certificate = result.certificate.length
      ? `证明集合：${result.certificate.join("、")}。`
      : "";
    elements.resultCard.className = `result-card ${result.eliminated ? "eliminated" : "alive"}`;
    elements.resultCard.innerHTML = `
      <h4>${escapeHtml(result.team)} ${result.eliminated ? "被淘汰" : "仍有机会"}</h4>
      <p>最大流 ${result.max_flow} / 待分配比赛 ${result.required_flow}。${escapeHtml(certificate)}</p>`;
  } else {
    elements.resultCard.className = "result-card";
    elements.resultCard.innerHTML = "";
  }
}

function renderPseudocode({ event }) {
  const lines = PSEUDOCODE[state.trace.algorithm];
  elements.pseudocode.innerHTML = lines
    .map(
      ([id, text]) =>
        `<li class="${event.pseudocode_line === id ? "active" : ""}">${escapeHtml(text)}</li>`,
    )
    .join("");
}

function chips(values, empty = "—") {
  if (!values?.length) return `<span class="state-chip">${empty}</span>`;
  return values
    .map((value) => `<span class="state-chip">${escapeHtml(value)}</span>`)
    .join("");
}

function renderAlgorithmState({ event }) {
  const payload = event.payload;
  const metrics = payload.metrics ?? state.trace.metrics;
  const sections = [];
  if (payload.queue) {
    sections.push(`
      <section class="state-section">
        <h3>BFS 队列</h3>
        <div class="state-chips">${chips(payload.queue)}</div>
      </section>`);
  }
  if (payload.levels) {
    sections.push(`
      <section class="state-section">
        <h3>Dinic 节点层级</h3>
        <div class="state-chips">${chips(
          payload.levels.map((level, index) => `${index}:${level}`),
        )}</div>
      </section>`);
  }
  if (payload.active_path || payload.path) {
    sections.push(`
      <section class="state-section">
        <h3>当前路径</h3>
        <div class="state-chips">${chips(
          (payload.active_path ?? payload.path).map(String),
        )}</div>
      </section>`);
  }
  sections.push(`
    <section class="state-section">
      <h3>累计操作计数</h3>
      <div class="event-metrics">
        ${metricCard("边检查", String(metrics.edge_inspections ?? 0))}
        ${metricCard("队列入队", String(metrics.queue_pushes ?? 0))}
        ${metricCard("增广/推流", String(metrics.augmentations ?? 0))}
        ${metricCard("当前弧跳过", String(metrics.current_arc_skips ?? 0))}
      </div>
    </section>`);
  elements.algorithmState.innerHTML = sections.join("");
}

function renderTimeline() {
  const timelineEvents = state.trace.events
    .map((event, index) => ({ event, index }))
    .filter(({ event }) => SIGNIFICANT_EVENTS.has(event.type));
  elements.timelineCount.textContent = `${timelineEvents.length} 个关键事件`;
  elements.timeline.innerHTML = timelineEvents
    .map(
      ({ event, index }) => `
        <button class="timeline-item ${index === state.step ? "active" : ""}" data-step="${index}" type="button">
          <span>STEP ${String(index + 1).padStart(2, "0")} · ${escapeHtml(event.type)}</span>
          <strong>${escapeHtml(event.title)}</strong>
          <span>${escapeHtml(event.detail || "查看网络状态")}</span>
        </button>`,
    )
    .join("");
  for (const button of elements.timeline.querySelectorAll("[data-step]")) {
    button.addEventListener("click", () => {
      stopPlayback();
      setStep(Number(button.dataset.step));
      button.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    });
  }
}

function activateTab(button) {
  for (const tab of document.querySelectorAll(".tab-button")) {
    const selected = tab === button;
    tab.classList.toggle("active", selected);
    tab.setAttribute("aria-selected", String(selected));
    const panel = $(tab.dataset.panel);
    panel.hidden = !selected;
    panel.classList.toggle("active", selected);
  }
}

function resetView() {
  state.transform = { x: 0, y: 0, scale: 1 };
  if (state.trace) renderNetwork(deriveFrame());
}

function bindNetworkInteractions() {
  elements.stage.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault();
      const factor = event.deltaY < 0 ? 1.1 : 0.9;
      state.transform.scale = Math.max(
        0.55,
        Math.min(2.4, state.transform.scale * factor),
      );
      renderNetwork(deriveFrame());
    },
    { passive: false },
  );

  elements.stage.addEventListener("pointerdown", (event) => {
    state.drag = {
      startX: event.clientX,
      startY: event.clientY,
      originX: state.transform.x,
      originY: state.transform.y,
    };
    elements.stage.classList.add("dragging");
    elements.stage.setPointerCapture(event.pointerId);
  });
  elements.stage.addEventListener("pointermove", (event) => {
    if (!state.drag) return;
    state.transform.x = state.drag.originX + event.clientX - state.drag.startX;
    state.transform.y = state.drag.originY + event.clientY - state.drag.startY;
    renderNetwork(deriveFrame());
  });
  elements.stage.addEventListener("pointerup", () => {
    state.drag = null;
    elements.stage.classList.remove("dragging");
  });
}

function bindControls() {
  elements.dataset.addEventListener("change", () => {
    populateTeams();
    if (
      activeDataset().teams.includes("Philadelphia") &&
      activeDataset().id === "teams4"
    ) {
      elements.team.value = "Philadelphia";
    }
    loadTrace();
  });
  elements.team.addEventListener("change", loadTrace);
  elements.algorithm.addEventListener("change", loadTrace);
  elements.reload.addEventListener("click", loadTrace);
  elements.speed.addEventListener("change", () => {
    state.speed = Number(elements.speed.value);
    if (state.playing) startPlayback();
  });
  elements.first.addEventListener("click", () => {
    stopPlayback();
    setStep(0);
  });
  elements.previous.addEventListener("click", () => {
    stopPlayback();
    setStep(state.step - 1);
  });
  elements.play.addEventListener("click", togglePlayback);
  elements.next.addEventListener("click", () => {
    stopPlayback();
    setStep(state.step + 1);
  });
  elements.last.addEventListener("click", () => {
    stopPlayback();
    setStep(state.trace.events.length - 1);
  });
  elements.resetView.addEventListener("click", resetView);
  for (const tab of document.querySelectorAll(".tab-button")) {
    tab.addEventListener("click", () => activateTab(tab));
  }
  bindNetworkInteractions();
}

async function initialize() {
  bindControls();
  try {
    await loadManifest();
    await loadTrace();
  } catch (error) {
    showToast(error.message);
    elements.eventTitle.textContent = "页面初始化失败";
    elements.eventDetail.textContent =
      "请通过本地 HTTP 服务或 GitHub Pages 打开，而不是直接双击 HTML 文件。";
  }
}

initialize();
