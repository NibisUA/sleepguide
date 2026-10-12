// Build-time copies: the browser never requests a third-party OCR service or CDN.
import { mkdir, readdir, copyFile, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
const root = resolve(import.meta.dirname, "..");
const dest = resolve(root, "public/ocr");
await mkdir(resolve(dest, "core"), { recursive: true });
await mkdir(resolve(dest, "lang"), { recursive: true });
await copyFile(resolve(root, "node_modules/tesseract.js/dist/worker.min.js"), resolve(dest, "worker.min.js"));
for (const name of await readdir(resolve(root, "node_modules/tesseract.js-core"))) {
  if (/\.wasm(?:\.js)?$/.test(name)) await copyFile(resolve(root, "node_modules/tesseract.js-core", name), resolve(dest, "core", name));
}
for (const lang of ["eng", "ukr"]) await copyFile(
  resolve(root, `node_modules/@tesseract.js-data/${lang}/4.0.0_best_int/${lang}.traineddata.gz`), resolve(dest, "lang", `${lang}.traineddata.gz`));
await writeFile(resolve(dest, "LICENSE-Tesseract.txt"), await readFile(resolve(root, "node_modules/tesseract.js-core/LICENSE")));
console.log("Prepared self-hosted OCR worker, WASM and English/Ukrainian models.");
