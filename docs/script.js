const HOLD_COLORS = ["#e83030", "#2070e0", "#18b050", "#f07020", "#8030c0", "#e0a800", "#e03080"];

const STATUS_LABELS = {
  found:     { text: "体験会情報あり", cls: "badge-found" },
  not_found: { text: "記載なし",       cls: "badge-none" },
  error:     { text: "取得エラー",     cls: "badge-error" },
  pending:   { text: "未スキャン",     cls: "badge-pending" },
};

function formatJST(isoStr) {
  if (!isoStr) return "---";
  const d = new Date(isoStr);
  return d.toLocaleString("ja-JP", {
    timeZone: "Asia/Tokyo",
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

function makeBadge(gym) {
  const span = document.createElement("span");
  span.className = "status-badge";
  if (gym.instagram_primary && gym.status !== "found") {
    span.textContent = "Instagram確認";
    span.classList.add("badge-instagram");
  } else {
    const info = STATUS_LABELS[gym.status] || { text: gym.status, cls: "badge-none" };
    span.textContent = info.text;
    span.classList.add(info.cls);
  }
  return span;
}

function makeSnippetEl(s) {
  const snip = document.createElement("div");
  snip.className = "snippet";

  // 記事タイトル（リンク）
  const titleEl = document.createElement("a");
  titleEl.className = "snippet-title";
  titleEl.href = s.source_url;
  titleEl.target = "_blank";
  titleEl.rel = "noopener";
  titleEl.textContent = s.title + " →";
  snip.appendChild(titleEl);

  // 日時（あれば）
  if (s.date) {
    const dateEl = document.createElement("div");
    dateEl.className = "snippet-date";
    dateEl.textContent = "📅 " + s.date;
    snip.appendChild(dateEl);
  }

  return snip;
}

function makeCard(gym, idx) {
  const card = document.createElement("div");
  card.className = "gym-card";
  card.dataset.gymId = gym.id;
  card.style.setProperty("--card-accent", HOLD_COLORS[idx % HOLD_COLORS.length]);

  if (gym.status === "found") {
    card.dataset.filter = "found";
  } else if (gym.instagram_primary) {
    card.dataset.filter = "instagram";
  } else {
    card.dataset.filter = "none";
  }

  // カード上部（名前 + バッジ）
  const top = document.createElement("div");
  top.className = "card-top";

  const nameEl = document.createElement("div");
  nameEl.className = "gym-name";
  nameEl.appendChild(document.createTextNode(gym.name));
  if (gym.station) {
    const stEl = document.createElement("span");
    stEl.className = "gym-station";
    stEl.textContent = "（" + gym.station + "）";
    nameEl.appendChild(stEl);
  }
  top.appendChild(nameEl);
  top.appendChild(makeBadge(gym));
  card.appendChild(top);

  // ノート
  if (gym.note) {
    const note = document.createElement("div");
    note.className = "gym-note";
    note.textContent = "ℹ️ " + gym.note;
    card.appendChild(note);
  }

  // 記事カード一覧
  if (gym.snippets && gym.snippets.length > 0) {
    const snippetsEl = document.createElement("div");
    snippetsEl.className = "snippets";
    gym.snippets.forEach(s => snippetsEl.appendChild(makeSnippetEl(s)));
    card.appendChild(snippetsEl);
  }

  // カード下部（リンク + 確認日時）
  const footer = document.createElement("div");
  footer.className = "card-footer";

  const links = document.createElement("div");
  links.className = "card-links";

  const siteLink = document.createElement("a");
  siteLink.className = "card-link site-link";
  siteLink.href = gym.url;
  siteLink.target = "_blank";
  siteLink.rel = "noopener";
  siteLink.textContent = "公式サイト →";
  links.appendChild(siteLink);

  if (gym.instagram_handle) {
    const instaLink = document.createElement("a");
    instaLink.className = "card-link insta-link";
    instaLink.href = "https://www.instagram.com/" + gym.instagram_handle + "/";
    instaLink.target = "_blank";
    instaLink.rel = "noopener";
    instaLink.textContent = "Instagram →";
    links.appendChild(instaLink);
  }

  footer.appendChild(links);

  const checkedEl = document.createElement("span");
  checkedEl.className = "card-checked";
  checkedEl.textContent = gym.last_checked ? "確認 " + formatJST(gym.last_checked) : "未スキャン";
  footer.appendChild(checkedEl);

  card.appendChild(footer);
  return card;
}

function applyFilter(filter) {
  document.querySelectorAll(".gym-card").forEach(card => {
    if (filter === "all" || card.dataset.filter === filter) {
      card.classList.remove("filter-hidden");
    } else {
      card.classList.add("filter-hidden");
    }
  });
  document.querySelectorAll(".filter-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.filter === filter);
  });
}

async function init() {
  try {
    const res = await fetch("data.json");
    if (!res.ok) throw new Error("HTTP " + res.status);
    const data = await res.json();

    document.getElementById("last-updated").textContent = formatJST(data.last_updated);

    const grid = document.getElementById("gym-grid");
    data.gyms.forEach((gym, idx) => grid.appendChild(makeCard(gym, idx)));

    document.getElementById("loading-state").classList.add("hidden");
    grid.classList.remove("hidden");

    document.getElementById("filter-bar").addEventListener("click", e => {
      const btn = e.target.closest(".filter-btn");
      if (btn) applyFilter(btn.dataset.filter);
    });

  } catch (err) {
    document.getElementById("loading-state").classList.add("hidden");
    document.getElementById("error-state").classList.remove("hidden");
    console.error("Failed to load data.json:", err);
  }
}

init();
