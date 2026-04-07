"""
Baron Kitchen OMS — Flask Application
======================================
Routes:
  GET  /                  → Dashboard (HTML)
  GET  /api/orders        → All orders (JSON)
  GET  /api/orders/<id>   → Single order (JSON)
  POST /api/orders/confirm/<id>   → Confirm a draft
  POST /api/orders/status/<id>    → Update status
  POST /api/intake/phone          → Submit phone transcript
  POST /api/intake/whatsapp       → Submit WhatsApp message
  POST /api/intake/email          → Submit email
  POST /api/intake/website        → Submit website order (JSON)
  POST /api/orders/dispatch/<id>  → Dispatch + auto-invoice
  GET  /api/alerts                → Alert log
  GET  /api/stats                 → Dashboard stats
  POST /api/demo/seed             → Seed demo data
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, request, render_template_string
from models.store import OrderStore
from models.order import OrderStatus
from channels.intake import phone_channel, whatsapp_channel, email_channel, website_channel
from services import alerts
from services.zoho import create_invoice, sync_to_crm
from demo import seed_demo_orders

app = Flask(__name__)
store = OrderStore()


# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD (Single-page HTML)
# ═══════════════════════════════════════════════════════════════════════════
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Baron Kitchen — Order Management</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f5f4f0; color: #1a1a18; font-size: 14px; }
  header { background: #1a1a18; color: #f5f4f0; padding: 16px 24px;
           display: flex; align-items: center; gap: 16px; }
  header h1 { font-size: 18px; font-weight: 500; }
  header .sub { font-size: 12px; opacity: .5; margin-left: auto; }
  .container { max-width: 1200px; margin: 0 auto; padding: 24px; }
  .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
  .metric { background: #fff; border: 0.5px solid #ddd; border-radius: 10px;
            padding: 16px; text-align: center; }
  .metric .val { font-size: 26px; font-weight: 500; }
  .metric .lbl { font-size: 11px; color: #888; margin-top: 4px; text-transform: uppercase; letter-spacing: .06em; }
  .metric.danger .val { color: #c0392b; }
  .metric.warning .val { color: #e67e22; }
  .metric.success .val { color: #27ae60; }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .card { background: #fff; border: 0.5px solid #ddd; border-radius: 10px; padding: 20px; }
  .card h2 { font-size: 13px; font-weight: 500; text-transform: uppercase;
             letter-spacing: .07em; color: #888; margin-bottom: 14px; }
  table { width: 100%; border-collapse: collapse; }
  th { font-size: 11px; font-weight: 500; color: #888; text-align: left;
       padding: 6px 8px; border-bottom: 1px solid #eee; text-transform: uppercase; letter-spacing: .05em; }
  td { padding: 8px 8px; border-bottom: 0.5px solid #f0f0f0; vertical-align: middle; }
  tr:last-child td { border-bottom: none; }
  .badge { display: inline-block; font-size: 10px; padding: 2px 8px; border-radius: 20px;
           font-weight: 500; white-space: nowrap; }
  .badge-draft       { background: #f0f0f0; color: #555; }
  .badge-confirmed   { background: #e8f5e9; color: #2e7d32; }
  .badge-in_kitchen  { background: #fff3e0; color: #e65100; }
  .badge-dispatched  { background: #e3f2fd; color: #1565c0; }
  .badge-billed      { background: #f3e5f5; color: #6a1b9a; }
  .badge-cancelled   { background: #fce4ec; color: #880e4f; }
  .badge-pending_review { background: #fff8e1; color: #f57f17; }
  .ch-phone    { background: #ede7f6; color: #4527a0; }
  .ch-whatsapp { background: #e8f5e9; color: #1b5e20; }
  .ch-email    { background: #e3f2fd; color: #0d47a1; }
  .ch-website  { background: #fce4ec; color: #880e4f; }
  .alert-item { padding: 8px 12px; border-radius: 8px; margin-bottom: 8px; font-size: 12px; }
  .alert-danger  { background: #fce4ec; border-left: 3px solid #e53935; }
  .alert-warning { background: #fff8e1; border-left: 3px solid #ffa000; }
  .alert-info    { background: #e3f2fd; border-left: 3px solid #1e88e5; }
  .alert-title { font-weight: 500; margin-bottom: 2px; }
  .alert-time  { font-size: 10px; color: #999; }
  .action-btn { font-size: 11px; padding: 3px 10px; border-radius: 6px; border: 0.5px solid #ddd;
                cursor: pointer; background: #fff; transition: background .15s; margin-right: 4px; }
  .action-btn:hover { background: #f5f5f5; }
  .action-btn.primary { background: #1a1a18; color: #fff; border-color: #1a1a18; }
  .action-btn.primary:hover { background: #333; }
  .intake-section { margin-top: 24px; }
  .intake-tabs { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
  .tab-btn { padding: 6px 14px; border-radius: 20px; border: 0.5px solid #ddd;
             cursor: pointer; font-size: 12px; background: #fff; transition: all .15s; }
  .tab-btn.active { background: #1a1a18; color: #fff; border-color: #1a1a18; }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }
  textarea, input[type=text] { width: 100%; border: 0.5px solid #ddd; border-radius: 8px;
    padding: 10px 12px; font-size: 13px; font-family: inherit; resize: vertical;
    background: #fafafa; transition: border-color .15s; }
  textarea:focus, input[type=text]:focus { outline: none; border-color: #888; background: #fff; }
  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
  .form-label { font-size: 11px; color: #888; margin-bottom: 4px; text-transform: uppercase; letter-spacing: .05em; }
  .submit-btn { margin-top: 12px; padding: 8px 20px; background: #1a1a18; color: #fff;
                border: none; border-radius: 8px; cursor: pointer; font-size: 13px;
                transition: background .15s; }
  .submit-btn:hover { background: #333; }
  .toast { position: fixed; bottom: 24px; right: 24px; background: #1a1a18; color: #fff;
           padding: 10px 18px; border-radius: 8px; font-size: 13px; display: none;
           z-index: 999; animation: slideIn .2s ease; }
  @keyframes slideIn { from { transform: translateY(10px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
  .refresh-note { font-size: 11px; color: #aaa; margin-top: 6px; text-align: right; }
  .phone-mode-toggle { display:flex; gap:8px; margin-bottom:14px; }
  .mode-btn { padding:5px 14px; border-radius:20px; border:0.5px solid #ddd; cursor:pointer;
              font-size:12px; background:#fff; transition:all .15s; }
  .mode-btn.active { background:#1a1a18; color:#fff; border-color:#1a1a18; }
  .item-row { display:grid; grid-template-columns:2fr 1fr 1fr auto; gap:8px;
              align-items:center; margin-bottom:8px; }
  .item-row input { margin:0; }
  .remove-item-btn { padding:4px 10px; border:0.5px solid #fcc; background:#fff8f8;
                     border-radius:6px; cursor:pointer; font-size:12px; color:#c0392b;
                     transition:background .15s; white-space:nowrap; }
  .remove-item-btn:hover { background:#fce4ec; }
  .add-item-btn { font-size:12px; padding:5px 12px; border:0.5px dashed #bbb;
                  border-radius:6px; background:#fafafa; cursor:pointer; color:#555;
                  transition:background .15s; margin-top:2px; }
  .add-item-btn:hover { background:#f0f0f0; }
  .wa-option-label { font-size:12px; color:#888; margin-bottom:12px;
                     padding:8px 10px; background:#f8f8f8; border-radius:6px;
                     border-left:3px solid #ddd; }
  .item-header { display:grid; grid-template-columns:2fr 1fr 1fr auto; gap:8px;
                 margin-bottom:4px; }
  .item-header span { font-size:10px; color:#aaa; text-transform:uppercase;
                      letter-spacing:.05em; padding-left:2px; }
  @media (max-width: 768px) { .two-col { grid-template-columns: 1fr; } .metrics { grid-template-columns: repeat(2,1fr); } }
</style>
</head>
<body>
<header>
  <div>🍱</div>
  <h1>Baron Kitchen — Order Management System</h1>
  <span class="sub" id="clock"></span>
</header>

<div class="container">

  <!-- Metrics Row -->
  <div class="metrics" id="metrics-row">
    <div class="metric"><div class="val" id="m-total">—</div><div class="lbl">Total Orders</div></div>
    <div class="metric success"><div class="val" id="m-revenue">—</div><div class="lbl">Revenue (₹)</div></div>
    <div class="metric warning"><div class="val" id="m-drafts">—</div><div class="lbl">Stale Drafts</div></div>
    <div class="metric danger"><div class="val" id="m-unbilled">—</div><div class="lbl">Unbilled Dispatched</div></div>
  </div>

  <div class="two-col">
    <!-- Orders Table -->
    <div class="card" style="overflow-x:auto">
      <h2>Live Order Board</h2>
      <table id="orders-table">
        <thead>
          <tr>
            <th>ID</th><th>Channel</th><th>Client</th><th>Items</th>
            <th>Total</th><th>Status</th><th>Actions</th>
          </tr>
        </thead>
        <tbody id="orders-tbody"></tbody>
      </table>
      <p class="refresh-note">Auto-refreshes every 10s</p>
    </div>

    <!-- Right column -->
    <div>
      <!-- Alerts -->
      <div class="card" style="margin-bottom: 20px;">
        <h2>Alerts &amp; Fail-safes</h2>
        <div id="alerts-list"><p style="color:#aaa;font-size:12px">No alerts yet.</p></div>
      </div>

      <!-- Channel chart -->
      <div class="card">
        <h2>Orders by Channel</h2>
        <div id="channel-chart" style="display:flex;gap:8px;align-items:flex-end;height:80px;margin-top:8px;"></div>
      </div>
    </div>
  </div>

  <!-- Intake Simulator -->
  <div class="intake-section">
    <div class="card">
      <h2>Simulate Order Intake</h2>
      <div class="intake-tabs">
        <button class="tab-btn active" onclick="switchTab('phone')">📞 Phone</button>
        <button class="tab-btn" onclick="switchTab('whatsapp')">💬 WhatsApp</button>
        <button class="tab-btn" onclick="switchTab('email')">✉️ Email</button>
        <button class="tab-btn" onclick="switchTab('website')">🌐 Website</button>
      </div>

      <div id="tab-phone" class="tab-panel active">

        <!-- Manual Entry Form -->
        <div id="phone-form-mode">
          <div class="form-row">
            <div>
              <div class="form-label">Customer Name *</div>
              <input type="text" id="pf-name" placeholder="e.g. Raj Mehta / Infosys Pune">
            </div>
            <div>
              <div class="form-label">Phone Number *</div>
              <input type="text" id="pf-phone" placeholder="+91 98765 43210">
            </div>
          </div>
          <div class="form-row">
            <div>
              <div class="form-label">Delivery Date & Time *</div>
              <input type="text" id="pf-delivery-time" placeholder="e.g. Tomorrow 1pm / 2025-02-10 12:30">
            </div>
            <div>
              <div class="form-label">Delivery Address *</div>
              <input type="text" id="pf-address" placeholder="e.g. Infosys BPO, Hinjewadi Phase 2">
            </div>
          </div>

          <!-- Order Items -->
          <div class="form-label" style="margin-bottom:8px">Order Items *</div>
          <div id="pf-items-list"></div>
          <button class="add-item-btn" onclick="addPhoneItem()">+ Add Item</button>

          <div style="margin-top:12px">
            <div class="form-label">Special Instructions</div>
            <input type="text" id="pf-instructions" placeholder="e.g. No onion in veg items, extra spicy for non-veg">
          </div>

          <div style="display:flex;align-items:center;gap:12px;margin-top:14px">
            <button class="submit-btn" onclick="submitPhoneForm()">Save Order →</button>
            <span id="pf-total-preview" style="font-size:13px;font-weight:500;color:#555"></span>
          </div>
        </div>

      </div>

      <div id="tab-whatsapp" class="tab-panel">

        <!-- Manual Entry -->
        <div id="wa-form-mode">
          <div class="wa-option-label">Customer sends message → you copy key details → fill form → Save ✅</div>
          <div class="form-row">
            <div>
              <div class="form-label">Customer Name *</div>
              <input type="text" id="wa-name" placeholder="e.g. Priya Sharma / TCS Pune">
            </div>
            <div>
              <div class="form-label">WhatsApp Number *</div>
              <input type="text" id="wa-phone" placeholder="+91 98765 43210">
            </div>
          </div>
          <div class="form-row">
            <div>
              <div class="form-label">Delivery Date &amp; Time</div>
              <input type="text" id="wa-delivery-time" placeholder="e.g. Friday 1pm / 2025-02-10 13:00">
            </div>
            <div>
              <div class="form-label">Delivery Address</div>
              <input type="text" id="wa-address" placeholder="e.g. TCS Tower, Hinjewadi Phase 1">
            </div>
          </div>
          <div class="form-label" style="margin-bottom:8px">Order Items *</div>
          <div id="wa-items-list"></div>
          <button class="add-item-btn" onclick="addWaItem()">+ Add Item</button>
          <div style="margin-top:12px">
            <div class="form-label">Special Instructions</div>
            <input type="text" id="wa-instructions" placeholder="e.g. Jain food for 5 people, no garlic">
          </div>
          <div style="display:flex;align-items:center;gap:12px;margin-top:14px">
            <button class="submit-btn" onclick="submitWaForm()">Save Order →</button>
            <span id="wa-total-preview" style="font-size:13px;font-weight:500;color:#555"></span>
          </div>
        </div>

      </div>

      <div id="tab-email" class="tab-panel">

        <!-- Manual Entry -->
        <div id="em-form-mode">
          <div class="wa-option-label">Open email → copy key details → fill form below → Save ✅</div>
          <div class="form-row">
            <div>
              <div class="form-label">Customer / Company Name *</div>
              <input type="text" id="em-name" placeholder="e.g. Wipro Pune / Neha Joshi">
            </div>
            <div>
              <div class="form-label">Sender Email *</div>
              <input type="text" id="em-email" placeholder="manager@wipro.com">
            </div>
          </div>
          <div class="form-row">
            <div>
              <div class="form-label">Delivery Date &amp; Time</div>
              <input type="text" id="em-delivery-time" placeholder="e.g. Monday 12:30pm / 2025-02-10 12:30">
            </div>
            <div>
              <div class="form-label">Delivery Address</div>
              <input type="text" id="em-address" placeholder="e.g. Tech Park, Baner, Pune">
            </div>
          </div>
          <div class="form-label" style="margin-bottom:8px">Order Items *</div>
          <div id="em-items-list"></div>
          <button class="add-item-btn" onclick="addEmItem()">+ Add Item</button>
          <div style="margin-top:12px">
            <div class="form-label">Special Instructions</div>
            <input type="text" id="em-instructions" placeholder="e.g. Jain meals for 10 people, deliver before 12:30 sharp">
          </div>
          <div style="display:flex;align-items:center;gap:12px;margin-top:14px">
            <button class="submit-btn" onclick="submitEmForm()">Save Order →</button>
            <span id="em-total-preview" style="font-size:13px;font-weight:500;color:#555"></span>
          </div>
        </div>

      </div>

      <div id="tab-website" class="tab-panel">
        <div class="form-label">Website JSON payload (structured form data)</div>
        <textarea id="website-json" rows="8">{
  "client_name": "Accenture Pune",
  "client_contact": "admin@accenture.com",
  "delivery_date": "2025-02-10T12:30:00",
  "delivery_address": "Magarpatta City, Pune",
  "special_instructions": "No onion in veg items",
  "items": [
    {"sku": "VEG-001", "name": "Veg Thali", "qty": 50, "unit_price": 180},
    {"sku": "NVG-002", "name": "Chicken Biryani", "qty": 30, "unit_price": 220}
  ]
}</textarea>
        <button class="submit-btn" onclick="submitIntake('website')">Submit Order →</button>
      </div>

    </div>
  </div>

  <!-- Demo seed -->
  <div style="margin-top:16px;text-align:center">
    <button class="action-btn primary" onclick="seedDemo()">🌱 Load Demo Data</button>
    <span style="font-size:11px;color:#aaa;margin-left:8px">Populates sample orders across all channels</span>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
const fmt = n => '₹' + Number(n).toLocaleString('en-IN');

async function loadDashboard() {
  const [stats, orders, alertsData] = await Promise.all([
    fetch('/api/stats').then(r => r.json()),
    fetch('/api/orders').then(r => r.json()),
    fetch('/api/alerts').then(r => r.json()),
  ]);

  // Metrics
  document.getElementById('m-total').textContent = stats.total_orders;
  document.getElementById('m-revenue').textContent = fmt(stats.total_revenue);
  document.getElementById('m-drafts').textContent = stats.stale_drafts;
  document.getElementById('m-unbilled').textContent = stats.unbilled_dispatched;

  // Orders table
  const tbody = document.getElementById('orders-tbody');
  tbody.innerHTML = orders.map(o => `
    <tr>
      <td style="font-family:monospace;font-size:12px">${o.order_id}</td>
      <td><span class="badge ch-${o.channel}">${o.channel}</span></td>
      <td>${o.client_name || '<span style="color:#bbb">Unknown</span>'}</td>
      <td style="font-size:12px">${o.items.map(i => i.qty+'x '+i.name).join(', ').substring(0,40) || '—'}</td>
      <td style="font-weight:500">${fmt(o.total)}</td>
      <td><span class="badge badge-${o.status}">${o.status_label}</span></td>
      <td>${actionButtons(o)}</td>
    </tr>`).join('');

  // Alerts
  const alertsList = document.getElementById('alerts-list');
  if (alertsData.length === 0) {
    alertsList.innerHTML = '<p style="color:#aaa;font-size:12px">No alerts.</p>';
  } else {
    alertsList.innerHTML = alertsData.slice(0, 6).map(a => `
      <div class="alert-item alert-${a.level}">
        <div class="alert-title">${a.title}</div>
        <div>${a.body}</div>
        <div class="alert-time">${a.timestamp.substring(11,19)}</div>
      </div>`).join('');
  }

  // Channel bar chart
  const chartDiv = document.getElementById('channel-chart');
  const channels = ['phone','whatsapp','email','website'];
  const colors   = {'phone':'#7F77DD','whatsapp':'#1D9E75','email':'#378ADD','website':'#D85A30'};
  const maxVal   = Math.max(1, ...channels.map(c => stats.by_channel[c] || 0));
  chartDiv.innerHTML = channels.map(c => {
    const v = stats.by_channel[c] || 0;
    const pct = Math.round((v / maxVal) * 100);
    return `<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:4px">
      <span style="font-size:11px;font-weight:500">${v}</span>
      <div style="width:100%;height:${Math.max(4, pct * 0.6)}px;background:${colors[c]};border-radius:4px 4px 0 0"></div>
      <span style="font-size:10px;color:#888">${c}</span>
    </div>`;
  }).join('');
}

function actionButtons(o) {
  const btns = [];
  if (o.status === 'draft' || o.status === 'pending_review') {
    btns.push(`<button class="action-btn primary" onclick="confirmOrder('${o.order_id}')">Confirm</button>`);
  }
  if (o.status === 'confirmed') {
    btns.push(`<button class="action-btn" onclick="updateStatus('${o.order_id}','in_kitchen')">→ Kitchen</button>`);
  }
  if (o.status === 'in_kitchen') {
    btns.push(`<button class="action-btn" onclick="dispatchOrder('${o.order_id}')">Dispatch + Invoice</button>`);
  }
  if (o.status === 'dispatched' && !o.zoho_invoice_id) {
    btns.push(`<button class="action-btn" onclick="dispatchOrder('${o.order_id}')">Create Invoice</button>`);
  }
  return btns.join('') || '<span style="color:#ccc;font-size:11px">—</span>';
}

async function confirmOrder(id) {
  await fetch(`/api/orders/confirm/${id}`, {method:'POST'});
  showToast('Order confirmed ✓');
  loadDashboard();
}
async function updateStatus(id, status) {
  await fetch(`/api/orders/status/${id}`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({status})
  });
  loadDashboard();
}
async function dispatchOrder(id) {
  await fetch(`/api/orders/dispatch/${id}`, {method:'POST'});
  showToast('Dispatched & invoice created ✓');
  loadDashboard();
}

async function submitIntake(channel) {
  let payload, url;
  if (channel === 'phone') {
    const t = document.getElementById('phone-text').value.trim();
    if (!t) return;
    url = '/api/intake/phone';
    payload = {transcript: t};
  } else if (channel === 'whatsapp') {
    const t = document.getElementById('wa-text').value.trim();
    if (!t) return;
    url = '/api/intake/whatsapp';
    payload = {message: t, sender: document.getElementById('wa-sender').value};
  } else if (channel === 'email') {
    const body = document.getElementById('email-body').value.trim();
    if (!body) return;
    url = '/api/intake/email';
    payload = {
      subject: document.getElementById('email-subject').value,
      body,
      sender_email: document.getElementById('email-from').value
    };
  } else {
    const raw = document.getElementById('website-json').value.trim();
    try { payload = JSON.parse(raw); } catch(e) { showToast('Invalid JSON!'); return; }
    url = '/api/intake/website';
  }
  const resp = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });
  const data = await resp.json();
  showToast(`Order ${data.order_id} captured via ${channel} ✓`);
  loadDashboard();
}

async function seedDemo() {
  await fetch('/api/demo/seed', {method:'POST'});
  showToast('Demo data loaded ✓');
  loadDashboard();
}

// ── Email Manual Entry Form ───────────────────────────────────────────────
let emItems = [];


function addEmItem(name='', qty='', price='') {
  emItems.push({ name, qty, price });
  renderEmItems();
}

function removeEmItem(idx) {
  emItems.splice(idx, 1);
  renderEmItems();
}

function renderEmItems() {
  const container = document.getElementById('em-items-list');
  if (emItems.length === 0) { container.innerHTML = ''; updateEmTotal(); return; }
  container.innerHTML = `
    <div class="item-header">
      <span>Item Name</span><span>Qty</span><span>Unit Price (₹)</span><span></span>
    </div>` +
    emItems.map((item, idx) => `
    <div class="item-row">
      <input type="text" placeholder="e.g. Veg Thali" value="${item.name}"
        oninput="emItems[${idx}].name=this.value;updateEmTotal()">
      <input type="text" placeholder="30" value="${item.qty}"
        oninput="emItems[${idx}].qty=this.value;updateEmTotal()">
      <input type="text" placeholder="180" value="${item.price}"
        oninput="emItems[${idx}].price=this.value;updateEmTotal()">
      <button class="remove-item-btn" onclick="removeEmItem(${idx})">✕</button>
    </div>`).join('');
  updateEmTotal();
}

function updateEmTotal() {
  let total = 0;
  for (const item of emItems) {
    total += (parseFloat(item.qty) || 0) * (parseFloat(item.price) || 0);
  }
  const el = document.getElementById('em-total-preview');
  el.textContent = total > 0 ? 'Est. Total: ₹' + total.toLocaleString('en-IN') : '';
}

async function submitEmForm() {
  const name    = document.getElementById('em-name').value.trim();
  const email   = document.getElementById('em-email').value.trim();
  const time    = document.getElementById('em-delivery-time').value.trim();
  const address = document.getElementById('em-address').value.trim();
  const notes   = document.getElementById('em-instructions').value.trim();

  if (!name)  { showToast('⚠️ Customer name is required'); return; }
  if (!email) { showToast('⚠️ Sender email is required'); return; }
  const validItems = emItems.filter(i => i.name && parseFloat(i.qty) > 0);
  if (!validItems.length) { showToast('⚠️ Add at least one item with name & qty'); return; }

  const payload = {
    client_name: name,
    client_contact: email,
    delivery_time_raw: time,
    delivery_address: address,
    special_instructions: notes,
    items: validItems.map((i, idx) => ({
      sku: `EM-${String(idx+1).padStart(3,'0')}`,
      name: i.name,
      qty: parseInt(i.qty) || 1,
      unit_price: parseFloat(i.price) || 0
    }))
  };

  const resp = await fetch('/api/intake/email/manual', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  });
  const data = await resp.json();
  showToast(`✅ Email order ${data.order_id} saved — pending confirmation`);

  // Reset form
  emItems = [];
  renderEmItems();
  ['em-name','em-email','em-delivery-time','em-address','em-instructions']
    .forEach(id => document.getElementById(id).value = '');
  document.getElementById('em-total-preview').textContent = '';
  loadDashboard();
}

// Pre-seed one blank row
addEmItem();

// ── WhatsApp Manual Entry Form (Option A) ────────────────────────────────
let waItems = [];


function addWaItem(name='', qty='', price='') {
  waItems.push({ name, qty, price });
  renderWaItems();
}

function removeWaItem(idx) {
  waItems.splice(idx, 1);
  renderWaItems();
}

function renderWaItems() {
  const container = document.getElementById('wa-items-list');
  if (waItems.length === 0) { container.innerHTML = ''; updateWaTotal(); return; }
  container.innerHTML = `
    <div class="item-header">
      <span>Item Name</span><span>Qty</span><span>Unit Price (₹)</span><span></span>
    </div>` +
    waItems.map((item, idx) => `
    <div class="item-row">
      <input type="text" placeholder="e.g. Paneer Box" value="${item.name}"
        oninput="waItems[${idx}].name=this.value;updateWaTotal()">
      <input type="text" placeholder="25" value="${item.qty}"
        oninput="waItems[${idx}].qty=this.value;updateWaTotal()">
      <input type="text" placeholder="180" value="${item.price}"
        oninput="waItems[${idx}].price=this.value;updateWaTotal()">
      <button class="remove-item-btn" onclick="removeWaItem(${idx})">✕</button>
    </div>`).join('');
  updateWaTotal();
}

function updateWaTotal() {
  let total = 0;
  for (const item of waItems) {
    total += (parseFloat(item.qty) || 0) * (parseFloat(item.price) || 0);
  }
  const el = document.getElementById('wa-total-preview');
  el.textContent = total > 0 ? 'Est. Total: ₹' + total.toLocaleString('en-IN') : '';
}

async function submitWaForm() {
  const name    = document.getElementById('wa-name').value.trim();
  const phone   = document.getElementById('wa-phone').value.trim();
  const time    = document.getElementById('wa-delivery-time').value.trim();
  const address = document.getElementById('wa-address').value.trim();
  const notes   = document.getElementById('wa-instructions').value.trim();

  if (!name)  { showToast('⚠️ Customer name is required'); return; }
  if (!phone) { showToast('⚠️ WhatsApp number is required'); return; }
  const validItems = waItems.filter(i => i.name && parseFloat(i.qty) > 0);
  if (!validItems.length) { showToast('⚠️ Add at least one item with name & qty'); return; }

  const payload = {
    client_name: name,
    client_contact: phone,
    delivery_time_raw: time,
    delivery_address: address,
    special_instructions: notes,
    items: validItems.map((i, idx) => ({
      sku: `WA-${String(idx+1).padStart(3,'0')}`,
      name: i.name,
      qty: parseInt(i.qty) || 1,
      unit_price: parseFloat(i.price) || 0
    }))
  };

  const resp = await fetch('/api/intake/whatsapp/manual', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  });
  const data = await resp.json();
  showToast(`✅ WhatsApp order ${data.order_id} saved — pending confirmation`);

  // Reset
  waItems = [];
  renderWaItems();
  ['wa-name','wa-phone','wa-delivery-time','wa-address','wa-instructions']
    .forEach(id => document.getElementById(id).value = '');
  document.getElementById('wa-total-preview').textContent = '';
  loadDashboard();
}

// Pre-seed one blank row
addWaItem();


let phoneItems = [];


function addPhoneItem(name='', qty='', price='') {
  const idx = phoneItems.length;
  phoneItems.push({ name, qty, price });
  renderPhoneItems();
}

function removePhoneItem(idx) {
  phoneItems.splice(idx, 1);
  renderPhoneItems();
}

function renderPhoneItems() {
  const container = document.getElementById('pf-items-list');
  if (phoneItems.length === 0) {
    container.innerHTML = '';
    updatePhoneTotal();
    return;
  }
  container.innerHTML = `
    <div class="item-header">
      <span>Item Name</span><span>Qty</span><span>Unit Price (₹)</span><span></span>
    </div>` +
    phoneItems.map((item, idx) => `
    <div class="item-row">
      <input type="text" placeholder="e.g. Veg Thali" value="${item.name}"
        oninput="phoneItems[${idx}].name=this.value;updatePhoneTotal()">
      <input type="text" placeholder="30" value="${item.qty}"
        oninput="phoneItems[${idx}].qty=this.value;updatePhoneTotal()">
      <input type="text" placeholder="180" value="${item.price}"
        oninput="phoneItems[${idx}].price=this.value;updatePhoneTotal()">
      <button class="remove-item-btn" onclick="removePhoneItem(${idx})">✕</button>
    </div>`).join('');
  updatePhoneTotal();
}

function updatePhoneTotal() {
  let total = 0;
  for (const item of phoneItems) {
    const q = parseFloat(item.qty) || 0;
    const p = parseFloat(item.price) || 0;
    total += q * p;
  }
  const el = document.getElementById('pf-total-preview');
  el.textContent = total > 0 ? 'Est. Total: ₹' + total.toLocaleString('en-IN') : '';
}

async function submitPhoneForm() {
  const name = document.getElementById('pf-name').value.trim();
  const phone = document.getElementById('pf-phone').value.trim();
  const deliveryTime = document.getElementById('pf-delivery-time').value.trim();
  const address = document.getElementById('pf-address').value.trim();
  const instructions = document.getElementById('pf-instructions').value.trim();

  if (!name) { showToast('⚠️ Customer name is required'); return; }
  if (!phone) { showToast('⚠️ Phone number is required'); return; }
  if (phoneItems.length === 0) { showToast('⚠️ Add at least one item'); return; }

  const validItems = phoneItems.filter(i => i.name && parseFloat(i.qty) > 0);
  if (validItems.length === 0) { showToast('⚠️ Items need a name and quantity'); return; }

  const payload = {
    client_name: name,
    client_contact: phone,
    delivery_time_raw: deliveryTime,
    delivery_address: address,
    special_instructions: instructions,
    items: validItems.map((i, idx) => ({
      sku: `PHONE-${String(idx+1).padStart(3,'0')}`,
      name: i.name,
      qty: parseInt(i.qty) || 1,
      unit_price: parseFloat(i.price) || 0
    }))
  };

  const resp = await fetch('/api/intake/phone/manual', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  });
  const data = await resp.json();
  showToast(`✅ Order ${data.order_id} saved — pending confirmation`);

  // Reset form
  phoneItems = [];
  renderPhoneItems();
  ['pf-name','pf-phone','pf-delivery-time','pf-address','pf-instructions']
    .forEach(id => document.getElementById(id).value = '');
  document.getElementById('pf-total-preview').textContent = '';
  loadDashboard();
}

// Pre-add one blank item row on load
addPhoneItem();

function switchTab(name) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  event.target.classList.add('active');
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 3000);
}

function updateClock() {
  document.getElementById('clock').textContent = new Date().toLocaleString('en-IN');
}

loadDashboard();
setInterval(loadDashboard, 10000);
setInterval(updateClock, 1000);
updateClock();
</script>
</body>
</html>"""


