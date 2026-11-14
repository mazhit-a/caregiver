const escapeHtml = (text: string): string =>
  text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/** Opens a plain print view of the note template. Returns false when the browser blocked it. */
export function printNote(template: { title: string; example: string }): boolean {
  const win = window.open("", "_blank");
  if (!win) return false;
  const doc = win.document;
  doc.open();
  doc.write(
    `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${escapeHtml(template.title)}</title>` +
      `<style>@page{size:letter;margin:0.75in}body{font:28px/1.4 Georgia,serif;color:#000;background:#fff}` +
      `h1{font-size:40px;margin:0 0 24px}p{margin:0 0 16px}.box{border:3px solid #000;padding:24px;min-height:240px}` +
      `</style></head><body><h1>${escapeHtml(template.title)}</h1><div class="box"><p>${escapeHtml(template.example)}</p></div></body></html>`,
  );
  doc.close();
  win.focus();
  win.print();
  return true;
}
