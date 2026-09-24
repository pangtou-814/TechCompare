# FT Lab 工艺性能分析

基于 `T12`、`T22`、`T28`、`T65` 目录中的 21 份原始 CSV，提供一个本地前端页面。可按器件、阈值类型和工艺筛选，查看 fT 等参数随 VGS、VDS 或 VDD 变化的曲线，并在相同偏置条件下横向对比工艺。

## 启动

需要 Node.js 20.19+ 或 22.12+。

```bash
npm install
npm run dev
```

然后打开终端显示的本地地址，通常是 <http://localhost:5173/>。

## 数据与构建

- 原始 CSV 是数据源；`scripts/build-data.mjs` 将其整理为 `public/process-data.json`。
- `npm run dev` 和 `npm run build` 都会先重新生成数据。因此修改或新增 CSV 后，重新运行即可更新页面。
- `npm run build` 生成可部署的静态站点，输出在 `dist/`。
- 数据查询页可查看偏置点的全部参数，并导出当前筛选结果。页面中的频率、电流、电容等数值已转换为 GHz、mA、fF 等单位。
- T65 原始数据只有 SVT，因此 ULVT 模式下不会显示 T65。

工艺对比使用各工艺共同存在的偏置点，不对缺失点插值。旧版 Streamlit 文件已移出此项目目录并单独备份。

## 在线访问

项目在 GitHub `master` 分支更新后，会自动构建并发布到 <https://pangtou-814.github.io/TechCompare/>。该地址和页面数据公开可访问。
