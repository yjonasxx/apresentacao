import puppeteer from 'puppeteer-core';
import { PDFDocument } from 'pdf-lib';
import { writeFileSync, unlinkSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const htmlPath = resolve(__dirname, 'apresentacao.html');
const pdfPath = resolve(__dirname, 'apresentacao_novo.pdf');
const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const TOTAL = 10;

const browser = await puppeteer.launch({
  executablePath: chromePath,
  headless: true,
  args: ['--no-sandbox'],
});

const page = await browser.newPage();
await page.setViewport({ width: 1920, height: 1080 });
await page.goto('file://' + htmlPath, { waitUntil: 'networkidle0' });

const screenshots = [];

for (let i = 1; i <= TOTAL; i++) {
  await page.evaluate((n) => {
    document.querySelectorAll('.slide').forEach((s) => {
      s.classList.remove('active');
      s.style.opacity = '0';
      s.style.visibility = 'hidden';
    });
    const el = document.querySelector(`[data-slide="${n}"]`);
    if (el) {
      el.classList.add('active');
      el.style.opacity = '1';
      el.style.visibility = 'visible';
      el.style.transform = 'translateX(0)';
      const anims = el.querySelectorAll('.animate');
      anims.forEach((a) => a.classList.add('visible'));
    }
  }, i);

  await new Promise((r) => setTimeout(r, 1000));

  const buf = await page.screenshot({ type: 'png', fullPage: false });
  screenshots.push(buf);
  console.log(`Slide ${i} capturado`);
}

await browser.close();

const pdfDoc = await PDFDocument.create();

for (const buf of screenshots) {
  const img = await pdfDoc.embedPng(buf);
  const page = pdfDoc.addPage([1920, 1080]);
  page.drawImage(img, { x: 0, y: 0, width: 1920, height: 1080 });
}

writeFileSync(pdfPath, await pdfDoc.save());
console.log('PDF gerado: ' + pdfPath);
