async function getJSON(url) { const r = await fetch(url); return r.json(); }

function renderHistory(rows, invoices = []) {
  const wrap = document.getElementById("history"); wrap.innerHTML = "";
  if (!rows || rows.length === 0) { wrap.innerHTML = "<div class='meta'>No history found.</div>"; return; }
  
  // Find the oldest invoice date to filter history
  let oldestInvoiceDate = null;
  if (invoices && invoices.length > 0) {
    const dates = invoices.map(inv => new Date(inv.date)).sort((a, b) => a - b);
    oldestInvoiceDate = dates[0];
  }
  
  // Filter history to show only dates before the oldest invoice
  const filteredRows = oldestInvoiceDate 
    ? rows.filter(r => new Date(r.date) < oldestInvoiceDate)
    : rows;
  
  if (filteredRows.length === 0) {
    wrap.innerHTML = "<div class='meta'>No history before recent invoices.</div>";
    return;
  }
  
  const ul = document.createElement("ul");
  filteredRows.slice(-12).forEach(r => { 
    const li = document.createElement("li"); 
    li.textContent = `${r.date}: ${r.item}`; 
    ul.appendChild(li); 
  });
  wrap.appendChild(ul);
}

function renderCustomerDetails(d) {
  const el = document.getElementById("customerDetails");
  if (!d || !d.name) { el.textContent = ""; return; }
  el.innerHTML = `<strong>${d.name}</strong>${d.address}<br>${d.phone} · ${d.email}`;
}

function renderInvoices(invoices) {
  // Clear both invoice containers
  const invoice1 = document.getElementById("invoice1");
  const invoice2 = document.getElementById("invoice2");
  
  invoice1.innerHTML = "";
  invoice2.innerHTML = "";
  
  if (invoices && invoices.length > 0) {
    const inv1 = invoices[0];
    const items1 = inv1.items.map(i => `<li class="meta">${i}</li>`).join("");
    invoice1.innerHTML = `<div class="meta" style="margin-bottom: 8px;">${inv1.date}</div><ul style="list-style: none; padding: 0; margin: 0 0 12px 0;">${items1}</ul><div class="pill">Total: $${inv1.total.toFixed(2)}</div>`;
  }
  
  if (invoices && invoices.length > 1) {
    const inv2 = invoices[1];
    const items2 = inv2.items.map(i => `<li class="meta">${i}</li>`).join("");
    invoice2.innerHTML = `<div class="meta" style="margin-bottom: 8px;">${inv2.date}</div><ul style="list-style: none; padding: 0; margin: 0 0 12px 0;">${items2}</ul><div class="pill">Total: $${inv2.total.toFixed(2)}</div>`;
  }
  
  if (!invoices || invoices.length === 0) {
    invoice1.innerHTML = "<div class='meta'>No recent invoices.</div>";
  }
}

function updateInvoiceMeta(count) {
  const cap = 3; const meta = document.getElementById("invoiceMeta");
  meta.textContent = `${count} / ${cap} selected`;
  meta.style.color = (count > cap) ? "#f59e0b" : "";
}

function getSelectedInvoiceItems() {
  const dropdowns = ["product1", "product2", "product3"];
  return dropdowns.map(id => document.getElementById(id).value).filter(value => value !== "");
}

function updateDropdownOptions() {
  const selected = getSelectedInvoiceItems();
  const dropdowns = ["product1", "product2", "product3"];
  
  dropdowns.forEach(dropdownId => {
    const dropdown = document.getElementById(dropdownId);
    const currentValue = dropdown.value;
    
    Array.from(dropdown.options).forEach(option => {
      if (option.value === "") {
        option.disabled = false;
        return;
      }
      
      // Disable if selected in another dropdown, but not in current dropdown
      option.disabled = selected.includes(option.value) && option.value !== currentValue;
    });
  });
  
  updateInvoiceMeta(selected.length);
}

