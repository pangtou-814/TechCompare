import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { Activity, ArrowDownToLine, ArrowRight, BarChart3, ChevronDown, CircuitBoard, Database, FlaskConical, Layers3, LayoutDashboard, Menu, Search, SlidersHorizontal, X } from 'lucide-react';
import './styles.css';

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);

const PROCESS = ['T12', 'T22', 'T28', 'T65'];
const COLORS = { T12: '#0d9f91', T22: '#4c78de', T28: '#9468cc', T65: '#e2a64a' };
const LABELS = { nmos: 'NMOS', pmos: 'PMOS', inv: '反相器', svt: 'SVT', ulvt: 'ULVT' };
const METRICS = {
  ft: { name: '截止频率 fT', unit: 'GHz', factor: 1e-9, digits: 2 },
  gm: { name: '跨导 gm', unit: 'mS', factor: 1e3, digits: 4 },
  gds: { name: '输出电导 gds', unit: 'mS', factor: 1e3, digits: 4 },
  ids: { name: '漏极电流 Ids', unit: 'mA', factor: 1e3, digits: 5 },
  gm_id: { name: '跨导效率 gm/Id', unit: 'V⁻¹', factor: 1, digits: 2 },
  gain: { name: '本征增益', unit: '', factor: 1, digits: 2 },
  vth: { name: '阈值电压 Vth', unit: 'V', factor: 1, digits: 4 },
  vdsat: { name: '饱和电压 Vdsat', unit: 'V', factor: 1, digits: 4 },
  cgg: { name: '栅极电容 Cgg', unit: 'fF', factor: 1e15, digits: 4 },
  cgs: { name: '栅源电容 Cgs', unit: 'fF', factor: 1e15, digits: 4 },
  cgd: { name: '栅漏电容 Cgd', unit: 'fF', factor: 1e15, digits: 4 },
};
const MOS_METRICS = ['ft', 'gm', 'gds', 'ids', 'gm_id', 'gain', 'vth', 'vdsat', 'cgg', 'cgs', 'cgd'];
const INV_METRICS = ['ft', 'ids', 'gm_nmos', 'gm_pmos', 'gds_nmos', 'gds_pmos', 'gm_id_nmos', 'gm_id_pmos', 'gain_nmos', 'gain_pmos', 'vth_nmos', 'vth_pmos', 'vdsat_nmos', 'vdsat_pmos', 'cgg_nmos', 'cgg_pmos', 'cgs_nmos', 'cgs_pmos', 'cgd_nmos', 'cgd_pmos'];
const closeEnough = (a, b) => Math.abs(a - b) < 0.000001;
const fixed = value => Number(value).toFixed(2);
const metricConfig = key => {
  if (METRICS[key]) return METRICS[key];
  const match = /^(.*)_(nmos|pmos)$/.exec(key);
  if (match && METRICS[match[1]]) return { ...METRICS[match[1]], name: `${match[2].toUpperCase()} ${METRICS[match[1]].name}` };
  return { name: key, unit: '', factor: 1, digits: 4 };
};
const scaled = (record, key) => record?.metrics[key] === undefined ? null : record.metrics[key] * metricConfig(key).factor;
const formatMetric = (record, key) => {
  const value = scaled(record, key);
  if (value === null) return '—';
  const config = metricConfig(key);
  return `${value.toLocaleString('zh-CN', { maximumFractionDigits: config.digits })}${config.unit ? ` ${config.unit}` : ''}`;
};
const metricName = key => metricConfig(key).name;

function Chart({ option, onPoint, className = '' }) {
  const element = useRef(null);
  const chart = useRef(null);
  useEffect(() => {
    if (!element.current) return;
    chart.current = echarts.init(element.current, null, { renderer: 'canvas' });
    const observer = new ResizeObserver(() => chart.current?.resize());
    observer.observe(element.current);
    return () => { observer.disconnect(); chart.current?.dispose(); chart.current = null; };
  }, []);
  useEffect(() => {
    chart.current?.setOption(option, true);
    chart.current?.off('click');
    if (onPoint) chart.current?.on('click', onPoint);
  }, [option, onPoint]);
  return <div ref={element} className={`chart ${className}`} role="img" aria-label="工艺性能曲线" />;
}

