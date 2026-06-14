/* Atelier web app — vanilla JS, no build step.
   One screen: add photos + notes, pick sizes, generate, download/send.
   Freemium: a few free packs per device, then a one-time unlock. */

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const I18N = {
  en: {
    tagline: "Inspiration in. Sewer-ready tech pack out.",
    s1_photos: "Inspiration photos", s1_notes: "Design notes",
    s1_garment: "Garment type", s1_drop: "Drag photos here or tap to add",
    s2_system: "Size system", s2_base: "Base size", s2_run: "Size run",
    more: "More options",
    gen_title: "Designing your tech pack…",
    gen_msg: "Claude is reading your references and drafting the spec. This takes ~1–2 min.",
    gen_pay: "Taking you to secure checkout…",
    dl_pdf: "Download PDF", dl_csv: "POM .csv",
    r_pom: "Points of measure (base)", r_bom: "Bill of materials",
    r_send: "Send to your sewer", r_sendbtn: "Email tech pack",
    r_again: "Make another", r_delete: "Delete my data",
    err_title: "Something went wrong", err_retry: "Try again",
    f_privacy: "Privacy", f_terms: "Terms",
    consent: "I have the right to use these photos and consent to them being sent to Anthropic (Claude) to generate my tech pack. Photos are auto-deleted after {days} days.",
    generate: "Generate tech pack →",
    generate_free: "Generate — {n} free left →",
    generate_last: "Generate — last free one →",
    unlock: "Unlock unlimited — {price} →",
    badge_unlimited: "✓ Unlimited", badge_free: "{n} free packs left",
    badge_owner: "✓ Owner — unlimited", badge_today: "{n} left today",
    owner_on: "This device now has unlimited free access. ✓",
    rate_limited: "Daily limit reached. Please come back tomorrow.",
    droplimits: "Up to {n} images, {mb} MB each. JPG / PNG / WebP.",
    need_consent: "Please tick the consent box to continue.",
    need_input: "Add at least one photo or some design notes.",
    need_size: "Pick at least one size.",
    footer: "Atelier — first-draft tech packs from inspiration. A human + the sewer's sample stay in the loop.",
    email_sent: "Sent to {to} ✓", email_fail: "Could not send: {err}",
    deleted: "Your data was deleted.",
  },
  bg: {
    tagline: "Вдъхновение → готов за шивача техпакет.",
    s1_photos: "Снимки за вдъхновение", s1_notes: "Бележки по дизайна",
    s1_garment: "Вид облекло", s1_drop: "Пуснете снимки тук или докоснете",
    s2_system: "Размерна система", s2_base: "Базов размер", s2_run: "Размерен диапазон",
    more: "Още опции",
    gen_title: "Създаваме вашия техпакет…",
    gen_msg: "Claude разчита референциите и изготвя спецификацията. Отнема ~1–2 мин.",
    gen_pay: "Към сигурно плащане…",
    dl_pdf: "Изтегли PDF", dl_csv: "POM .csv",
    r_pom: "Точки на измерване (базови)", r_bom: "Спецификация на материалите",
    r_send: "Изпрати на шивача", r_sendbtn: "Изпрати техпакета",
    r_again: "Нов техпакет", r_delete: "Изтрий данните ми",
    err_title: "Възникна грешка", err_retry: "Опитай отново",
    f_privacy: "Поверителност", f_terms: "Условия",
    consent: "Имам право да използвам тези снимки и съм съгласен/на да бъдат изпратени до Anthropic (Claude) за генериране на техпакета. Снимките се изтриват автоматично след {days} дни.",
    generate: "Генерирай техпакет →",
    generate_free: "Генерирай — {n} безплатни →",
    generate_last: "Генерирай — последен безплатен →",
    unlock: "Отключи неограничено — {price} →",
    badge_unlimited: "✓ Неограничено", badge_free: "{n} безплатни техпакета",
    badge_owner: "✓ Собственик — неограничено", badge_today: "още {n} днес",
    owner_on: "Това устройство вече има неограничен безплатен достъп. ✓",
    rate_limited: "Достигнат дневен лимит. Моля, върнете се утре.",
    droplimits: "До {n} изображения, по {mb} MB. JPG / PNG / WebP.",
    need_consent: "Моля, отметнете съгласието, за да продължите.",
    need_input: "Добавете поне една снимка или бележки.",
    need_size: "Изберете поне един размер.",
    footer: "Atelier — техпакети-чернова от вдъхновение. Човек + мостра от шивача остават в процеса.",
    email_sent: "Изпратено до {to} ✓", email_fail: "Неуспешно изпращане: {err}",
    deleted: "Данните ви бяха изтрити.",
  },
};

