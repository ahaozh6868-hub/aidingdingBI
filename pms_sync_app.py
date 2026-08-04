#!/usr/bin/env python3
"""
PMS → AI表格 同步可视化前端
启动后在本地起一个Web服务，浏览器打开即可输入token并查看同步结果

用法: python3 pms_sync_app.py [port]
默认端口: 8080
"""
import http.server, json, subprocess, sys, os, datetime, threading

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SYNC_SCRIPT = os.path.join(SCRIPT_DIR, "pms_sync.py")

HTML_PAGE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PMS → AI表格 同步控制台</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:'PingFang SC','Microsoft YaHei',sans-serif; background:#0f1117; color:#e0e0e0; min-height:100vh; }
  .header { background:linear-gradient(135deg,#1a1a2e,#16213e); padding:24px 32px; border-bottom:1px solid #333; }
  .header h1 { font-size:22px; color:#fff; }
  .header .sub { font-size:13px; color:#888; margin-top:4px; }
  .container { max-width:900px; margin:0 auto; padding:32px 20px; }
  .card { background:#1a1a2e; border:1px solid #333; border-radius:12px; padding:24px; margin-bottom:20px; }
  .card h2 { font-size:16px; color:#888; margin-bottom:16px; text-transform:uppercase; letter-spacing:1px; }
  .input-group { display:flex; gap:12px; margin-bottom:16px; }
  .input-group input[type=text] { flex:1; background:#0f1117; border:1px solid #444; border-radius:8px; padding:12px 16px; color:#fff; font-size:14px; }
  .input-group input[type=text]:focus { border-color:#e74c3c; outline:none; }
  .btn { padding:12px 24px; border:none; border-radius:8px; font-size:14px; cursor:pointer; font-weight:600; transition:all .2s; }
  .btn-primary { background:#e74c3c; color:#fff; }
  .btn-primary:hover { background:#c0392b; }
  .btn-secondary { background:#2d2d44; color:#aaa; }
  .btn-secondary:hover { background:#3d3d54; }
  .btn:disabled { opacity:0.5; cursor:not-allowed; }
  .mode-group { display:flex; gap:12px; margin-bottom:16px; }
  .mode-group label { display:flex; align-items:center; gap:6px; cursor:pointer; font-size:14px; }
  .stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:12px; margin:16px 0; }
  .stat-card { background:#0f1117; border:1px solid #333; border-radius:8px; padding:16px; text-align:center; }
  .stat-card .num { font-size:28px; font-weight:bold; }
  .stat-card .label { font-size:12px; color:#888; margin-top:4px; }
  .stat-card.new .num { color:#27ae60; }
  .stat-card.updated .num { color:#3498db; }
  .stat-card.skipped .num { color:#f39c12; }
  .log { background:#0a0a0f; border:1px solid #222; border-radius:8px; padding:16px; font-family:monospace; font-size:13px; line-height:1.6; max-height:400px; overflow-y:auto; white-space:pre-wrap; }
  .log .info { color:#aaa; }
  .log .success { color:#27ae60; }
  .log .warn { color:#f39c12; }
  .log .error { color:#e74c3c; }
  .log .header-line { color:#fff; font-weight:bold; }
  .spinner { display:inline-block; width:16px; height:16px; border:2px solid #444; border-top:2px solid #e74c3c; border-radius:50%; animation:spin 1s linear infinite; }
  @keyframes spin { to { transform:rotate(360deg); } }
  .status-badge { display:inline-block; padding:4px 12px; border-radius:4px; font-size:12px; font-weight:600; }
  .status-idle { background:#2d2d44; color:#888; }
  .status-running { background:#1a3a5c; color:#3498db; }
  .status-done { background:#1a3c2a; color:#27ae60; }
  .status-error { background:#3c1a1a; color:#e74c3c; }
</style>
</head>
<body>
<div class="header">
  <h1>PMS → AI表格 同步控制台</h1>
  <div class="sub">阿拉善一期基地 (baseId=152) | 钉钉AI表格: 商品销售分析表</div>
</div>
<div class="container">
  <div class="card">
    <h2>同步配置</h2>
    <div class="input-group">
      <input type="text" id="token" placeholder="粘贴 PMS Bearer token (如: Bearer eyJhbGci...)" />
    </div>
    <div class="mode-group">
      <label><input type="radio" name="mode" value="incremental" checked> 增量同步（昨天数据）</label>
      <label><input type="radio" name="mode" value="full"> 全量同步（全部数据）</label>
      <label><input type="checkbox" id="dryrun"> 仅检查（不写入）</label>
    </div>
    <button class="btn btn-primary" id="syncBtn" onclick="startSync()">开始同步</button>
    <span id="status" class="status-badge status-idle">待机</span>
  </div>
  <div id="resultArea" style="display:none;">
    <div class="card">
      <h2>同步结果</h2>
      <div id="stats" class="stats"></div>
    </div>
    <div class="card">
      <h2>执行日志</h2>
      <div id="log" class="log"></div>
    </div>
  </div>
</div>
<script>
async function startSync() {
  const token = document.getElementById('token').value.trim();
  if (!token) { alert('请输入PMS token'); return; }
  const mode = document.querySelector('input[name=mode]:checked').value;
  const dryrun = document.getElementById('dryrun').checked;
  const btn = document.getElementById('syncBtn');
  const status = document.getElementById('status');
  btn.disabled = true;
  status.className = 'status-badge status-running';
  status.innerHTML = '<span class="spinner"></span> 同步中...';
  document.getElementById('resultArea').style.display = 'block';
  const logEl = document.getElementById('log');
  const statsEl = document.getElementById('stats');
  logEl.innerHTML = '<span class="info">正在启动同步...</span>';
  statsEl.innerHTML = '';
  try {
    const params = new URLSearchParams({ token, mode });
    if (dryrun) params.set('dryrun', '1');
    const resp = await fetch('/api/sync', { method:'POST', body: params });
    const data = await resp.json();
    if (data.error) {
      logEl.innerHTML += '\\n<span class="error">错误: ' + data.error + '</span>';
      status.className = 'status-badge status-error';
      status.textContent = '失败';
    } else {
      // Render stats
      let statsHtml = '';
      let totalNew = 0, totalUpd = 0, totalSkip = 0;
      for (const [name, r] of Object.entries(data.results || {})) {
        const n = r.new || 0, u = r.updated || 0, s = r.skipped ? 1 : 0;
        totalNew += n; totalUpd += u; totalSkip += s;
        statsHtml += `<div class="stat-card ${s?'skipped':''}"><div class="num">${s?'-':n+'/'+u}</div><div class="label">${name}</div></div>`;
      }
      statsHtml = `<div class="stat-card new"><div class="num">${totalNew}</div><div class="label">总新增</div></div>` +
                  `<div class="stat-card updated"><div class="num">${totalUpd}</div><div class="label">总更新</div></div>` +
                  statsHtml;
      statsEl.innerHTML = statsHtml;
      // Render log
      logEl.innerHTML = (data.log || '').split('\\n').map(line => {
        if (line.includes('===')) return '<span class="header-line">' + line + '</span>';
        if (line.includes('⚠')) return '<span class="warn">' + line + '</span>';
        if (line.includes('错误') || line.includes('Error')) return '<span class="error">' + line + '</span>';
        return '<span class="info">' + line + '</span>';
      }).join('\\n');
      status.className = 'status-badge status-done';
      status.textContent = '完成';
    }
  } catch(e) {
    logEl.innerHTML += '\\n<span class="error">请求失败: ' + e.message + '</span>';
    status.className = 'status-badge status-error';
    status.textContent = '失败';
  }
  btn.disabled = false;
}
</script>
</body>
</html>"""

class SyncHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default logging

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/sync":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            from urllib.parse import parse_qs
            params = parse_qs(body)
            token = params.get("token", [""])[0]
            mode = params.get("mode", ["incremental"])[0]
            dryrun = params.get("dryrun", [""])[0] == "1"

            if not token:
                self.send_json({"error": "缺少token参数"})
                return

            # Build command
            cmd = ["python3", SYNC_SCRIPT, "--token", token]
            if mode == "full":
                cmd.append("--full")
            if dryrun:
                cmd.append("--dry-run")

            # Run sync
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                log = result.stdout
                # Try to parse the JSON summary at the end
                summary = {}
                try:
                    # Find the JSON block (last { to end)
                    json_start = log.rfind("\n{")
                    if json_start >= 0:
                        summary = json.loads(log[json_start+1:])
                except:
                    pass
                self.send_json({"log": log, "results": summary.get("results", {}), "mode": summary.get("mode", mode)})
            except subprocess.TimeoutExpired:
                self.send_json({"error": "同步超时（超过10分钟）"})
            except Exception as e:
                self.send_json({"error": str(e)})
        else:
            self.send_response(404)
            self.end_headers()

    def send_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", PORT), SyncHandler)
    print(f"PMS同步控制台已启动: http://localhost:{PORT}")
    print(f"同步脚本: {SYNC_SCRIPT}")
    print("按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
