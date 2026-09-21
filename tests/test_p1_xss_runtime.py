from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIGMA_JS = ROOT / "static" / "assets" / "sigma.js"


def test_sigma_escape_and_css_guards_against_xss_payloads():
    payloads = [
        "<script>alert(1)</script>",
        '<img src=x onerror=alert(1)>',
        '<svg onload=alert(1)>',
        '" onmouseover="alert(1)',
        "' onfocus='alert(1)",
        "&lt;script&gt;alert(1)&lt;/script&gt;",
        "javascript:alert(1)",
    ]
    script = r"""
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync(process.argv[1], 'utf8') + '\nglobalThis.__Sigma = Sigma;';
function escapeHtmlLocal(v) {
  return String(v)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
function mockElement() {
  return {
    textContent: '',
    get innerHTML() { return this._html ?? escapeHtmlLocal(this.textContent); },
    set innerHTML(v) { this._html = String(v); },
  };
}
const ctx = {
  document: { createElement: () => mockElement() },
  sessionStorage: { setItem() {}, removeItem() {}, getItem() { return null; } },
  window: {}, navigator: { onLine: true }, location: {},
  fetch() { throw new Error('network disabled in unit test'); },
  URLSearchParams, FormData: class {}, console,
};
vm.createContext(ctx);
vm.runInContext(src, ctx);
const S = ctx.__Sigma;
const payloads = JSON.parse(process.argv[2]);
for (const p of payloads) {
  const out = S.escapeHtml(p);
  if (/<(?:script|img|svg)\b|<\/?[a-z][^>]*>/i.test(out)) {
    throw new Error(`raw HTML tag remained for ${p}: ${out}`);
  }
  if (/[<>"']/.test(out)) {
    throw new Error(`raw delimiter remained for ${p}: ${out}`);
  }
}
const safe = ['#abc', '#AABBCCDD'];
for (const c of safe) if (S.safeCssHexColor(c, '#123456') !== c) throw new Error(`valid CSS color rejected: ${c}`);
for (const c of ['red', 'url(javascript:alert(1))', ';color:red', '" onload="alert(1)']) {
  if (S.safeCssHexColor(c, '#123456') !== '#123456') throw new Error(`unsafe CSS color accepted: ${c}`);
}
console.log(`PASS ${payloads.length} payloads + CSS guard`);
"""
    result = subprocess.run(
        ["node", "-e", script, str(SIGMA_JS), json.dumps(payloads)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