const state = {
  cfg: null, lang: "en", files: [], system: "alpha",
  selected: new Set(), base: "", jobId: null,
  access: { unlocked: true, owner: false, free_left: null, day_left: null },
  deviceId: deviceId(), ownerKey: localStorage.getItem("atelier_owner_key") || "",
};

function deviceId() {
  let id = localStorage.getItem("atelier_device");
  if (!id) { id = "d_" + Math.random().toString(36).slice(2) + Date.now().toString(36); localStorage.setItem("atelier_device", id); }
  return id;
}

function t(key, vars) {
  let s = (I18N[state.lang] || I18N.en)[key] || I18N.en[key] || key;
  if (vars) for (const k in vars) s = s.replaceAll(`{${k}}`, vars[k]);
  return s;
}

function applyI18n() {
  $$("[data-i18n]").forEach((el) => { el.innerHTML = t(el.dataset.i18n); });
  document.documentElement.lang = state.lang;
  $("#consenttext").textContent = t("consent", { days: state.cfg.retention_days });
  $("#droplimits").textContent = t("droplimits", { n: state.cfg.max_images, mb: state.cfg.max_image_mb });
  $("#footernote").textContent = t("footer");
  $$("#langsw button").forEach((b) => b.classList.toggle("on", b.dataset.lang === state.lang));
  if (!state.cfg.email_enabled) $("#emailbox").classList.add("hidden");
  renderAccess();
}

/* ---- access (owner / freemium / daily limit) ---- */
async function refreshAccess() {
  try { state.access = await (await fetch(`/api/me?device=${state.deviceId}`)).json(); } catch (e) {}
  renderAccess();
}

// If this browser holds the owner key, (re)assert owner — survives server resets.
async function assertOwner() {
  if (!state.ownerKey) return;
  const fd = new FormData(); fd.append("key", state.ownerKey); fd.append("device_id", state.deviceId);
  try {
    const r = await fetch("/api/owner", { method: "POST", body: fd });
    if (!r.ok) localStorage.removeItem("atelier_owner_key");  // bad/old key
  } catch (e) {}
}

function renderAccess() {
  const badge = $("#accessbadge"), gen = $("#generate"), a = state.access;
  const paid = state.cfg.payments_enabled;
  gen.textContent = t("generate");
  badge.classList.add("hidden"); badge.classList.remove("ok");

  if (a.owner) { badge.textContent = t("badge_owner"); badge.classList.remove("hidden"); badge.classList.add("ok"); return; }

  if (paid && !a.unlocked) {
    const left = a.free_left;
    badge.textContent = t("badge_free", { n: left }); badge.classList.remove("hidden");
    if (left > 1) gen.textContent = t("generate_free", { n: left });
    else if (left === 1) gen.textContent = t("generate_last");
    else gen.textContent = t("unlock", { price: state.cfg.price_label });
    return;
  }
  if (paid && a.unlocked) { badge.textContent = t("badge_unlimited"); badge.classList.remove("hidden"); badge.classList.add("ok"); return; }

  // Free public mode: show remaining daily allowance if a limit is set.
  if (a.day_left !== null && a.day_left !== undefined) {
    badge.textContent = t("badge_today", { n: a.day_left }); badge.classList.remove("hidden");
  }
}

/* ---- files ---- */
function renderThumbs() {
  const wrap = $("#thumbs");
  wrap.innerHTML = "";
  state.files.forEach((f, i) => {
    const div = document.createElement("div");
    div.className = "thumb";
    const img = document.createElement("img");
    img.src = URL.createObjectURL(f);
    const btn = document.createElement("button");
    btn.textContent = "×";
    btn.onclick = (e) => { e.stopPropagation(); state.files.splice(i, 1); renderThumbs(); };
    div.append(img, btn);
    wrap.append(div);
  });
}
function addFiles(list) {
  for (const f of list) {
    if (!f.type.startsWith("image/")) continue;
    if (state.files.length >= state.cfg.max_images) break;
    state.files.push(f);
  }
  renderThumbs();
}

