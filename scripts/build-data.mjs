import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const processes = ['T12', 'T22', 'T28', 'T65'];
const output = [];

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '"') {
      if (quoted && text[i + 1] === '"') { field += '"'; i++; }
      else quoted = !quoted;
    } else if (ch === ',' && !quoted) {
      row.push(field); field = '';
    } else if ((ch === '\n' || ch === '\r') && !quoted) {
      if (ch === '\r' && text[i + 1] === '\n') i++;
      row.push(field);
      if (row.some(Boolean)) rows.push(row);
      row = []; field = '';
    } else {
      field += ch;
    }
  }
  row.push(field);
  if (row.some(Boolean)) rows.push(row);
  return rows;
}

function volts(raw) {
  const match = /^([+-]?(?:\d+\.?\d*|\.\d+))(m?)$/.exec(raw);
  if (!match) throw new Error(`Unknown voltage: ${raw}`);
  return Number((Number(match[1]) * (match[2] ? 0.001 : 1)).toFixed(6));
}

for (const process of processes) {
  const directory = path.join(root, process);
  for (const filename of fs.readdirSync(directory).filter(name => name.endsWith('.csv')).sort()) {
    const [device, vt] = filename.replace('.csv', '').split('_');
    const rows = parseCsv(fs.readFileSync(path.join(directory, filename), 'utf8').replace(/^\uFEFF/, ''));
    const points = new Map();
    let bias = {};
    for (const row of rows.slice(1)) {
      if (row[0].startsWith('Parameters:')) {
        bias = {};
        for (const [, key, raw] of row[0].matchAll(/(VDS|VGS|VDD)=([\d.]+m?)/g)) {
          bias[key.toLowerCase()] = volts(raw);
        }
        continue;
      }
      const point = Number(row[0]);
      if (!Number.isInteger(point) || !row[2]) continue;
      if (!points.has(point)) {
        points.set(point, { process, device, vt, point, ...bias, metrics: {} });
      }
      const value = Number(row[3]);
      if (Number.isFinite(value) && row[3] !== '') points.get(point).metrics[row[2]] = value;
    }
    for (const item of points.values()) {
      if (device === 'inv' ? !Number.isFinite(item.vdd) : !Number.isFinite(item.vds) || !Number.isFinite(item.vgs)) {
        throw new Error(`Missing bias in ${process}/${filename} point ${item.point}`);
      }
      output.push(item);
    }
  }
}

const dest = path.join(root, 'public', 'process-data.json');
fs.mkdirSync(path.dirname(dest), { recursive: true });
fs.writeFileSync(dest, JSON.stringify({ records: output }));
console.log(`Generated ${output.length} bias points from 21 CSV files → ${path.relative(root, dest)}`);
