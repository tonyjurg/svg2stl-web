const guides = {
  usage: { file: "USAGE.md", label: "Using the converter" },
  deployment: { file: "DEPLOYMENT.md", label: "Deployment" },
  authentication: { file: "AUTHENTICATION.md", label: "DSM authentication" },
  troubleshooting: { file: "TROUBLESHOOTING.md", label: "Troubleshooting" },
  api: { file: "API.md", label: "HTTP API" },
  development: { file: "DEVELOPMENT.md", label: "Development" },
  security: { file: "SECURITY.md", label: "Security policy" },
  licenses: { file: "LICENSES.md", label: "Licenses and components" },
};

const article = document.querySelector("#manual-article");
const errorPanel = document.querySelector("#manual-error");
const breadcrumb = document.querySelector("#manual-breadcrumb");
const sourceLink = document.querySelector("#source-link");

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function slugify(value) {
  return value
    .toLowerCase()
    .replace(/<[^>]+>/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function rewriteGuideLink(target) {
  if (target.startsWith("../examples/")) {
    return `https://github.com/tonyjurg/svg2stl-web/blob/main/${target.slice(3)}`;
  }
  const match = target.match(/^(?:docs\/)?([A-Z]+)\.md(#[a-z0-9-]+)?$/i);
  if (!match) return target;
  const key = match[1].toLowerCase();
  return guides[key] ? `manual.html?guide=${key}${match[2] || ""}` : target;
}

function inlineMarkdown(value) {
  let output = escapeHtml(value);
  const codeSpans = [];
  output = output.replace(/`([^`]+)`/g, (_, code) => {
    codeSpans.push(`<code>${code}</code>`);
    return `@@CODE${codeSpans.length - 1}@@`;
  });
  output = output.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, target) => {
    const href = rewriteGuideLink(target);
    const external = /^https?:\/\//.test(href) ? ' rel="noreferrer"' : "";
    return `<a href="${href}"${external}>${label}</a>`;
  });
  output = output.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  output = output.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  output = output.replace(/@@CODE(\d+)@@/g, (_, index) => codeSpans[Number(index)]);
  return output;
}

function isTableDivider(line) {
  return /^\|?\s*:?-{3,}/.test(line) && line.includes("|");
}

function tableCells(line) {
  return line.replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim());
}

function renderMarkdown(markdown) {
  const lines = markdown.replaceAll("\r\n", "\n").split("\n");
  const html = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) { index += 1; continue; }

    if (line.startsWith("```")) {
      const language = line.slice(3).trim();
      const code = [];
      index += 1;
      while (index < lines.length && !lines[index].startsWith("```")) {
        code.push(lines[index]);
        index += 1;
      }
      index += 1;
      html.push(`<pre data-language="${escapeHtml(language || "text")}"><code>${escapeHtml(code.join("\n"))}</code></pre>`);
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      const level = heading[1].length;
      const content = inlineMarkdown(heading[2]);
      html.push(`<h${level} id="${slugify(content)}">${content}</h${level}>`);
      index += 1;
      continue;
    }

    if (line.includes("|") && index + 1 < lines.length && isTableDivider(lines[index + 1])) {
      const headers = tableCells(line);
      index += 2;
      const rows = [];
      while (index < lines.length && lines[index].includes("|") && lines[index].trim()) {
        rows.push(tableCells(lines[index]));
        index += 1;
      }
      html.push(`<div class="table-scroll"><table><thead><tr>${headers.map((cell) => `<th>${inlineMarkdown(cell)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${inlineMarkdown(cell)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
      continue;
    }

    const unordered = line.match(/^\s*[-*]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+\.\s+(.+)$/);
    if (unordered || ordered) {
      const listTag = unordered ? "ul" : "ol";
      const items = [];
      const pattern = unordered ? /^\s*[-*]\s+(.+)$/ : /^\s*\d+\.\s+(.+)$/;
      while (index < lines.length) {
        const item = lines[index].match(pattern);
        if (!item) break;
        items.push(`<li>${inlineMarkdown(item[1])}</li>`);
        index += 1;
      }
      html.push(`<${listTag}>${items.join("")}</${listTag}>`);
      continue;
    }

    if (/^---+$/.test(line.trim())) {
      html.push("<hr>");
      index += 1;
      continue;
    }

    const paragraph = [line.trim()];
    index += 1;
    while (index < lines.length && lines[index].trim()) {
      const next = lines[index];
      if (/^(#{1,4})\s+/.test(next) || next.startsWith("```") || /^\s*[-*]\s+/.test(next) || /^\s*\d+\.\s+/.test(next)) break;
      if (next.includes("|") && index + 1 < lines.length && isTableDivider(lines[index + 1])) break;
      paragraph.push(next.trim());
      index += 1;
    }
    html.push(`<p>${inlineMarkdown(paragraph.join(" "))}</p>`);
  }

  return html.join("\n");
}

async function loadGuide() {
  const requested = new URLSearchParams(window.location.search).get("guide") || "usage";
  const guideKey = guides[requested] ? requested : "usage";
  const guide = guides[guideKey];
  document.querySelectorAll("#guide-nav a").forEach((link) => {
    link.classList.toggle("is-active", link.dataset.guide === guideKey);
  });
  breadcrumb.textContent = guide.label;
  sourceLink.href = guide.file;
  document.title = `${guide.label} | SVG to STL`;

  try {
    const response = await fetch(guide.file);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    article.innerHTML = renderMarkdown(await response.text());
    errorPanel.hidden = true;
    if (window.location.hash) {
      requestAnimationFrame(() => document.querySelector(window.location.hash)?.scrollIntoView());
    }
  } catch {
    article.hidden = true;
    errorPanel.hidden = false;
  }
}

loadGuide();