function lineOption(series, xLabel, metric) {
  const config = metricConfig(metric);
  return {
    animationDuration: 450,
    color: PROCESS.map(p => COLORS[p]),
    grid: { left: 58, right: 20, top: 27, bottom: 48, containLabel: false },
    legend: { show: false },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'line', lineStyle: { color: '#a7b7c7', type: 'dashed' } },
      backgroundColor: '#172236', borderWidth: 0, textStyle: { color: '#f4f7fb', fontSize: 12 },
      padding: [10, 13], confine: true,
      formatter: items => `<div class="tooltip-title">${xLabel} ${fixed(items[0]?.axisValue || 0)} V</div>${items.filter(item => item.data?.[1] !== null).map(item => `<div class="tooltip-row"><span class="tooltip-dot" style="background:${item.color}"></span>${item.seriesName}<b>${Number(item.data[1]).toFixed(config.digits)} ${config.unit}</b></div>`).join('')}`,
    },
    xAxis: {
      type: 'value', scale: true, name: `${xLabel} (V)`, nameLocation: 'middle', nameGap: 30,
      nameTextStyle: { color: '#748195', fontSize: 11, fontFamily: 'IBM Plex Mono' },
      axisLine: { lineStyle: { color: '#d9e1ea' } }, axisTick: { show: false },
      axisLabel: { color: '#8b98a8', fontSize: 11, formatter: value => Number(value).toFixed(2) },
      splitLine: { lineStyle: { color: '#edf1f5' } },
    },
    yAxis: {
      type: 'value', name: config.unit,
      nameTextStyle: { color: '#8b98a8', fontSize: 11, align: 'right' },
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: '#8b98a8', fontSize: 11, formatter: v => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : Number(v).toFixed(v < 1 && v !== 0 ? 2 : 0) },
      splitLine: { lineStyle: { color: '#edf1f5' } },
    },
    series: series.map(item => ({
      name: item.process, type: 'line', data: item.points.map(p => [p.x, p.y]),
      connectNulls: false, showSymbol: true, symbol: 'circle', symbolSize: 7,
      lineStyle: { width: 2.8, color: COLORS[item.process] },
      itemStyle: { color: COLORS[item.process], borderColor: '#fff', borderWidth: 1.5 },
      emphasis: { focus: 'series', scale: 1.5 },
    })),
  };
}

function Pill({ active, children, onClick, color, disabled = false }) {
  return <button className={`pill ${active ? 'active' : ''}`} style={active && color ? { '--pill-color': color } : undefined} onClick={onClick} disabled={disabled} type="button">{children}</button>;
}

function Stat({ icon: Icon, label, value, foot, accent }) {
  return <div className="stat-card"><div className="stat-top"><span>{label}</span><span className="stat-icon" style={{ color: accent }}><Icon size={17} strokeWidth={1.8} /></span></div><strong>{value}</strong><small>{foot}</small></div>;
}

