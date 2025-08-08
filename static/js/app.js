async function getJSON(url) { const r = await fetch(url); return r.json(); }

function renderHistory(rows) {
  const wrap = document.getElementById("history"); wrap.innerHTML = "";
  if (!rows || rows.length === 0) { wrap.innerHTML = "<div class='meta'>No history found.</div>"; return; }
  const ul = document.createElement("ul");
  rows.slice(-12).forEach(r => { const li = document.createElement("li"); li.className = "meta"; li.textContent = `${r.date}: ${r.item}`; ul.appendChild(li); });
  wrap.appendChild(ul);
}

function renderCustomerDetails(d) {
  const el = document.getElementById("customerDetails");
  if (!d || !d.name) { el.textContent = ""; return; }
  el.innerHTML = `<strong>${d.name}</strong><br>${d.address}<br>${d.phone} · ${d.email}`;
}

function renderInvoices(invoices) {
  const grid = document.getElementById("invoicesGrid");
  grid.innerHTML = "";
  invoices.forEach(inv => {
    const col = document.createElement("div");
    col.className = "col";
    const items = inv.items.map(i => `<li class="meta">${i}</li>`).join("");
    col.innerHTML = `<h3>${inv.date}</h3><ul>${items}</ul><div class="pill">Total: $${inv.total.toFixed(2)}</div>`;
    grid.appendChild(col);
  });
}

function updateInvoiceMeta(count) {
  const cap = 3; const meta = document.getElementById("invoiceMeta");
  meta.textContent = `${count} / ${cap} selected`;
  meta.style.color = (count > cap) ? "#f59e0b" : "";
}

function getSelectedInvoiceItems() {
  return Array.from(document.querySelectorAll(".invoice-item input[type=checkbox]:checked")).map(c => c.value);
}

function enforceMaxThree(e) {
  const selected = getSelectedInvoiceItems();
  if (selected.length > 3) { e.target.checked = false; return false; }
  updateInvoiceMeta(selected.length); return true;
}

function renderInvoicePicker(items) {
  const wrap = document.getElementById("invoicePicker"); wrap.innerHTML = "";
  items.forEach(name => {
    const div = document.createElement("div"); div.className = "invoice-item";
    const id = `inv-${name.replace(/\s+/g, "-")}`;
    div.innerHTML = `<label for="${id}"><input id="${id}" type="checkbox" value="${name}" /> <span style="margin-left:6px">${name}</span></label>`;
    const input = div.querySelector("input"); input.addEventListener("change", enforceMaxThree);
    wrap.appendChild(div);
  });
  updateInvoiceMeta(0);
}

function renderSuggestionColumn(title, list) {
  const col = document.createElement("div"); col.className = "col";
  col.innerHTML = `<h3>${title}</h3>`;
  if (!list || list.length === 0) { col.innerHTML += `<div class="meta">No suggestions</div>`; return col; }
  list.forEach(s => {
    const div = document.createElement("div"); div.className = "suggestion";
    div.innerHTML = `
      <div class="row"><strong>${s.item}</strong>
        <span class="meta">Probability: ${(s.probability*100).toFixed(1)}% | Score: ${(s.score*100).toFixed(1)}</span>
      </div>
      <div class="kicker">Support: ${s.support}, Similarity: ${s.similarity}${s.room ? ` · Room: ${s.room}` : ""}</div>
      <div class="bar"><div style="width:${Math.max(5, Math.min(100, s.score*100))}%"></div></div>`;
    col.appendChild(div);
  });
  return col;
}

async function loadCustomers() {
  const data = await getJSON("/api/customers");
  const select = document.getElementById("customerSelect");
  select.innerHTML = `<option value="">Select a customer...</option>`;
  data.forEach(d => {
    const opt = document.createElement("option"); opt.value = d.id; opt.textContent = `${d.id} — ${d.name}`; select.appendChild(opt);
  });
}

async function onCustomerChange() {
  const id = document.getElementById("customerSelect").value;
  document.getElementById("suggestionsGrid").innerHTML = "";
  document.getElementById("additionalGrid").innerHTML = "";
  if (!id) { document.getElementById("customerDetails").innerHTML = ""; document.getElementById("invoicesGrid").innerHTML=""; document.getElementById("history").innerHTML=""; return; }
  const [details, invoices, hist] = await Promise.all([
    getJSON(`/api/customer_details?customer_id=${encodeURIComponent(id)}`),
    getJSON(`/api/customer_invoices?customer_id=${encodeURIComponent(id)}&limit=2`),
    getJSON(`/api/customer_history?customer_id=${encodeURIComponent(id)}`)
  ]);
  renderCustomerDetails(details);
  renderInvoices(invoices);
  renderHistory(hist);
}

async function loadMainCatalog() {
  const items = await getJSON("/api/catalog_main");
  renderInvoicePicker(items);
}

async function getSuggestions() {
  try {
    const items = getSelectedInvoiceItems();
    if (items.length === 0) {
      alert("Select up to 3 products to add to the invoice.");
      return;
    }

    const grid = document.getElementById("suggestionsGrid");
    grid.innerHTML = "";

    // fetch suggestions per selected product
    const promises = items.map(item =>
      getJSON(`/api/suggest?item=${encodeURIComponent(item)}&k=5`)
        .then(d => ({ item, list: d.suggestions || [] }))
    );
    const results = await Promise.all(promises);
    results.forEach(({ item, list }) => {
      grid.appendChild(renderSuggestionColumn(item, list));
    });

    // additional recs based on previous invoices
    const cid = document.getElementById("customerSelect").value;
    if (!cid) return; // no customer selected

    const extra = await getJSON(`/api/additional_recs?customer_id=${encodeURIComponent(cid)}`);
    const extraGrid = document.getElementById("additionalGrid");
    extraGrid.innerHTML = "";
    extraGrid.appendChild(
      renderSuggestionColumn("For their rooms", (extra && extra.suggestions) ? extra.suggestions : [])
    );
  } catch (err) {
    console.error("Failed to get suggestions:", err);
    alert("Sorry—couldn’t load suggestions. Check the console for details.");
  }
}


document.addEventListener("DOMContentLoaded", async () => {
  await loadCustomers();
  await loadMainCatalog();
  document.getElementById("customerSelect").addEventListener("change", onCustomerChange);
  document.getElementById("suggestBtn").addEventListener("click", getSuggestions);
});
