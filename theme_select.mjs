// theme_select.mjs - 读取配置/写入配置，充当 wenyan_render 的主题选择器
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const CONFIG_FILE = resolve(__dirname, ".theme_selected.json");

/** 读取当前选中的主题 */
export function getSelectedTheme() {
  if (!existsSync(CONFIG_FILE)) return "pie"; // 默认
  try {
    const cfg = JSON.parse(readFileSync(CONFIG_FILE, "utf-8"));
    return cfg.theme || "pie";
  } catch {
    return "pie";
  }
}

/** 写入选中的主题 */
export function setSelectedTheme(theme) {
  writeFileSync(CONFIG_FILE, JSON.stringify({ theme, updated: new Date().toISOString() }, null, 2), "utf-8");
  console.log("Theme set to: " + theme);
}

// 命令行用法: node theme_select.mjs get|set <theme>
const cmd = process.argv[2];
const themeArg = process.argv[3];
if (cmd === "get") {
  console.log(getSelectedTheme());
} else if (cmd === "set" && themeArg) {
  setSelectedTheme(themeArg);
}