/* ---- sizes ---- */
function buildSystem() {
  const sel = $("#system");
  sel.innerHTML = "";
  Object.keys(state.cfg.size_systems).forEach((k) => {
    const o = document.createElement("option"); o.value = k; o.textContent = k; sel.append(o);
  });
  sel.value = state.system;
  buildSizes();
}
function buildSizes() {
  const sizes = state.cfg.size_systems[state.system];
  const def = { alpha: ["S", "M", "L", "XL"], "eu-women": ["36", "38", "40", "42"], "eu-men": ["48", "50", "52", "54"] }[state.system] || sizes.slice(2, 6);
  state.selected = new Set(def.filter((s) => sizes.includes(s)));
  state.base = def[Math.floor(def.length / 2)] || sizes[Math.floor(sizes.length / 2)];
  const box = $("#sizes");
  box.innerHTML = "";
  sizes.forEach((s) => {
    const chip = document.createElement("div");
    chip.className = "chip"; chip.textContent = s;
    chip.onclick = () => {
      if (state.selected.has(s)) state.selected.delete(s); else state.selected.add(s);
      if (s === state.base && !state.selected.has(s)) state.base = [...state.selected][0] || "";
      paintChips();
    };
    box.append(chip);
  });
  buildBase(); paintChips();
}
function buildBase() {
  const sel = $("#base"), order = state.cfg.size_systems[state.system];
  sel.innerHTML = "";
  [...state.selected].sort((a, b) => order.indexOf(a) - order.indexOf(b))
    .forEach((s) => { const o = document.createElement("option"); o.value = s; o.textContent = s; sel.append(o); });
  if (!state.selected.has(state.base)) state.base = sel.value;
  sel.value = state.base;
}
function paintChips() {
  $$("#sizes .chip").forEach((c) => {
    const s = c.textContent.replace("base", "");
    c.classList.toggle("on", state.selected.has(s) && s !== state.base);
    c.classList.toggle("base", s === state.base && state.selected.has(s));
    c.querySelector(".b")?.remove();
    if (s === state.base && state.selected.has(s)) {
      const b = document.createElement("span"); b.className = "b"; b.textContent = "base"; c.append(b);
    }
  });
  buildBase();
}

/* ---- generation ---- */
async function submitJob() {
  if (!$("#consent").checked) return alert(t("need_consent"));
  if (!state.files.length && !$("#notes").value.trim()) return alert(t("need_input"));
  if (!state.selected.size) return alert(t("need_size"));

  const fd = new FormData();
  fd.append("notes", $("#notes").value.trim());
  fd.append("garment", $("#garment").value);
  fd.append("size_system", state.system);
  fd.append("sizes", JSON.stringify([...state.selected]));
  fd.append("base", $("#base").value);
  fd.append("lang", state.lang);
  fd.append("consent", "true");
  fd.append("device_id", state.deviceId);
  state.files.forEach((f) => fd.append("images", f, f.name));

  showStep3(); showProgress(true);

  const res = await fetch("/api/jobs", { method: "POST", body: fd });
  const data = await res.json().catch(() => ({}));

  if (res.status === 402 && data.checkout_required) {
    $("#progressmsg").textContent = t("gen_pay");
    const cf = new FormData(); cf.append("job_id", data.job_id); cf.append("device_id", state.deviceId);
    const cr = await fetch("/api/checkout", { method: "POST", body: cf });
    const cj = await cr.json().catch(() => ({}));
    if (cj.url) { window.location = cj.url; return; }
    return showError(cj.detail || "Checkout failed.");
  }
  if (res.status === 429) { await refreshAccess(); return showError(data.detail || t("rate_limited")); }
  if (!res.ok) return showError(data.detail || "Request failed.");
  state.jobId = data.job_id;
  poll();
}

async function poll() {
  try {
    const res = await fetch(`/api/jobs/${state.jobId}`);
    if (!res.ok) return showError("Job not found.");
    const job = await res.json();
    if (job.status === "done") { await refreshAccess(); return showResult(job); }
    if (job.status === "error") return showError(job.error || "Generation failed.");
    setTimeout(poll, 2500);
  } catch (e) { setTimeout(poll, 3000); }
}