function renderInvoicePicker(items) {
  const dropdowns = ["product1", "product2", "product3"];
  
  dropdowns.forEach(dropdownId => {
    const dropdown = document.getElementById(dropdownId);
    dropdown.innerHTML = '<option value="">Select a product...</option>';
    
    items.forEach(name => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      dropdown.appendChild(option);
    });
    
    dropdown.addEventListener("change", updateDropdownOptions);
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
  document.getElementById("additionalGrid").innerHTML = "";
  if (!id) { 
    document.getElementById("customerDetails").innerHTML = ""; 
    document.getElementById("invoice1").innerHTML=""; 
    document.getElementById("invoice2").innerHTML=""; 
    document.getElementById("history").innerHTML=""; 
    return; 
  }
  const [details, invoices, hist] = await Promise.all([
    getJSON(`/api/customer_details?customer_id=${encodeURIComponent(id)}`),
    getJSON(`/api/customer_invoices?customer_id=${encodeURIComponent(id)}&limit=2`),
    getJSON(`/api/customer_history?customer_id=${encodeURIComponent(id)}`)
  ]);
  renderCustomerDetails(details);
  renderInvoices(invoices);
  renderHistory(hist, invoices);
  
  // Load AI insights if customer is selected
  if (details && details.name) {
    loadCustomerInsights(id);
  }
}

async function loadMainCatalog() {
  const items = await getJSON("/api/catalog_main");
  renderInvoicePicker(items);
}

async function getSuggestions() {
  try {
    const items = getSelectedInvoiceItems();
    if (items.length === 0) {
      alert("Select up to 3 products from the dropdowns to add to the order.");
      return;
    }

    // Show suggestions section FIRST
    const suggestionsSection = document.getElementById("suggestionsSection");
    if (suggestionsSection) {
      suggestionsSection.style.display = "block";
    }

    // Remove the button after showing the section
    const buttonContainer = document.querySelector(".button-container");
    if (buttonContainer) {
      buttonContainer.style.display = "none";
    }

    // Clear previous suggestions (now that section is visible)
    clearSuggestionColumns();

    // fetch suggestions per selected product
    const promises = items.map((item, index) =>
      getJSON(`/api/suggest?item=${encodeURIComponent(item)}&k=5`)
        .then(d => ({ item, list: d.suggestions || [], index }))
    );
    const results = await Promise.all(promises);
    
    // Render suggestions in columns
    results.forEach(({ item, list, index }) => {
      renderSuggestionInColumn(item, list, index + 1);
    });

    // Load AI explanation for recommendations (works with or without customer)
    loadRecommendationExplanation(items);

    // additional recs based on previous invoices (only if customer is selected)
    const cid = document.getElementById("customerSelect").value;
    if (cid) {
      const extra = await getJSON(`/api/additional_recs?customer_id=${encodeURIComponent(cid)}`);
      const extraGrid = document.getElementById("additionalGrid");
      extraGrid.innerHTML = "";
      extraGrid.appendChild(
        renderSuggestionColumn("For their rooms", (extra && extra.suggestions) ? extra.suggestions : [])
      );
    } else {
      // Clear additional recommendations if no customer selected
      const extraGrid = document.getElementById("additionalGrid");
      if (extraGrid) {
        extraGrid.innerHTML = "";
      }
    }
  } catch (err) {
    console.error("Failed to get suggestions:", err);
    alert("Sorry—couldn’t load suggestions. Check the console for details.");
  }
}


async function loadCustomerInsights(customerId) {
  const section = document.getElementById("aiInsightsSection");
  const content = document.getElementById("aiInsightsContent");
  
  try {
    // Show loading state
    section.style.display = "block";
    content.innerHTML = '<div class="ai-loading">Loading AI insights...</div>';
    
    const insights = await getJSON(`/api/customer_insights?customer_id=${encodeURIComponent(customerId)}`);
    
    if (insights.success && insights.insights) {
      content.innerHTML = formatInsightsForSales(insights.insights);
    } else if (insights.error) {
      if (insights.error.includes("not available") || insights.error.includes("not configured")) {
        section.style.display = "none"; // Hide if OpenAI not configured
      } else {
        content.innerHTML = `<div class="ai-error">Unable to generate insights: ${insights.error}</div>`;
      }
    }
  } catch (err) {
    console.warn("AI insights not available:", err);
    section.style.display = "none"; // Hide on error
  }
}

function formatInsightsForSales(insightsText) {
  // Parse the insights text and format it into cards
  const insights = parseInsights(insightsText);
  
  return insights.map(insight => `
    <div class="ai-insight-card ${insight.type}">
      <h4><span class="insight-icon">${insight.icon}</span>${insight.title}</h4>
      <p>${insight.content}</p>
    </div>
  `).join('');
}

function parseInsights(text) {
  const insights = [];
  
  // Split by numbered points and clean up
  const points = text.split(/\d+\.\s*\*?\*?/).filter(p => p.trim());
  
  points.forEach((point, index) => {
    let type = 'preferences';
    let icon = '👤';
    let title = 'Customer Profile';
    
    const cleanPoint = point.replace(/\*\*/g, '').trim();
    
    if (cleanPoint.toLowerCase().includes('preference') || cleanPoint.toLowerCase().includes('shows a preference')) {
      type = 'preferences';
      icon = '🎯';
      title = 'Preferences';
    } else if (cleanPoint.toLowerCase().includes('needs') || cleanPoint.toLowerCase().includes('potential needs')) {
      type = 'needs';  
      icon = '💡';
      title = 'Opportunities';
    } else if (cleanPoint.toLowerCase().includes('behavior') || cleanPoint.toLowerCase().includes('seasonal') || cleanPoint.toLowerCase().includes('buying')) {
      type = 'behavior';
      icon = '📈';
      title = 'Buying Patterns';
    }
    
    // Extract the main content after the category
    let content = cleanPoint;
    if (content.includes(':')) {
      content = content.split(':').slice(1).join(':').trim();
    }
    
    // Limit to 2-3 sentences for brevity
    const sentences = content.split('.').filter(s => s.trim());
    if (sentences.length > 2) {
      content = sentences.slice(0, 2).join('.') + '.';
    }
    
    if (content) {
      insights.push({ type, icon, title, content });
    }
  });
  
  return insights.length > 0 ? insights : [
    { type: 'preferences', icon: '🎯', title: 'Customer Analysis', content: text }
  ];
}

async function loadRecommendationExplanation(selectedProducts) {
  if (!selectedProducts || selectedProducts.length === 0) return;
  
  const container = document.getElementById("aiExplanation");
  const content = document.getElementById("aiExplanationContent");
  
  try {
    // Show loading state
    container.style.display = "block";
    content.innerHTML = '<div class="ai-loading">Analyzing recommendations...</div>';
    
    const params = selectedProducts.map(p => `products=${encodeURIComponent(p)}`).join('&');
    const explanation = await getJSON(`/api/recommendation_explanation?${params}`);
    
    if (explanation.success && explanation.explanation) {
      content.innerHTML = formatRecommendationCards(explanation.explanation, explanation.recommendations || []);
    } else if (explanation.error) {
      if (explanation.error.includes("not available") || explanation.error.includes("not configured")) {
        container.style.display = "none"; // Hide if OpenAI not configured
      } else {
        content.innerHTML = `<div class="ai-error">Unable to generate explanation: ${explanation.error}</div>`;
      }
    }
  } catch (err) {
    console.warn("AI explanation not available:", err);
    container.style.display = "none"; // Hide on error
  }
}

function formatRecommendationCards(explanationText, recommendations) {
  // Parse the explanation and create value-focused cards
  const cards = parseRecommendationExplanation(explanationText, recommendations);
  
  if (cards.length === 0) {
    return `<div class="recommendation-card">
      <h4>💰 Value Add-Ons</h4>
      <p>${explanationText}</p>
    </div>`;
  }
  
  return cards.map(card => `
    <div class="recommendation-card">
      <h4>${card.icon} ${card.title}</h4>
      <p>${card.content}</p>
    </div>
  `).join('');
}

function parseRecommendationExplanation(text, recommendations) {
  const cards = [];
  
  // Look for key value propositions and financial benefits
  const sentences = text.split(/[.!]/).filter(s => s.trim());
  
  sentences.forEach(sentence => {
    const lower = sentence.toLowerCase();
    let icon = '💡';
    let title = 'Smart Addition';
    let cardType = 'general';
    
    // Categorize by financial/practical value
    if (lower.includes('save') || lower.includes('cost') || lower.includes('money') || lower.includes('price')) {
      icon = '💰';
      title = 'Cost Savings';
      cardType = 'savings';
    } else if (lower.includes('protect') || lower.includes('warranty') || lower.includes('replacement') || lower.includes('insurance')) {
      icon = '🛡️';
      title = 'Protection Value';
      cardType = 'protection';
    } else if (lower.includes('maintenance') || lower.includes('care') || lower.includes('clean') || lower.includes('filter')) {
      icon = '🔧';
      title = 'Maintenance Essential';
      cardType = 'maintenance';
    } else if (lower.includes('performance') || lower.includes('efficiency') || lower.includes('better') || lower.includes('improve')) {
      icon = '⚡';
      title = 'Performance Boost';
      cardType = 'performance';
    } else if (lower.includes('convenience') || lower.includes('easy') || lower.includes('time') || lower.includes('effort')) {
      icon = '⏰';
      title = 'Time Saver';
      cardType = 'convenience';
    }
    
    const content = sentence.trim();
    if (content && content.length > 10) {
      cards.push({ icon, title, content, type: cardType });
    }
  });
  
  // If we have too many cards, prioritize by value type
  if (cards.length > 3) {
    const priorities = ['savings', 'protection', 'maintenance', 'performance', 'convenience', 'general'];
    cards.sort((a, b) => {
      const aIndex = priorities.indexOf(a.type);
      const bIndex = priorities.indexOf(b.type);
      return aIndex - bIndex;
    });
    return cards.slice(0, 3);
  }
  
  return cards;
}

function clearSuggestionColumns() {
  const elements = [
    'product1Suggestions',
    'product2Suggestions', 
    'product3Suggestions'
  ];
  
  const titles = [
    'product1Title',
    'product2Title',
    'product3Title'
  ];
  
  elements.forEach(id => {
    const element = document.getElementById(id);
    if (element) element.innerHTML = "";
  });
  
  titles.forEach((id, index) => {
    const element = document.getElementById(id);
    if (element) element.textContent = `Product ${index + 1} Add-Ons`;
  });
}

function renderSuggestionInColumn(productName, suggestions, columnNumber) {
  const titleElement = document.getElementById(`product${columnNumber}Title`);
  const contentElement = document.getElementById(`product${columnNumber}Suggestions`);
  
  // Check if elements exist
  if (!titleElement || !contentElement) {
    console.warn(`Suggestion column ${columnNumber} elements not found`);
    return;
  }
  
  // Update title
  titleElement.textContent = `${productName} Add-Ons`;
  
  // Render suggestions
  if (!suggestions || suggestions.length === 0) {
    contentElement.innerHTML = '<div class="meta">No suggestions available</div>';
    return;
  }
  
  const suggestionItems = suggestions.map(s => `
    <div class="suggestion-item">
      <h4>${s.item}</h4>
      <div class="suggestion-meta">
        <span>Score: ${(s.score*100).toFixed(1)}%</span>
        <span>Confidence: ${(s.probability*100).toFixed(1)}%</span>
      </div>
      <div class="score-bar">
        <div class="score-fill" style="width: ${Math.max(5, Math.min(100, s.score*100))}%"></div>
      </div>
    </div>
  `).join('');
  
  contentElement.innerHTML = suggestionItems;
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadCustomers();
  await loadMainCatalog();
  document.getElementById("customerSelect").addEventListener("change", onCustomerChange);
  document.getElementById("suggestBtn").addEventListener("click", getSuggestions);
});
