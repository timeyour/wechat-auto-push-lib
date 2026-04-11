// wenyan_render.mjs - 调用 wenyan 排版，输出到文件
// 用法: node wenyan_render.mjs <md-file> [theme] <out-html>
//       不传 theme 时自动读取 .theme_selected.json
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const CONFIG_FILE = resolve(__dirname, ".theme_selected.json");

const mdFile = process.argv[2];
let theme = process.argv[3];
const outFile = process.argv[4];

if (!mdFile || !outFile) {
  console.error("Usage: node wenyan_render.mjs <md-file> [theme] <out-html>");
  console.error("  theme 可省略，自动读取 .theme_selected.json（由 theme_gallery.html 设置）");
  process.exit(1);
}

// 无 theme 参数 → 读配置文件
if (!theme) {
  theme = (() => {
    if (!existsSync(CONFIG_FILE)) return "pie";
    try {
      const cfg = JSON.parse(readFileSync(CONFIG_FILE, "utf-8"));
      return cfg.theme || "pie";
    } catch { return "pie"; }
  })();
  console.log("Auto theme: " + theme);
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

  const detail = lastError && lastError.message ? `\n${lastError.message}` : "";
  throw new Error(
    "未找到可用的 wenyan-cli。请先运行 `npm install -g @wenyan-md/cli`，或在当前仓库执行 `npm install @wenyan-md/cli`。" +
      detail,
  );
}

try {
  const html = runWenyan(["render", "-f", mdFile, "-t", theme, "--no-footnote"]);

  // 包装成完整 HTML 页面
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
  console.log("OK: " + outFile + " (" + (fullHtml.length / 1024).toFixed(1) + "KB, theme=" + theme + ")");

  // 同时输出纯 HTML 内容（不含外层），供 direct_publish 使用
  const contentOnly = outFile.replace(/\.html$/i, "_content.html");
  writeFileSync(contentOnly, html, "utf-8");
  console.log("Content: " + contentOnly);
} catch (e) {
  console.error("FAIL: " + e.message);
  process.exit(1);
}