/* ---- views ---- */
function showForm() {
  $("#form").classList.remove("hidden");
  $("#step3").classList.add("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
}
function showStep3() {
  $("#form").classList.add("hidden");
  $("#step3").classList.remove("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
}
function showProgress(on) {
  $("#progress").classList.toggle("hidden", !on);
  $("#result").classList.add("hidden"); $("#error").classList.add("hidden");
  if (on) $("#progressmsg").textContent = t("gen_msg");
}
function showError(msg) {
  $("#progress").classList.add("hidden"); $("#result").classList.add("hidden");
  $("#error").classList.remove("hidden"); $("#errormsg").textContent = msg;
}
function showResult(job) {
  $("#progress").classList.add("hidden"); $("#error").classList.add("hidden");
  $("#result").classList.remove("hidden");
  const b = job.brief || {};
  $("#styleName").textContent = `${b.style_name || "Tech pack"} — ${b.style_code || ""}`;
  $("#styleMeta").textContent = `${b.garment_type || ""} · ${b.fabric || ""} · base ${job.base}`;
  $("#pdfframe").src = `/api/jobs/${job.id}/files/pdf`;
  $("#dlpdf").href = `/api/jobs/${job.id}/files/pdf`;
  $("#dlcsv").href = `/api/jobs/${job.id}/files/csv`;
  const pom = $("#pomtable");
  pom.innerHTML = "<tr><th>#</th><th>Point</th><th>cm</th><th>±</th></tr>";
  (b.points_of_measure || []).forEach((p) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td class="pom">${p.code}</td><td>${p.name}</td><td>${p.base_cm}</td><td>${p.tolerance_cm}</td>`;
    pom.append(tr);
  });
  const bom = $("#bomlist"); bom.innerHTML = "";
  (b.bill_of_materials || []).forEach((it) => {
    const li = document.createElement("li");
    li.textContent = `${it.component} — ${it.specification}${it.quantity ? " · " + it.quantity : ""}`;
    bom.append(li);
  });
  $("#emailstatus").textContent = "";
}

/* ---- payment return ---- */
async function resumeAfterPayment() {
  const q = new URLSearchParams(location.search);
  const paid = q.get("paid"), job = q.get("job"), dev = q.get("device");
  history.replaceState({}, "", location.pathname);
  if (q.get("canceled")) return false;
  if (!paid || !job) return false;
  state.jobId = job;
  showStep3(); showProgress(true);
  const fd = new FormData(); fd.append("paid_token", paid); fd.append("device_id", dev || state.deviceId);
  const res = await fetch(`/api/jobs/${job}/pay`, { method: "POST", body: fd });
  if (!res.ok) { const d = await res.json().catch(() => ({})); showError(d.detail || "Payment could not be confirmed."); return true; }
  poll();
  return true;
}

/* ---- email + delete ---- */
async function sendEmail() {
  const to = $("#emailto").value.trim();
  if (!to) return;
  $("#sendbtn").disabled = true;
  const fd = new FormData(); fd.append("to", to); fd.append("message", $("#emailmsg").value.trim());
  const res = await fetch(`/api/jobs/${state.jobId}/email`, { method: "POST", body: fd });
  const d = await res.json().catch(() => ({}));
  $("#emailstatus").textContent = res.ok ? t("email_sent", { to }) : t("email_fail", { err: d.detail || res.status });
  $("#sendbtn").disabled = false;
}
async function deleteData() {
  if (state.jobId) await fetch(`/api/jobs/${state.jobId}`, { method: "DELETE" });
  alert(t("deleted")); resetAll();
}
function resetAll() {
  state.files = []; renderThumbs();
  $("#notes").value = ""; $("#consent").checked = false;
  $("#pdfframe").src = ""; state.jobId = null;
  renderAccess(); showForm();
}

/* ---- init ---- */
async function init() {
  state.cfg = await (await fetch("/api/config")).json();
  const g = $("#garment");
  g.innerHTML = '<option value="">—</option>';
  state.cfg.garments.forEach((x) => { const o = document.createElement("option"); o.value = x; o.textContent = x; g.append(o); });
  buildSystem();
  applyI18n();

  // Owner activation: /?owner=KEY once on a device grants free-forever access.
  const ownerParam = new URLSearchParams(location.search).get("owner");
  if (ownerParam) {
    state.ownerKey = ownerParam;
    localStorage.setItem("atelier_owner_key", ownerParam);
    const url = new URL(location); url.searchParams.delete("owner"); history.replaceState({}, "", url);
  }
  await assertOwner();
  await refreshAccess();
  if (ownerParam && state.access.owner) alert(t("owner_on"));

  $$("#langsw button").forEach((b) => b.onclick = () => { state.lang = b.dataset.lang; applyI18n(); paintChips(); });

  const drop = $("#drop"), input = $("#files");
  drop.onclick = () => input.click();
  input.onchange = () => { addFiles(input.files); input.value = ""; };
  drop.ondragover = (e) => { e.preventDefault(); drop.classList.add("over"); };
  drop.ondragleave = () => drop.classList.remove("over");
  drop.ondrop = (e) => { e.preventDefault(); drop.classList.remove("over"); addFiles(e.dataTransfer.files); };

  $("#system").onchange = (e) => { state.system = e.target.value; buildSizes(); };
  $("#base").onchange = (e) => { state.base = e.target.value; paintChips(); };

  $("#generate").onclick = submitJob;
  $("#sendbtn").onclick = sendEmail;
  $("#deletebtn").onclick = deleteData;
  $("#startover").onclick = resetAll;
  $("#retry").onclick = showForm;

  await resumeAfterPayment();

  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
}

init();