@app.route("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML)


@app.route("/order")
def customer_portal():
    from flask import render_template
    return render_template("customer_portal.html")


# ═══════════════════════════════════════════════════════════════════════════
# API ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/orders")
def get_orders():
    return jsonify([o.to_dict() for o in store.all()])


@app.route("/api/orders/<order_id>")
def get_order(order_id):
    order = store.get(order_id)
    if not order:
        return jsonify({"error": "Not found"}), 404
    return jsonify(order.to_dict())


@app.route("/api/orders/confirm/<order_id>", methods=["POST"])
def confirm_order(order_id):
    order = store.update_status(order_id, OrderStatus.CONFIRMED, confirmed_by="staff")
    if not order:
        return jsonify({"error": "Not found"}), 404
    alerts.notify_status_change(order, "draft")
    sync_to_crm(order)
    return jsonify(order.to_dict())


@app.route("/api/orders/status/<order_id>", methods=["POST"])
def update_status(order_id):
    data = request.get_json()
    try:
        new_status = OrderStatus(data["status"])
    except (KeyError, ValueError):
        return jsonify({"error": "Invalid status"}), 400
    order = store.get(order_id)
    if not order:
        return jsonify({"error": "Not found"}), 404
    old = order.status.value
    store.update_status(order_id, new_status)
    alerts.notify_status_change(order, old)
    return jsonify(order.to_dict())


@app.route("/api/orders/dispatch/<order_id>", methods=["POST"])
def dispatch_order(order_id):
    order = store.get(order_id)
    if not order:
        return jsonify({"error": "Not found"}), 404
    store.update_status(order_id, OrderStatus.DISPATCHED)
    invoice_id = create_invoice(order)
    return jsonify({**order.to_dict(), "invoice_id": invoice_id})


# ── Intake endpoints ──────────────────────────────────────────────────────
@app.route("/api/intake/phone", methods=["POST"])
def intake_phone():
    data = request.get_json()
    order = phone_channel.intake(transcript=data.get("transcript", ""))
    return jsonify(order.to_dict()), 201


@app.route("/api/intake/phone/manual", methods=["POST"])
def intake_phone_manual():
    """
    Manual phone order entry — staff fills in structured fields during/after a call.
    Creates a DRAFT order (pending_review) that staff must confirm.
    """
    from models.order import Order, OrderChannel, OrderItem, OrderStatus
    from datetime import datetime
    import re

    data = request.get_json()

    # Parse delivery time from free-text
    delivery_date = None
    raw_time = data.get("delivery_time_raw", "").strip()
    if raw_time:
        # Try ISO format first
        try:
            delivery_date = datetime.fromisoformat(raw_time)
        except ValueError:
            pass  # Leave as None — staff will confirm

    items = []
    for i, item_data in enumerate(data.get("items", [])):
        items.append(OrderItem(
            sku=item_data.get("sku", f"PHONE-{i+1:03d}"),
            name=item_data["name"],
            qty=int(item_data.get("qty", 1)),
            unit_price=float(item_data.get("unit_price", 0.0)),
        ))

    order = Order(
        channel=OrderChannel.PHONE,
        status=OrderStatus.PENDING_REVIEW,
        client_name=data.get("client_name", ""),
        client_contact=data.get("client_contact", ""),
        items=items,
        delivery_date=delivery_date,
        delivery_address=data.get("delivery_address", ""),
        special_instructions=data.get("special_instructions", ""),
        raw_input=f"[Manual Entry] Name: {data.get('client_name','')} | Phone: {data.get('client_contact','')} | Delivery: {raw_time}",
        ai_confidence=1.0,  # Staff entered — full confidence
        confirmed_by="pending_staff",
    )

    store.save(order)
    alerts.notify_new_order(order)
    return jsonify(order.to_dict()), 201


@app.route("/api/intake/whatsapp", methods=["POST"])
def intake_whatsapp():
    data = request.get_json()
    order = whatsapp_channel.intake(
        message=data.get("message", ""),
        sender=data.get("sender", ""),
    )
    return jsonify(order.to_dict()), 201


@app.route("/api/intake/whatsapp/manual", methods=["POST"])
def intake_whatsapp_manual():
    """
    Option A: Admin manually enters order details copied from WhatsApp.
    Creates a PENDING_REVIEW order — staff confirms on dashboard.
    """
    from models.order import Order, OrderChannel, OrderItem, OrderStatus
    from datetime import datetime

    data = request.get_json()

    delivery_date = None
    raw_time = data.get("delivery_time_raw", "").strip()
    if raw_time:
        try:
            delivery_date = datetime.fromisoformat(raw_time)
        except ValueError:
            pass

    items = []
    for i, item_data in enumerate(data.get("items", [])):
        items.append(OrderItem(
            sku=item_data.get("sku", f"WA-{i+1:03d}"),
            name=item_data["name"],
            qty=int(item_data.get("qty", 1)),
            unit_price=float(item_data.get("unit_price", 0.0)),
        ))

    order = Order(
        channel=OrderChannel.WHATSAPP,
        status=OrderStatus.PENDING_REVIEW,
        client_name=data.get("client_name", ""),
        client_contact=data.get("client_contact", ""),
        items=items,
        delivery_date=delivery_date,
        delivery_address=data.get("delivery_address", ""),
        special_instructions=data.get("special_instructions", ""),
        raw_input=f"[WhatsApp Manual] {data.get('client_name','')} | {data.get('client_contact','')} | Delivery: {raw_time}",
        ai_confidence=1.0,
        confirmed_by="pending_staff",
    )

    store.save(order)
    alerts.notify_new_order(order)
    return jsonify(order.to_dict()), 201


@app.route("/api/intake/email", methods=["POST"])
def intake_email():
    data = request.get_json()
    order = email_channel.intake(
        subject=data.get("subject", ""),
        body=data.get("body", ""),
        sender_email=data.get("sender_email", ""),
    )
    return jsonify(order.to_dict()), 201


@app.route("/api/intake/email/manual", methods=["POST"])
def intake_email_manual():
    """
    Manual entry: admin copies key details from a Gmail/email → fills form → saves.
    Creates a PENDING_REVIEW order ready for staff confirmation.
    """
    from models.order import Order, OrderChannel, OrderItem, OrderStatus
    from datetime import datetime

    data = request.get_json()

    delivery_date = None
    raw_time = data.get("delivery_time_raw", "").strip()
    if raw_time:
        try:
            delivery_date = datetime.fromisoformat(raw_time)
        except ValueError:
            pass

    items = []
    for i, item_data in enumerate(data.get("items", [])):
        items.append(OrderItem(
            sku=item_data.get("sku", f"EM-{i+1:03d}"),
            name=item_data["name"],
            qty=int(item_data.get("qty", 1)),
            unit_price=float(item_data.get("unit_price", 0.0)),
        ))

    order = Order(
        channel=OrderChannel.EMAIL,
        status=OrderStatus.PENDING_REVIEW,
        client_name=data.get("client_name", ""),
        client_contact=data.get("client_contact", ""),
        items=items,
        delivery_date=delivery_date,
        delivery_address=data.get("delivery_address", ""),
        special_instructions=data.get("special_instructions", ""),
        raw_input=f"[Email Manual] {data.get('client_name','')} <{data.get('client_contact','')}> | Delivery: {raw_time}",
        ai_confidence=1.0,
        confirmed_by="pending_staff",
    )

    store.save(order)
    alerts.notify_new_order(order)
    return jsonify(order.to_dict()), 201


@app.route("/api/intake/website", methods=["POST"])
def intake_website():
    data = request.get_json()
    order = website_channel.intake(data=data)
    return jsonify(order.to_dict()), 201


# ── Meta endpoints ────────────────────────────────────────────────────────
@app.route("/api/stats")
def get_stats():
    return jsonify(store.stats())


@app.route("/api/alerts")
def get_alerts():
    return jsonify(alerts.ALERT_LOG)


@app.route("/api/demo/seed", methods=["POST"])
def seed():
    seed_demo_orders()
    return jsonify({"ok": True, "count": len(store.all())})


# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    from services.alerts import start_watchdog
    start_watchdog(interval_seconds=30)  # Check every 30s in dev
    print("\n🍱 Baron Kitchen OMS starting...")
    print("📊 Admin Dashboard  → http://localhost:5000")
    print("🛒 Customer Portal  → http://localhost:5000/order\n")
    app.run(debug=True, port=5000, use_reloader=False)
