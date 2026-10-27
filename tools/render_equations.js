"use strict";

const fs = require("fs");
const path = require("path");
const sharp = require("sharp");
const { mathjax } = require("mathjax-full/js/mathjax.js");
const { TeX } = require("mathjax-full/js/input/tex.js");
const { SVG } = require("mathjax-full/js/output/svg.js");
const { liteAdaptor } = require("mathjax-full/js/adaptors/liteAdaptor.js");
const { RegisterHTMLHandler } = require("mathjax-full/js/handlers/html.js");
const { AllPackages } = require("mathjax-full/js/input/tex/AllPackages.js");

if (process.argv.length !== 3) {
  throw new Error("Usage: render_equations.js OUTPUT_DIRECTORY");
}

const outDir = process.argv[2];
fs.mkdirSync(outDir, { recursive: true });

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const tex = new TeX({ packages: AllPackages });
const svgOut = new SVG({ fontCache: "local" });
const doc = mathjax.document("", { InputJax: tex, OutputJax: svgOut });

async function render(latex, filename) {
  const html = adaptor.outerHTML(doc.convert(latex, { display: false }));
  const start = html.indexOf("<svg");
  const end = html.indexOf("</svg>");
  let svg = html.slice(start, end + 6);
  if (!svg.includes('xmlns="http://www.w3.org/2000/svg"')) {
    svg = svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ');
  }
  svg = svg.replace(/currentColor/g, "#000000");
  const svgPath = path.join(outDir, `${filename}.svg`);
  fs.writeFileSync(svgPath, svg);
  await sharp(Buffer.from(svg), { density: 600 }).png().toFile(path.join(outDir, `${filename}.png`));
}

Promise.all([
  render(String.raw`E_{\mathrm{kWh}}=\frac{P_{\mathrm{start,W}}\times \Delta t_{\mathrm{s}}}{3{,}600{,}000}`, "interval_energy"),
  render(String.raw`0<\Delta t_{\mathrm{s}}\leq 16\ \mathrm{s}`, "interval_condition"),
]).catch((error) => {
  console.error(error);
  process.exit(1);
});
