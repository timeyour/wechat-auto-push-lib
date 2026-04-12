// wenyan_render.mjs - 调用 wenyan 排版，输出到文件
// 用法: node wenyan_render.mjs <md-file> [theme] <out-html>
//       不传 theme 时自动读取 .theme_selected.json
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const CONFIG_FILE = resolve(__dirname, ".theme_selected.json");
const THEME_LIBRARY_FILE = resolve(__dirname, "data", "theme_library.json");
const DEFAULT_THEME = "pie";
const BUILTIN_THEMES = new Set([
  "default",
  "orangeheart",
  "rainbow",
  "lapis",
  "pie",
  "maize",
  "purple",
  "phycat",
]);

const mdFile = process.argv[2];
let theme = process.argv[3];
const outFile = process.argv[4];

if (!mdFile || !outFile) {
  console.error("Usage: node wenyan_render.mjs <md-file> [theme] <out-html>");
  console.error("  theme 可省略，自动读取 .theme_selected.json");
  process.exit(1);
}

if (!theme) {
  theme = (() => {
    if (!existsSync(CONFIG_FILE)) return DEFAULT_THEME;
    try {
      const cfg = JSON.parse(readFileSync(CONFIG_FILE, "utf-8"));
      return cfg.theme || DEFAULT_THEME;
    } catch {
      return DEFAULT_THEME;
    }
  })();
}

function loadCustomThemes() {
  if (!existsSync(THEME_LIBRARY_FILE)) return [];
  try {
    const payload = JSON.parse(readFileSync(THEME_LIBRARY_FILE, "utf-8"));
    return Array.isArray(payload) ? payload : payload.custom_themes || [];
  } catch {
    return [];
  }
}

function resolveThemeSpec(themeId) {
  if (BUILTIN_THEMES.has(themeId)) {
    return { id: themeId, base_theme: themeId, style_profile: {} };
  }

  const custom = loadCustomThemes().find((item) => item.id === themeId);
  if (custom) return custom;
  return { id: DEFAULT_THEME, base_theme: DEFAULT_THEME, style_profile: {} };
}

function runWenyan(args) {
  const localCmd = resolve(
    __dirname,
    "node_modules",
    ".bin",
    process.platform === "win32" ? "wenyan.cmd" : "wenyan",
  );
  const candidates = [
    existsSync(localCmd) ? { cmd: localCmd, args } : null,
    { cmd: process.platform === "win32" ? "wenyan.cmd" : "wenyan", args },
    {
      cmd: process.platform === "win32" ? "npx.cmd" : "npx",
      args: ["@wenyan-md/cli", ...args],
    },
  ].filter(Boolean);

  let lastError;
  for (const candidate of candidates) {
    try {
      return execFileSync(candidate.cmd, candidate.args, {
        encoding: "utf-8",
        timeout: 60000,
        windowsHide: true,
      });
    } catch (error) {
      lastError = error;
    }
  }

  const detail = lastError?.message ? `\n${lastError.message}` : "";
  throw new Error(
    "未找到可用的 wenyan-cli。请先运行 `npm install -g @wenyan-md/cli`，或在当前仓库执行 `npm install @wenyan-md/cli`。" +
      detail,
  );
}

function appendStyle(attrs = "", styleText) {
  const styleMatch = attrs.match(/\sstyle=(["'])(.*?)\1/i);
  if (styleMatch) {
    const existing = styleMatch[2].trim();
    const merged = `${existing}${existing.endsWith(";") ? "" : ";"} ${styleText}`.trim();
    return attrs.replace(styleMatch[0], ` style="${merged}"`);
  }
  return `${attrs} style="${styleText}"`;
}

function injectStyleIntoTag(html, tag, styleText) {
  if (!styleText) return html;
  const regex = new RegExp(`<${tag}(\\b[^>]*)>`, "gi");
  return html.replace(regex, (match, attrs = "") => `<${tag}${appendStyle(attrs, styleText)}>`);
}

function applyStyleProfile(html, styleProfile = {}) {
  const {
    title_color = "",
    body_color = "",
    accent_color = "",
    quote_background = "",
    heading_weight = "",
  } = styleProfile;

  let nextHtml = html;
  const headingStyles = [];
  if (title_color) headingStyles.push(`color: ${title_color} !important;`);
  if (heading_weight) headingStyles.push(`font-weight: ${heading_weight} !important;`);
  for (const tag of ["h1", "h2", "h3", "h4", "h5", "h6"]) {
    nextHtml = injectStyleIntoTag(nextHtml, tag, headingStyles.join(" "));
  }

  const bodyStyle = body_color ? `color: ${body_color} !important;` : "";
  for (const tag of ["p", "li"]) {
    nextHtml = injectStyleIntoTag(nextHtml, tag, bodyStyle);
  }

  const accentStyle = accent_color ? `color: ${accent_color} !important;` : "";
  for (const tag of ["strong", "a"]) {
    nextHtml = injectStyleIntoTag(nextHtml, tag, accentStyle);
  }

  const quoteStyles = [];
  if (quote_background) quoteStyles.push(`background: ${quote_background} !important;`);
  if (accent_color) quoteStyles.push(`border-left: 4px solid ${accent_color} !important;`);
  if (body_color) quoteStyles.push(`color: ${body_color} !important;`);
  if (quoteStyles.length) {
    quoteStyles.push("padding: 14px 18px !important;");
    quoteStyles.push("border-radius: 16px !important;");
  }
  nextHtml = injectStyleIntoTag(nextHtml, "blockquote", quoteStyles.join(" "));

  return nextHtml;
}

try {
  const themeSpec = resolveThemeSpec(theme);
  const baseTheme = themeSpec.base_theme || DEFAULT_THEME;
  let html = runWenyan(["render", "-f", mdFile, "-t", baseTheme, "--no-footnote"]);
  html = applyStyleProfile(html, themeSpec.style_profile || {});

  const fullHtml = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Preview — ${theme}</title>
<style>body{max-width:580px;margin:20px auto;background:#fff;padding:20px;}</style>
</head>
<body>
${html}
</body>
</html>`;

  writeFileSync(outFile, fullHtml, "utf-8");
  console.log(
    `OK: ${outFile} (${(fullHtml.length / 1024).toFixed(1)}KB, theme=${theme}, base=${baseTheme})`,
  );

  const contentOnly = outFile.replace(/\.html$/i, "_content.html");
  writeFileSync(contentOnly, html, "utf-8");
  console.log("Content: " + contentOnly);
} catch (error) {
  console.error("FAIL: " + error.message);
  process.exit(1);
}
