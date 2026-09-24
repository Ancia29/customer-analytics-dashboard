const $ = s => document.querySelector(s);
const fmt = n => (n == null ? '-' : Number(n).toLocaleString(undefined, {maximumFractionDigits: 2}));
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => '&#' + c.charCodeAt(0) + ';');
const say = (t, bad) => { $('#msg').textContent = t; $('#msg').className = bad ? 'err' : 'ok'; };
const COLORS = ['#4f7cff', '#22c1a0', '#f5b942', '#ef6f6c', '#9b6bff', '#8895a7'];
const charts = {};
const st = {page: 1, pages: 1, sort: 'total_revenue', order: 'desc'};
const COLS = [['customer_id', 'Customer ID'], ['total_orders', 'Orders'], ['total_revenue', 'Revenue'], ['recency', 'Recency'],
  ['frequency', 'Frequency'], ['monetary_value', 'Monetary'], ['segment', 'Segment'], ['predicted_clv', 'Predicted CLV']];

async function api(path, opts) {
  const res = await fetch('/api' + path, opts);
  const json = await res.json().catch(() => ({error: 'Server returned an invalid response'}));
  if (!json.success) throw new Error(json.error);
  return json.data;
}

function draw(id, type, labels, values, label) {
  charts[id]?.destroy();
  const multi = type === 'doughnut';
  charts[id] = new Chart($('#' + id), {type, data: {labels, datasets: [{label, data: values,
    backgroundColor: multi ? COLORS : '#4f7cff', borderColor: multi ? '#fff' : '#4f7cff'}]},
    options: {plugins: {legend: {display: multi}}}});
}

async function loadDashboard() {
  try {
    const [s, trend, seg, top, clv] = await Promise.all([api('/dashboard-summary'), api('/revenue-trend'),
      api('/segments'), api('/top-customers'), api('/clv')]);
    const cards = [['Total Revenue', s.total_revenue], ['Customers', s.total_customers], ['Orders', s.total_orders],
      ['Avg Order Value', s.avg_order_value], ['Repeat Customer Rate', s.repeat_customer_rate + '%'], ['Avg Predicted CLV', s.avg_clv]];
    $('#kpis').innerHTML = cards.map(([a, b]) => `<div class="card kpi"><span>${a}</span><b>${typeof b === 'string' ? b : fmt(b)}</b></div>`).join('');
    draw('c1', 'line', trend.map(x => x.month), trend.map(x => x.revenue), 'Revenue');
    draw('c2', 'doughnut', seg.map(x => x.segment), seg.map(x => x.customers), 'Customers');
    draw('c3', 'bar', top.map(x => x.customer_id), top.map(x => x.total_revenue), 'Revenue');
    draw('c4', 'bar', clv.map(x => x.range), clv.map(x => x.customers), 'Customers');
    $('#seg').innerHTML = '<option value="">All segments</option>' + seg.map(x => `<option>${esc(x.segment)}</option>`).join('');
    loadTable();
  } catch (e) { say(e.message, true); }
}

async function loadTable() {
  try {
    const q = new URLSearchParams({page: st.page, per_page: 10, sort: st.sort, order: st.order,
      search: $('#search').value, segment: $('#seg').value});
    const d = await api('/customers?' + q);
    $('#thead').innerHTML = '<tr>' + COLS.map(([k, l]) => `<th data-k="${k}">${l}${st.sort === k ? (st.order === 'asc' ? ' ▲' : ' ▼') : ''}</th>`).join('') + '</tr>';
    $('#rows').innerHTML = d.customers.map(c => `<tr data-id="${esc(c.customer_id)}">` +
      COLS.map(([k]) => `<td>${k === 'customer_id' || k === 'segment' ? esc(c[k]) : fmt(c[k])}</td>`).join('') + '</tr>').join('');
    st.pages = Math.max(Math.ceil(d.total / d.per_page), 1);
    $('#pg').textContent = `Page ${d.page} of ${st.pages} (${d.total} customers)`;
  } catch (e) { say(e.message, true); }
}

async function showDetail(id) {
  try {
    const {customer: c, history} = await api('/customers/' + encodeURIComponent(id));
    $('#detail').hidden = false;
    $('#detail').innerHTML = `<h3>Customer ${esc(c.customer_id)} · ${esc(c.segment)}</h3>
      <p>Revenue ${fmt(c.total_revenue)} · Orders ${c.total_orders} · Avg order ${fmt(c.avg_order_value)} ·
      Recency ${c.recency} days · Frequency ${c.frequency} · Predicted CLV ${fmt(c.predicted_clv)}</p>
      <table><tr><th>Date</th><th>Invoice</th><th>Product</th><th>Qty</th><th>Revenue</th></tr>` +
      history.map(h => `<tr><td>${esc(h.invoice_date.slice(0, 10))}</td><td>${esc(h.invoice_no)}</td><td>${esc(h.description)}</td><td>${h.quantity}</td><td>${fmt(h.revenue)}</td></tr>`).join('') + '</table>';
    $('#detail').scrollIntoView({behavior: 'smooth'});
  } catch (e) { say(e.message, true); }
}

$('#file').onchange = () => { $('#fname').textContent = $('#file').files[0]?.name || 'Drag & drop a CSV here, or click to browse'; };
$('#up').onclick = async () => {
  const f = $('#file').files[0];
  if (!f) return say('Choose a CSV file first.', true);
  const body = new FormData(); body.append('file', f);
  $('#up').disabled = true; say('Uploading and analysing…');
  try {
    const r = await api('/upload', {method: 'POST', body});
    say(`Done: ${r.valid_rows} valid rows, ${r.rows_removed} removed, ${r.customers} customers.`);
    await loadDashboard();
  } catch (e) { say(e.message, true); } finally { $('#up').disabled = false; }
};
$('#thead').onclick = e => { const k = e.target.dataset.k; if (!k) return;
  st.order = st.sort === k && st.order === 'desc' ? 'asc' : 'desc'; st.sort = k; st.page = 1; loadTable(); };
$('#rows').onclick = e => { const tr = e.target.closest('tr'); if (tr) showDetail(tr.dataset.id); };
$('#search').oninput = $('#seg').onchange = () => { st.page = 1; loadTable(); };
$('#prev').onclick = () => { if (st.page > 1) { st.page--; loadTable(); } };
$('#next').onclick = () => { if (st.page < st.pages) { st.page++; loadTable(); } };
loadDashboard();