function App() {
  const [records, setRecords] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [view, setView] = useState('overview');
  const [mobileMenu, setMobileMenu] = useState(false);
  const [device, setDevice] = useState('nmos');
  const [vt, setVt] = useState('svt');
  const [processes, setProcesses] = useState(PROCESS);
  const [metric, setMetric] = useState('ft');
  const [vds, setVds] = useState(0.5);
  const [vgs, setVgs] = useState(0.6);
  const [vdd, setVdd] = useState(1.2);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}process-data.json`).then(response => {
      if (!response.ok) throw new Error('数据文件读取失败');
      return response.json();
    }).then(data => setRecords(data.records)).catch(error => setLoadError(error.message));
  }, []);

  const changeDevice = next => { setDevice(next); setMetric('ft'); setSearch(''); setPage(1); };
  const changeVt = next => { setVt(next); if (next === 'ulvt') setProcesses(current => { const supported = current.filter(p => p !== 'T65'); return supported.length ? supported : ['T12']; }); setSearch(''); setPage(1); };
  const toggleProcess = process => setProcesses(current => current.includes(process) ? (current.length === 1 ? current : current.filter(p => p !== process)) : [...current, process].sort((a, b) => PROCESS.indexOf(a) - PROCESS.indexOf(b)));
  const filtered = useMemo(() => (records || []).filter(r => r.device === device && r.vt === vt && processes.includes(r.process)), [records, device, vt, processes]);
  const available = useMemo(() => [...new Set(filtered.map(r => r.process))], [filtered]);
  const allSelectedHave = key => {
    const lists = available.map(p => new Set(filtered.filter(r => r.process === p && Number.isFinite(r[key])).map(r => r[key])));
    if (!lists.length) return [];
    return [...lists[0]].filter(v => lists.every(set => set.has(v))).sort((a, b) => a - b);
  };
  const vdsOptions = useMemo(() => allSelectedHave('vds'), [filtered, available]);
  const vgsOptions = useMemo(() => allSelectedHave('vgs'), [filtered, available]);
  const vddOptions = useMemo(() => allSelectedHave('vdd'), [filtered, available]);
  useEffect(() => { if (vdsOptions.length && !vdsOptions.some(n => closeEnough(n, vds))) setVds(vdsOptions[0]); }, [vdsOptions, vds]);
  useEffect(() => { if (vgsOptions.length && !vgsOptions.some(n => closeEnough(n, vgs))) setVgs(vgsOptions[Math.floor(vgsOptions.length / 2)]); }, [vgsOptions, vgs]);
  useEffect(() => { if (vddOptions.length && !vddOptions.some(n => closeEnough(n, vdd))) setVdd(vddOptions[0]); }, [vddOptions, vdd]);

  const isInv = device === 'inv';
  const currentMetric = isInv && !INV_METRICS.includes(metric) ? 'ft' : !isInv && !MOS_METRICS.includes(metric) ? 'ft' : metric;
  const activeVds = vdsOptions.find(n => closeEnough(n, vds)) ?? vdsOptions[0];
  const activeVgs = vgsOptions.find(n => closeEnough(n, vgs)) ?? vgsOptions[0];
  const activeVdd = vddOptions.find(n => closeEnough(n, vdd)) ?? vddOptions[0];
  const selectedPoint = useMemo(() => PROCESS.filter(p => available.includes(p)).map(process => filtered.find(r => r.process === process && (isInv ? closeEnough(r.vdd, activeVdd) : closeEnough(r.vds, activeVds) && closeEnough(r.vgs, activeVgs)))).filter(Boolean), [filtered, isInv, activeVds, activeVgs, activeVdd, available]);
  const winner = [...selectedPoint].filter(r => scaled(r, currentMetric) !== null).sort((a, b) => scaled(b, currentMetric) - scaled(a, currentMetric))[0];
  const comparisonValues = selectedPoint.map(r => scaled(r, currentMetric)).filter(v => v !== null);
  const comparisonDiverges = comparisonValues.some(v => v < 0);
  const comparisonMax = Math.max(0, ...comparisonValues);
  const comparisonAbsMax = Math.max(1e-12, ...comparisonValues.map(v => Math.abs(v)));
  const seriesFor = (xKey, fixedKey, fixedValue) => PROCESS.filter(p => available.includes(p)).map(process => ({
    process,
    points: filtered.filter(r => r.process === process && (fixedKey === null || closeEnough(r[fixedKey], fixedValue)) && scaled(r, currentMetric) !== null).sort((a, b) => a[xKey] - b[xKey]).map(r => ({ x: r[xKey], y: scaled(r, currentMetric), record: r })),
  })).filter(s => s.points.length);
  const vgsSeries = useMemo(() => seriesFor('vgs', 'vds', activeVds), [filtered, currentMetric, activeVds, available]);
  const vdsSeries = useMemo(() => seriesFor('vds', 'vgs', activeVgs), [filtered, currentMetric, activeVgs, available]);
  const vddSeries = useMemo(() => seriesFor('vdd', null, null), [filtered, currentMetric, available]);
  const chartClick = (xKey, fixedKey, fixedValue) => event => {
    const match = filtered.find(r => r.process === event.seriesName && closeEnough(r[xKey], event.value[0]) && (fixedKey === null || closeEnough(r[fixedKey], fixedValue)));
    if (match) setDetail(match);
  };
  const pointLabel = isInv ? `VDD = ${fixed(activeVdd)} V` : `VDS = ${fixed(activeVds)} V · VGS = ${fixed(activeVgs)} V`;
  const searchResults = useMemo(() => filtered.filter(r => !search || [r.process, r.device, r.vt, r.vds, r.vgs, r.vdd, r.point].some(v => String(v ?? '').toLowerCase().includes(search.toLowerCase()))), [filtered, search]);
  const pageSize = view === 'data' ? 14 : 6;
  const pages = Math.max(1, Math.ceil(searchResults.length / pageSize));
  const visibleRows = searchResults.slice((Math.min(page, pages) - 1) * pageSize, Math.min(page, pages) * pageSize);
  const metricList = isInv ? INV_METRICS : MOS_METRICS;
  const largestFt = [...filtered].sort((a, b) => (b.metrics.ft || 0) - (a.metrics.ft || 0))[0];

  function downloadCsv() {
    const header = ['工艺', '器件', '阈值类型', 'VDS (V)', 'VGS (V)', 'VDD (V)', ...metricList.map(k => `${k} (${metricConfig(k).unit || '-'})`)];
    const lines = searchResults.map(r => [r.process, r.device, r.vt, r.vds ?? '', r.vgs ?? '', r.vdd ?? '', ...metricList.map(k => scaled(r, k) ?? '')].join(','));
    const blob = new Blob(['\uFEFF', header.join(','), '\n', lines.join('\n')], { type: 'text/csv;charset=utf-8' });
    const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = `ft-lab-${device}-${vt}.csv`;
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }

  if (loadError) return <div className="load-message"><Database size={28} /><h2>数据加载失败</h2><p>{loadError}。请通过 npm run dev 启动页面。</p></div>;
  if (!records) return <div className="load-message"><div className="loading-ring" /><p>正在读取工艺数据…</p></div>;

  return <div className="app-shell">
    <aside className={`sidebar ${mobileMenu ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Activity size={22} strokeWidth={2.3} /></div><div><strong>FT<span>Lab</span></strong><small>PROCESS INTELLIGENCE</small></div></div>
      <div className="sidebar-section-label">工作空间</div>
      <nav className="side-nav">
        <button type="button" className={view === 'overview' ? 'selected' : ''} onClick={() => { setView('overview'); setMobileMenu(false); }}><LayoutDashboard size={18} /> 性能总览 <ArrowRight size={15} className="nav-arrow" /></button>
        <button type="button" className={view === 'curves' ? 'selected' : ''} onClick={() => { setView('curves'); setMobileMenu(false); }}><Activity size={18} /> 曲线分析 <ArrowRight size={15} className="nav-arrow" /></button>
        <button type="button" className={view === 'data' ? 'selected' : ''} onClick={() => { setView('data'); setMobileMenu(false); setPage(1); }}><Database size={18} /> 数据查询 <ArrowRight size={15} className="nav-arrow" /></button>
      </nav>
      <div className="sidebar-section-label process-label">工艺库 <span>4 NODES</span></div>
      <div className="side-processes">{PROCESS.map(p => <div className="side-process" key={p}><i style={{ background: COLORS[p] }} /><span>{p.replace('T', '')} nm</span><small>{p}</small></div>)}</div>
      <div className="sidebar-bottom"><div className="sidebar-bottom-icon"><CircuitBoard size={18} /></div><div><strong>基于原始仿真数据</strong><span>21 份 CSV · 本地分析</span></div></div>
    </aside>
    <div className="main-wrap">
      <header className="topbar"><button className="mobile-toggle" type="button" onClick={() => setMobileMenu(!mobileMenu)}><Menu size={21} /></button><div className="breadcrumb">工作空间 <span>/</span> <strong>{view === 'overview' ? '性能总览' : view === 'curves' ? '曲线分析' : '数据查询'}</strong></div><div className="topbar-right"><span className="live-dot" /> 数据已就绪 <span className="topbar-divider" /> <span className="topbar-tag"><FlaskConical size={14} /> FT 数据库</span></div></header>
      <main className="content">
        <div className="heading-row"><div><div className="eyebrow"><span /> SEMICONDUCTOR / ANALYTICS</div><h1>{view === 'overview' ? '探索每一条性能曲线' : view === 'curves' ? '曲线分析' : '偏置点数据查询'}</h1><p>{view === 'data' ? '查看每一个仿真偏置点及其完整参数，并导出当前筛选结果。' : '跨工艺、跨器件对比 fT 与关键电学参数，快速找到目标工作点。'}</p></div><div className="heading-badge"><Layers3 size={17} /><span>4 个工艺节点</span></div></div>

        <section className="filter-panel"><div className="filter-header"><div><SlidersHorizontal size={17} /><strong>分析条件</strong><span>选择器件与工艺，图表实时更新</span></div><span className="filter-header-id">CONFIG / 01</span></div><div className="filter-grid">
          <div className="filter-group"><label>器件类型</label><div className="pill-row">{['nmos', 'pmos', 'inv'].map(key => <Pill key={key} active={device === key} onClick={() => changeDevice(key)}>{LABELS[key]}</Pill>)}</div></div>
          <div className="filter-group"><label>阈值类型</label><div className="pill-row">{['svt', 'ulvt'].map(key => <Pill key={key} active={vt === key} onClick={() => changeVt(key)}>{LABELS[key]}</Pill>)}</div></div>
          <div className="filter-group filter-process"><label>参与对比的工艺</label><div className="pill-row">{PROCESS.map(p => <Pill key={p} active={processes.includes(p)} onClick={() => toggleProcess(p)} disabled={vt === 'ulvt' && p === 'T65'} color={COLORS[p]}><i className="process-dot" style={{ background: COLORS[p] }} />{p}</Pill>)}</div></div>
        </div>{vt === 'ulvt' && <div className="filter-note">T65 原始数据仅包含 SVT，因此在 ULVT 模式下不可选。</div>}</section>

        {view !== 'data' && <>
          <div className="section-heading"><div><span className="section-kicker">OVERVIEW</span><h2>当前分析概览</h2></div><span className="section-subtle">{LABELS[device]} / {vt.toUpperCase()}</span></div>
          <div className="stats-grid">
            <Stat icon={Layers3} label="已选工艺" value={String(available.length).padStart(2, '0')} foot="参与当前横向对比" accent="#0d9f91" />
            <Stat icon={Database} label="偏置数据点" value={filtered.length.toLocaleString()} foot="当前条件下可查询" accent="#4c78de" />
            <Stat icon={Activity} label="最高 fT" value={largestFt ? `${scaled(largestFt, 'ft').toFixed(1)} GHz` : '—'} foot={largestFt ? `${largestFt.process} · ${LABELS[device]} · ${vt.toUpperCase()}` : '暂无数据'} accent="#9468cc" />
            <Stat icon={BarChart3} label="当前最高数值" value={winner?.process || '—'} foot={winner ? `${metricName(currentMetric)} · ${pointLabel}` : '请选择共同偏置点'} accent="#e2a64a" />
          </div>
        </>}

        {view !== 'data' && <>
          <div className="section-heading chart-section-heading"><div><span className="section-kicker">CURVE ANALYSIS</span><h2>性能曲线</h2></div><div className="chart-metric-select"><label htmlFor="metric-select">观察参数</label><div className="select-wrap"><select id="metric-select" value={currentMetric} onChange={e => setMetric(e.target.value)}>{metricList.map(key => <option value={key} key={key}>{metricName(key)}</option>)}</select><ChevronDown size={15} /></div></div></div>
          {isInv ? <div className="chart-grid single-chart"><div className="chart-card"><div className="chart-card-head"><div><span className="chart-overline">VDD SWEEP</span><h3>{metricName(currentMetric)} vs VDD</h3><p>反相器供电电压扫描 · 各工艺独立曲线</p></div><span className="chart-card-icon"><Activity size={18} /></span></div><Chart option={lineOption(vddSeries, 'VDD', currentMetric)} onPoint={chartClick('vdd', null, null)} /><div className="chart-legend">{vddSeries.map(s => <span key={s.process}><i style={{ background: COLORS[s.process] }} />{s.process}</span>)}</div></div></div> : <div className="chart-grid"><div className="chart-card"><div className="chart-card-head"><div><span className="chart-overline">VGS SWEEP</span><h3>{metricName(currentMetric)} vs VGS</h3><p>固定漏源电压，观察栅压变化</p></div><span className="chart-card-icon"><Activity size={18} /></span></div><div className="bias-row"><span>固定 VDS</span><div className="select-wrap small"><select aria-label="固定 VDS" value={activeVds ?? ''} onChange={e => setVds(Number(e.target.value))}>{vdsOptions.map(v => <option value={v} key={v}>{fixed(v)} V</option>)}</select><ChevronDown size={14} /></div></div><Chart option={lineOption(vgsSeries, 'VGS', currentMetric)} onPoint={chartClick('vgs', 'vds', activeVds)} /><div className="chart-legend">{vgsSeries.map(s => <span key={s.process}><i style={{ background: COLORS[s.process] }} />{s.process}</span>)}</div></div><div className="chart-card"><div className="chart-card-head"><div><span className="chart-overline">VDS SWEEP</span><h3>{metricName(currentMetric)} vs VDS</h3><p>固定栅源电压，观察漏压变化</p></div><span className="chart-card-icon"><Activity size={18} /></span></div><div className="bias-row"><span>固定 VGS</span><div className="select-wrap small"><select aria-label="固定 VGS" value={activeVgs ?? ''} onChange={e => setVgs(Number(e.target.value))}>{vgsOptions.map(v => <option value={v} key={v}>{fixed(v)} V</option>)}</select><ChevronDown size={14} /></div></div><Chart option={lineOption(vdsSeries, 'VDS', currentMetric)} onPoint={chartClick('vds', 'vgs', activeVgs)} /><div className="chart-legend">{vdsSeries.map(s => <span key={s.process}><i style={{ background: COLORS[s.process] }} />{s.process}</span>)}</div></div></div>}
          <div className="compare-card">
            <div className="compare-head"><div><span className="section-kicker">SIDE BY SIDE</span><h2>相同偏置下的工艺对比</h2><p>{pointLabel} · {LABELS[device]} / {vt.toUpperCase()}</p></div><div className="compare-metric">{metricName(currentMetric)} <span>{metricConfig(currentMetric).unit}</span></div></div>
            <div className="compare-body">{selectedPoint.length ? selectedPoint.map(r => {
              const value = scaled(r, currentMetric) || 0;
              const width = comparisonDiverges ? Math.abs(value) / comparisonAbsMax * 50 : value / (comparisonMax || 1) * 100;
              const left = comparisonDiverges && value < 0 ? 50 - width : comparisonDiverges ? 50 : 0;
              return <div className="compare-row" key={r.process}><div className="compare-process"><i style={{ background: COLORS[r.process] }} />{r.process}</div><div className={`compare-track ${comparisonDiverges ? 'diverging' : ''}`}><span style={{ left: `${left}%`, width: `${Math.max(value === 0 ? 0 : 1, width)}%`, background: COLORS[r.process] }} /></div><strong>{formatMetric(r, currentMetric)}</strong></div>;
            }) : <div className="empty-state">当前选择没有共同偏置点。</div>}</div>
            <div className="compare-footer"><span>仅对比原始数据中相同的偏置条件；曲线上的点可点击查看完整参数。</span><button type="button" onClick={() => { setView('data'); setPage(1); }}>查看数据明细 <ArrowRight size={15} /></button></div>
          </div>
        </>}

        {(view === 'data' || view === 'overview') && <section className="table-card"><div className="table-head"><div><span className="section-kicker">DATA EXPLORER</span><h2>偏置点明细</h2><p>每行对应原始 CSV 中的一个仿真偏置点</p></div><div className="table-actions"><div className="search-box"><Search size={16} /><input value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} placeholder="搜索工艺或偏置…" aria-label="搜索数据" /></div><button className="export-button" type="button" onClick={downloadCsv}><ArrowDownToLine size={16} /> 导出 CSV</button></div></div><div className="table-scroll"><table><thead><tr><th>工艺</th><th>器件</th><th>VT</th><th>VDS (V)</th><th>VGS (V)</th><th>VDD (V)</th><th>fT (GHz)</th><th>{isInv ? 'Ids (mA)' : 'gm (mS)'}</th><th></th></tr></thead><tbody>{visibleRows.map(r => <tr key={`${r.process}-${r.device}-${r.vt}-${r.point}`} onClick={() => setDetail(r)}><td><span className="table-process"><i style={{ background: COLORS[r.process] }} />{r.process}</span></td><td>{LABELS[r.device]}</td><td>{r.vt.toUpperCase()}</td><td>{r.vds === undefined ? '—' : fixed(r.vds)}</td><td>{r.vgs === undefined ? '—' : fixed(r.vgs)}</td><td>{r.vdd === undefined ? '—' : fixed(r.vdd)}</td><td className="table-emphasis">{scaled(r, 'ft')?.toFixed(2) ?? '—'}</td><td>{scaled(r, isInv ? 'ids' : 'gm')?.toFixed(3) ?? '—'}</td><td><ArrowRight size={15} /></td></tr>)}</tbody></table>{!visibleRows.length && <div className="empty-state">没有匹配的数据，请调整筛选条件。</div>}</div><div className="table-footer"><span>共 {searchResults.length} 个偏置点 · 第 {Math.min(page, pages)} / {pages} 页</span><div><button type="button" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}>上一页</button><button type="button" onClick={() => setPage(p => Math.min(pages, p + 1))} disabled={page >= pages}>下一页</button></div></div></section>}
        <footer className="page-footer">FT Lab <span>·</span> 数据源：T12 / T22 / T28 / T65 原始仿真 CSV <span>·</span> 数值按 SI 单位转换展示</footer>
      </main>
    </div>
    {detail && <div className="modal-backdrop" onMouseDown={() => setDetail(null)}><div className="detail-modal" role="dialog" aria-modal="true" aria-label="偏置点详情" onMouseDown={e => e.stopPropagation()}><div className="modal-header"><div><span className="section-kicker">BIAS POINT DETAIL</span><h2>{detail.process} · {LABELS[detail.device]} · {detail.vt.toUpperCase()}</h2><p>{detail.device === 'inv' ? `VDD ${fixed(detail.vdd)} V` : `VDS ${fixed(detail.vds)} V · VGS ${fixed(detail.vgs)} V`} · Point #{detail.point}</p></div><button type="button" onClick={() => setDetail(null)} aria-label="关闭详情"><X size={20} /></button></div><div className="detail-grid">{Object.keys(detail.metrics).map(key => <div className="detail-item" key={key}><span>{metricName(key)}</span><strong>{formatMetric(detail, key)}</strong><small>{key}</small></div>)}</div><div className="modal-foot">数值取自原始 CSV；频率、电容、电流等已转换为便于阅读的单位。</div></div></div>}
  </div>;
}

createRoot(document.getElementById('root')).render(<App />);
