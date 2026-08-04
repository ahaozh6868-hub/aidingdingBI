#!/usr/bin/env python3
"""
PMS → AI钉钉表格 增量同步脚本 v3
支持：token参数化、增量同步（昨天数据）、去重检查、详细日志

用法:
  python3 pms_sync.py --token "Bearer xxx"           # 增量同步昨天数据
  python3 pms_sync.py --token "Bearer xxx" --full     # 全量同步
  python3 pms_sync.py --token "Bearer xxx" --dry-run   # 只检查不写入
"""
import argparse, json, subprocess, urllib.request, urllib.error, datetime, sys, os, ssl, certifi
import logging, logging.handlers, traceback, time, io

# Windows 控制台编码修复：强制 stdout/stderr 用 utf-8，避免 → 等字符在 cp1252 下崩溃
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ====== 项目根目录（日志/脚本所在目录） ======
def _get_app_dir():
    """获取应用根目录：exe 所在目录（PyInstaller）或脚本目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

SCRIPT_DIR = _get_app_dir()

# ====== 日志系统 ======
class DualLogger:
    """双通道日志：控制台 INFO 级别 + 文件 DEBUG 级别，带时间戳文件名"""
    def __init__(self):
        self.start_time = time.time()
        self.error_count = 0
        self.warn_count = 0
        self.stage_start = 0

        # 确保 logs 目录存在
        log_dir = os.path.join(SCRIPT_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(log_dir, f"sync_{timestamp}.log")

        self.logger = logging.getLogger("pms_sync")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()

        # 文件 handler：DEBUG 级别，记录全部细节
        fh = logging.FileHandler(self.log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s.%(msecs)03d [%(levelname)-5s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        self.logger.addHandler(fh)

        # 控制台 handler：INFO 级别，简洁输出
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(ch)

    def debug(self, msg, *args): self.logger.debug(msg, *args)
    def info(self, msg, *args): self.logger.info(msg, *args)
    def warning(self, msg, *args):
        self.warn_count += 1
        self.logger.warning(msg, *args)
    def error(self, msg, *args):
        self.error_count += 1
        self.logger.error(msg, *args)

    def exception(self, msg, *args):
        """记录异常 + 完整堆栈"""
        self.error_count += 1
        buf = io.StringIO()
        traceback.print_exc(file=buf)
        self.logger.error(f"{msg}\n{buf.getvalue().rstrip()}", *args)

    def stage_begin(self, name):
        self.stage_start = time.time()
        self.info(f"  ── [{name}] 开始...")

    def stage_end(self, name, extra=""):
        elapsed = time.time() - self.stage_start
        tail = f" | {extra}" if extra else ""
        self.info(f"  ── [{name}] 完成 (耗时 {elapsed:.1f}s){tail}")

    def lifecycle(self, msg):
        self.info(f"◆ {msg}")
        self.debug(f"[LIFECYCLE] {msg}")

    def hr(self, char="─", width=60):
        self.info(char * width)

    def summary(self, extra_errors=0):
        total_elapsed = time.time() - self.start_time
        total_err = self.error_count + extra_errors
        status = "❌ 失败" if total_err > 0 else "✅ 成功"
        self.hr("=")
        self.info(f"  执行结果: {status}")
        self.info(f"  总耗时: {total_elapsed:.1f}s")
        self.info(f"  警告: {self.warn_count}  错误: {total_err}")
        self.info(f"  日志文件: {self.log_file}")
        self.hr("=")
        return total_err

# 全局日志实例
log = DualLogger()

# ====== 配置 ======
PMS_BASE = "https://pms.cosmos-ag.com"
BASE_ID_PMS = 152

AI_BASE_ID = "vNG4YZ7Jnlp30gY2HNoGqLr9W2LD0oRE"
AI_TABLES = {
    "order_main": "89RjlI0",
    "order_detail": "2Em2ubU",
    "material": "QJwb6MT",
    "warehouse": "sTwFnIX",
    "inventory": "wOSrNZM",
}

# Field mappings (same as v1)
MATERIAL_FIELDS = {
    "name": "8rcs8uaxpcaxnoidgth0o", "num": "i8968bt2xp37jf6ks263a",
    "variety": "1i0b0mkfxmk62w2ow59jp", "unit": "l95pbs3q856hpmm9265xe",
    "saleUnit": "5b8dexvv0qckdaxd0ys9g", "grade": "pukwhbfvmewntnifkdkv2",
    "netWeight": "srrx6u6e32zrex885ez9v", "matGroup": "rrmnapbokbf9duhtz5a5u",
    "status": "au60oofzejjdnfldp2i43",
}
WAREHOUSE_FIELDS = {
    "code": "uof2j4mvfzohv5ohymore", "name": "jotuo3h0m0mv1rh75bqip",
    "type": "9xqqm63t147hnyyudg6v1", "matType": "nb8naf0ycz7t3cvy9o6ji",
}
ORDER_FIELDS = {
    "orderId": "grsx5v1hsm0jqrio1n0b9", "orderNumber": "ns6pnsovm5h06ii5ex9i2",
    "customer": "i2ksuztm4hb0go01qkwo8", "customerNum": "nmd2f7m2eksio1bb9eicn",
    "purpose": "qnjh1ifgavn5frtq2ubnp", "planDate": "ha3c18bt380ymx2wq6kti",
    "latestDate": "3h0kntat8p9nf0bwe97gj", "takeStatus": "7oi6wfjb87h78uoy8mi1s",
    "collectStatus": "alzahmywi33zxyi2dbi9t", "status": "hdoqicwplrv8ffvminwcw",
    "cancelReason": "8h8s59hdgyzb2ucy90djs", "remark": "mg2x9fsiwvstxub09xjal",
    "totalPlan": "1r0i1gv8dhnht7i5w3kg2", "totalDelivered": "18l9bsc6m7iexh0gldvfz",
    "totalTake": "1v5ptqfixasoapl4u5kyz", "orderPrice": "mgo2qeiq0qed3c2et093c",
    "overOrderPrice": "x28a08jbo3o4ts7nzctv8", "collectAmount": "qcbtn6u0qtr4d1d5lmhi6",
    "detailCount": "jvjcza9igs695avbir9dn",
}
DETAIL_FIELDS = {
    "orderNumber": "ts71955hgzohfxehzzwaq", "customer": "gxxs7278qy3ek1fnas5mh",
    "detailId": "61udcyteq9mdib9dyak5p", "matNum": "cgns0m3asacmgafndtb0d",
    "matName": "8gr6wyhwnlg0fln7oi8m1", "planDelivery": "i4elylq2ajg580ngz8nqu",
    "actualDelivery": "hjdp49wkboa7cn4mmhmtz", "unit": "qnnag4icqh6f5cbu4guyx",
    "unitPrice": "k6wyodstrzsizywdtwbdb", "orderPrice": "uotabj0yyvm7yjmsip4ek",
    "overAmount": "np52g72dfiryc4n21mq3j", "waitDelivery": "lg4jgpchwivkoszsh96z0",
    "takeNum": "n3a2bnmo32qm3bmhg1vbj", "takeDamage": "8ehrr8lk81c3bl624ys3n",
    "lossRemark": "r9sumnhfvlgoz15mxyzoy", "detailRemark": "pb671l4k0cpanlq9mf3ph",
    "convertPlan": "kl5ea3zx96c6mybjcjipk", "convertActual": "x7l9lx6ngipltngh6yvnx",
    "convertTake": "v0f5u1eo479oyquee2q9q",
}
INVENTORY_FIELDS = {
    "invId": "vezf294rv2kaaumzvnvrr", "recordNum": "oxh5k1mxdz4ga0lx9tikc",
    "opTime": "21g6xmhx520a6po5m0pij", "changeType": "083f874128yzur5h41sk3",
    "warehouseId": "db4vuj6tvh0ykmpallx7p", "warehouseName": "j7djj9d2fqvryudemy66t",
    "materialId": "q0xe4qewf3o2jfan88cmw", "materialName": "3omwrcf4pqix8biz4kk8e",
    "materialNum": "vyzik5brmosv3a38zkor8", "auxQty": "z0167r6ysjfhezywlxj96",
    "basicQty": "2b92hrdyhsf254sihezzr", "basicUnit": "ysbn7uceja2er4d9j45tc",
    "saleUnit": "wfapol890uu4yev7wfbe8", "qtyDesc": "0y6fsed0e75vm00c3rihe",
    "orderDetailId": "fyobumg6qllymcn65c4qd", "deliveryDate": "gzshsh7e6me59u9oxhgxg",
    "remark": "pkvrixpj38tox0qe6rjrm", "status": "1l0n513nq5iyxnsnrwe3v",
    "seqNum": "hbw80w8k0vkjh34npta6j",
}

# ====== HTTP 工具 ======
_SSL_CONTEXT = None
_DWS_PATH = "dws"  # 默认依赖 PATH, 可用 --dws-path 覆盖

def _find_dws():
    """查找 dws 可执行文件：指定路径 > 同级目录 > where命令 > npm全局目录 > PATH"""
    # 1. 显式指定路径
    if _DWS_PATH and os.path.isfile(_DWS_PATH):
        return _DWS_PATH

    # 2. exe 同级目录查找 (PyInstaller 打包 / 手动放 dws.exe 过来)
    exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    for name in ["dws.exe", "dws", "dws.cmd"]:
        candidate = os.path.join(exe_dir, name)
        if os.path.isfile(candidate):
            return candidate

    # 3. Windows: 用 where 命令查找 PATH 里的 dws（最可靠，能找到终端里的 dws）
    if sys.platform == "win32":
        try:
            result = subprocess.run(["where", "dws"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip() and os.path.isfile(l.strip())]
                # 优先选 .cmd/.exe/.bat，避免无扩展名的 shell 脚本（WinError 193）
                for pref_ext in (".cmd", ".exe", ".bat"):
                    for line in lines:
                        if line.lower().endswith(pref_ext):
                            return line
                # 若只找到无扩展名的 dws，查同目录下的 dws.cmd（npm 会同时生成）
                for line in lines:
                    d = os.path.dirname(line)
                    for name in ["dws.cmd", "dws.exe", "dws.bat"]:
                        candidate = os.path.join(d, name)
                        if os.path.isfile(candidate):
                            return candidate
                if lines:
                    return lines[0]
        except Exception:
            pass

    # 4. Windows: 探测常见 npm/node 安装目录（不依赖 PATH）
    if sys.platform == "win32":
        candidate_bases = [
            os.environ.get("APPDATA", ""),
            os.environ.get("LOCALAPPDATA", ""),
            os.environ.get("PROGRAMFILES", ""),
            os.environ.get("PROGRAMFILES(X86)", ""),
        ]
        for base in candidate_bases:
            if not base:
                continue
            # base/npm/dws.cmd 和 base/dws.cmd 都试
            for sub in ["npm", "nodejs", ""]:
                for name in ["dws.cmd", "dws.exe", "dws"]:
                    candidate = os.path.join(base, sub, name) if sub else os.path.join(base, name)
                    if os.path.isfile(candidate):
                        return candidate
        # npm prefix -g 的实际路径
        try:
            result = subprocess.run(["npm", "prefix", "-g"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                npm_prefix = result.stdout.strip()
                for name in ["dws.cmd", "dws", "dws.exe"]:
                    candidate = os.path.join(npm_prefix, name)
                    if os.path.isfile(candidate):
                        return candidate
        except Exception:
            pass

    # 5. 回退到 PATH 查找 (subprocess 会自己找)
    return _DWS_PATH

def _get_ssl_context():
    """创建 SSL 上下文，使用 certifi 证书"""
    global _SSL_CONTEXT
    if _SSL_CONTEXT is not None:
        return _SSL_CONTEXT
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
    return _SSL_CONTEXT

def _check_pms_response(data, url):
    """PMS API 有时返回 HTTP 200 但 body 里埋了错误码，需要检测"""
    if isinstance(data, dict) and data.get("code") and data["code"] != 200:
        code = data["code"]
        msg = data.get("msg", str(data))
        log.error(f"PMS 返回错误 [{url}]: code={code}, msg={msg[:200]}")
        if code == 401:
            # 降为 warning，避免与外层错误重复计数导致 error_count 虚高
            log.warning(f"  → Token 已失效或无权限，请更新 PMS token")
        return False
    return True

def pms_get(path, params=None):
    url = PMS_BASE + path
    if params:
        url += "?" + "&".join(f"{k}={v}" for k,v in params.items())
    log.debug(f"GET {url}")
    req = urllib.request.Request(url, headers={"Authorization": PMS_TOKEN})
    try:
        with urllib.request.urlopen(req, timeout=30, context=_get_ssl_context()) as resp:
            raw = resp.read()
            log.debug(f"GET {url} → HTTP {resp.status} ({len(raw)} bytes)\n--- RESPONSE BODY ---\n{raw.decode('utf-8', errors='replace')}\n--- END ---")
            data = json.loads(raw)
            _check_pms_response(data, url)
            return data
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500] if e.fp else ""
        log.error(f"GET {url} → HTTP {e.code}: {body}")
        raise
    except Exception as e:
        log.error(f"GET {url} → {type(e).__name__}: {e}")
        raise

def pms_post(path, body):
    url = PMS_BASE + path
    data = json.dumps(body).encode("utf-8")
    log.debug(f"POST {url} (body:{len(data)} bytes)\n--- REQUEST BODY ---\n{json.dumps(body, ensure_ascii=False)}\n--- END ---")
    req = urllib.request.Request(PMS_BASE + path, data=data,
        headers={"Authorization": PMS_TOKEN, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30, context=_get_ssl_context()) as resp:
            raw = resp.read()
            log.debug(f"POST {url} → HTTP {resp.status} ({len(raw)} bytes)\n--- RESPONSE BODY ---\n{raw.decode('utf-8', errors='replace')}\n--- END ---")
            data = json.loads(raw)
            _check_pms_response(data, url)
            return data
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500] if e.fp else ""
        log.error(f"POST {url} → HTTP {e.code}: {body}")
        raise
    except Exception as e:
        log.error(f"POST {url} → {type(e).__name__}: {e}")
        raise

# ====== 通用分页拉取 ======
def pms_fetch_all_post(path, body, page_size=100):
    """POST 分页拉取全部数据。
    优先用 PMS 返回的 total，total=0 或不可信时按"本页未满则停止"兜底。"""
    body["current"] = 1
    body["size"] = page_size
    resp = pms_post(path, dict(body))
    total = resp.get("total", 0)
    rows = list(resp.get("rows", []))
    first_got = len(resp.get("rows", []))
    log.debug(f"[分页POST] {path}: page=1, got={first_got}, total={total}")

    # 兜底：total 不可信时用 page_size 推断是否需要翻页
    if total <= 0 and first_got >= page_size:
        total = first_got + 1  # 强制进循环
        log.debug(f"[分页POST] {path}: total={total} but got {first_got}, fallback to size-based pagination")

    page = 2
    while len(rows) < total:
        body["current"] = page
        resp = pms_post(path, dict(body))
        new_rows = resp.get("rows", [])
        if not new_rows:
            log.warning(f"[分页POST] {path}: 第{page}页返回空, 停止翻页")
            break
        rows.extend(new_rows)
        log.debug(f"[分页POST] {path}: page={page}, got={len(new_rows)}, accumulated={len(rows)}/{total}")
        # 兜底：本页不满 page_size 且 total 不可信(人为值)，说明到最后一页了
        if first_got >= page_size and len(new_rows) < page_size and total != resp.get("total", 0):
            break
        page += 1
    return rows

def pms_fetch_all_get(path, params, page_size=100):
    """GET 分页拉取全部数据。
    优先用 PMS 返回的 total，total=0 或不可信时按"本页未满则停止"兜底。"""
    params["current"] = 1
    params["size"] = page_size
    resp = pms_get(path, dict(params))
    total = resp.get("total", 0)
    rows = list(resp.get("rows", []))
    first_got = len(resp.get("rows", []))
    log.debug(f"[分页GET] {path}: page=1, got={first_got}, total={total}")

    # 兜底：total 不可信时用 page_size 推断是否需要翻页
    if total <= 0 and first_got >= page_size:
        total = first_got + 1  # 强制进循环
        log.debug(f"[分页GET] {path}: total={total} but got {first_got}, fallback to size-based pagination")

    page = 2
    while len(rows) < total:
        params["current"] = page
        resp = pms_get(path, dict(params))
        new_rows = resp.get("rows", [])
        if not new_rows:
            log.warning(f"[分页GET] {path}: 第{page}页返回空, 停止翻页")
            break
        rows.extend(new_rows)
        log.debug(f"[分页GET] {path}: page={page}, got={len(new_rows)}, accumulated={len(rows)}/{total}")
        # 兜底：本页不满 page_size 且 total 不可信(人为值)，说明到最后一页了
        if first_got >= page_size and len(new_rows) < page_size and total != resp.get("total", 0):
            break
        page += 1
    return rows

def dws_cmd(args):
    dws_bin = _find_dws()
    dws_bin_quoted = f'"{dws_bin}"' if " " in dws_bin and not dws_bin.startswith('"') else dws_bin
    log.debug(f"DWS: {dws_bin} {' '.join(args[:6])}...")

    # Windows: 直接用 shell=True，最稳定，不会被 cmd/node 路径间歇性问题影响
    if sys.platform == "win32":
        cmd_str = f"{dws_bin_quoted} {' '.join(args)}"
        try:
            result = subprocess.run(cmd_str, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace',
                                    timeout=120, shell=True)
        except FileNotFoundError:
            log.error(f"DWS 执行失败: {dws_bin} (shell=True also failed)")
            log.error("请确保 dws CLI 已正确安装: npm install -g --allow-scripts=dingtalk-workspace-cli dingtalk-workspace-cli")
            return {"success": False, "error": f"dws not found: {dws_bin}"}
        except subprocess.TimeoutExpired:
            log.error(f"DWS 命令超时 (>120s): {' '.join(args[:6])}")
            return {"success": False, "error": "timeout"}
    else:
        try:
            result = subprocess.run([dws_bin] + args, capture_output=True,
                                    text=True, timeout=120)
        except FileNotFoundError:
            log.error(f"DWS 执行失败: 找不到 {dws_bin}")
            return {"success": False, "error": f"dws not found: {dws_bin}"}
        except subprocess.TimeoutExpired:
            log.error(f"DWS 命令超时 (>120s): {' '.join(args[:6])}")
            return {"success": False, "error": "timeout"}

    if result.returncode != 0:
        log.warning(f"DWS 返回非零: {result.returncode}")
        log.warning(f"  stderr: {(result.stderr or '')[:500]}")
        log.debug(f"  stdout: {(result.stdout or '')[:500]}")
        return {"success": False, "error": (result.stderr or '')[:500]}
    if not result.stdout:
        log.warning(f"DWS 无输出 (returncode=0 但 stdout 为空)")
        log.warning(f"  stderr: {(result.stderr or '')[:500]}")
        return {"success": False, "error": "dws 无输出（可能未登录或内部错误）"}
    try:
        parsed = json.loads(result.stdout)
        log.debug(f"DWS 响应: {json.dumps(parsed, ensure_ascii=False)[:1000]}")
        return parsed
    except json.JSONDecodeError:
        log.warning(f"DWS 输出非 JSON (len={len(result.stdout)}): {result.stdout[:500]}")
        return {"success": False, "error": result.stdout[:500]}

# ====== 去重查询（分页） ======
def query_existing_ids(table_key, field_id):
    """查询已有记录，返回 key→recordId 的映射（自动分页）。
    返回 None 表示查询完全失败（权限/认证问题），不应继续写入。
    返回 {} 表示查询成功但无记录。"""
    table_id = AI_TABLES[table_key]
    lookup = {}
    cursor = None
    page = 0
    first_page_failed = False
    while True:
        page += 1
        args = ["aitable","record","query","--base-id",AI_BASE_ID,"--table-id",table_id,"--format","json"]
        if cursor:
            args.extend(["--cursor", cursor])
        resp = dws_cmd(args)
        if not resp.get("success"):
            err_msg = resp.get('error','')[:200]
            log.warning(f"查询已有记录失败 [{table_key}] p{page}: {err_msg}")
            if page == 1:
                # 首页失败 = 没有读取权限或表不存在，标记为不可操作
                first_page_failed = True
                if "ResourceNotFound" in err_msg:
                    log.error(f"  → [{table_key}] 表不存在或当前钉钉账号无访问权限！")
                    log.error(f"  → 请确认账号已加入 AI表格 {AI_BASE_ID} 的协作者列表")
                elif "access token" in err_msg.lower():
                    log.error(f"  → [{table_key}] dws 未登录，请执行: dws auth login")
            break
        data = resp.get("data",{})
        records = data.get("records",[])
        for rec in records:
            cells = rec.get("cells",{})
            val = cells.get(field_id)
            if isinstance(val, list) and val:
                item = val[0]
                val = item.get("text") or item.get("name") or str(item) if isinstance(item, dict) else str(item)
            elif isinstance(val, dict):
                val = val.get("text") or val.get("name") or str(val)
            if val is not None and str(val).strip():
                lookup[str(val).strip()] = rec.get("recordId")
        cursor = data.get("nextCursor")
        if not cursor:
            break
    if first_page_failed:
        return None  # 完全失败，禁止写入
    log.debug(f"query_existing_ids [{table_key}]: {len(lookup)} 条 ({page} 页)")
    return lookup

# ====== 数据转换 ======
def parse_num(s):
    """解析字符串数字（处理千位逗号）"""
    if s is None: return 0
    if isinstance(s, (int, float)): return float(s)
    s = str(s).replace(",", "").split()[0] if str(s).split() else "0"
    try: return float(s) if s else 0
    except: return 0

def transform_material(m):
    units = m.get("unit") or []
    sale = m.get("saleUint") or {}
    group = m.get("group") or {}
    custom = m.get("customAttMap") or {}
    crop = m.get("cropCategory") or {}
    return {
        "name": m.get("materialName") or "", "num": m.get("materialNum") or "",
        "variety": crop.get("name") or "",
        "unit": units[0].get("val","") if units and isinstance(units[0],dict) else (str(units[0]) if units else ""),
        "saleUnit": sale.get("val","") if isinstance(sale,dict) else "",
        "grade": custom.get("103","") if isinstance(custom,dict) else "",
        "netWeight": custom.get("107","") if isinstance(custom,dict) else "",
        "matGroup": group.get("name","") if isinstance(group,dict) else "",
        "status": "启用" if m.get("status")==1 else "停用",
    }

def transform_warehouse(w):
    return {"code": w.get("code") or "", "name": w.get("name") or "",
            "type": str(w.get("type","")), "matType": str(w.get("materialType",""))}

def transform_order(o):
    cust = o.get("customerInfo") or {}
    purpose = o.get("purposeVo") or {}
    pms_status = o.get("status")
    take = o.get("takeStatus", 0)
    # 订单状态
    if pms_status == -1: order_status = "已取消"
    elif take == 0: order_status = "未收货"
    elif take == 10: order_status = "部分收货"
    elif take == 11: order_status = "已收货"
    else: order_status = "未收货"
    # 发货状态（基于实际发货量）
    td_num = parse_num(o.get("totalDelivered"))
    tp_num = parse_num(o.get("totalPlanDelivery"))
    if td_num > 0:
        take_text = "部分发货" if (tp_num > 0 and td_num < tp_num) else "已发货"
    else:
        take_text = "未发货"
    # 收款状态
    cs = o.get("collectStatus", 0)
    collect_text = {0:"未收款",10:"部分收款",11:"已收款"}.get(cs, str(cs))
    details = o.get("details") or []
    pd = o.get("planDeliveryDate") or ""
    if pd and "T" not in pd: pd += "T00:00:00+08:00"
    ld = o.get("latestDeliveryDate") or ""
    if ld and "T" not in ld: ld += "T00:00:00+08:00"
    return {
        "orderId": o.get("orderId"), "orderNumber": o.get("orderNumber") or "",
        "customer": cust.get("name") or "", "customerNum": cust.get("number") or "",
        "purpose": purpose.get("purpose") or "" if isinstance(purpose,dict) else "",
        "planDate": pd or None, "latestDate": ld or None,
        "takeStatus": take_text, "collectStatus": collect_text,
        "status": order_status, "cancelReason": o.get("cancelReason") or "",
        "remark": o.get("remark") or "", "totalPlan": o.get("totalPlanDelivery") or "",
        "totalDelivered": td_num, "totalTake": o.get("totalTake") or "",
        "orderPrice": o.get("orderPrice"), "overOrderPrice": o.get("overOrderPrice"),
        "collectAmount": o.get("collectAmount"), "detailCount": len(details),
    }

def transform_detail(o, d):
    cust = o.get("customerInfo") or {}
    mat = d.get("materialVo") or {}
    uv = d.get("unitVo") or {}
    def conv(c):
        if not c or not isinstance(c, dict): return ""
        r = c.get("right"); m = c.get("middle","")
        return f"{r}{m}" if r is not None else ""
    return {
        "orderNumber": o.get("orderNumber") or "", "customer": cust.get("name") or "",
        "detailId": d.get("id"), "matNum": mat.get("materialNum") or "",
        "matName": mat.get("materialName") or "",
        "planDelivery": d.get("planDelivery"), "actualDelivery": d.get("overDelivery"),
        "unit": uv.get("val") or "" if isinstance(uv,dict) else "",
        "unitPrice": d.get("unitPrice"), "orderPrice": d.get("orderPrice"),
        "overAmount": d.get("overOrderPrice"), "waitDelivery": d.get("waitDelivery"),
        "takeNum": d.get("takeNumber"), "takeDamage": d.get("takeDamage"),
        "lossRemark": d.get("takeDamageRemark") or None,
        "detailRemark": d.get("detailRemark") or "",
        "convertPlan": conv(d.get("convertPlanDelivery")),
        "convertActual": conv(d.get("convertOverDelivery")),
        "convertTake": conv(d.get("convertTakeNumber")),
    }

def transform_inventory(i):
    CT_MAP = {1:"入仓加",2:"入库增",3:"入库减",4:"移库增",5:"移库减",
              6:"调整增",7:"调整减",8:"出仓减",9:"出仓减(发货)",
              10:"移仓减",11:"移仓增",12:"退库增"}
    ct = i.get("changeType")
    ot = i.get("operationTime") or ""
    if ot: ot = ot.replace(" ","T"); ot = ot if ("+" in ot or "Z" in ot) else ot+"+08:00"
    dd = i.get("orderDeliveryDate") or ""
    if dd: dd = dd.replace(" ","T"); dd = dd if ("+" in dd or "Z" in dd) else dd+"+08:00"
    return {
        "invId": i.get("inventoryId"), "recordNum": i.get("recordNo") or "",
        "opTime": ot, "changeType": CT_MAP.get(ct, str(ct) if ct else ""),
        "warehouseId": i.get("warehouseId"), "warehouseName": i.get("warehouseName") or "",
        "materialId": i.get("materialId"), "materialName": i.get("materialName") or "",
        "materialNum": i.get("materialNum") or "",
        "auxQty": i.get("amount"), "basicQty": i.get("basicAmount"),
        "basicUnit": i.get("unit") or "", "saleUnit": i.get("saleUnit") or "",
        "qtyDesc": i.get("amountDesc") or "",
        "orderDetailId": i.get("orderDetailId") if i.get("orderDetailId") and i.get("orderDetailId")>0 else None,
        "deliveryDate": dd or None, "remark": i.get("remark") or "",
        "status": {0:"正常", -1:"废弃"}.get(i.get("status"), str(i.get("status",""))), "seqNum": i.get("id"),
    }

# ====== 同步逻辑 ======
def sync_table(table_key, fields, records, key_field, dry_run=False, full_mode=False, skip_update=False):
    """同步单表：去重检查 + 新增/更新 + (full_mode时)删除PMS不存在的孤儿记录
    skip_update=True: 已有记录直接跳过，不更新也不报错（用于库存等不可变数据）
    Returns None 表示因权限/认证问题无法操作，调用方应跳过
    """
    key_fid = fields[key_field]
    existing = query_existing_ids(table_key, key_fid)

    # 查询完全失败 → 禁止写入，防止因去重失效而重复创建
    if existing is None:
        log.error(f"  → [{table_key}] 无法查询已有记录，跳过同步（防止重复写入）")
        return None

    # PMS 侧的去重 key 集合
    pms_keys = set()
    to_create, to_update, skipped = [], [], 0
    for item in records:
        cells = {fid: item[k] for k, fid in fields.items() if item.get(k) is not None}
        kv = str(item.get(key_field, ""))
        pms_keys.add(kv)
        if kv in existing:
            if skip_update:
                skipped += 1
            else:
                to_update.append({"recordId": existing[kv], "cells": cells})
        else:
            to_create.append({"cells": cells})

    # 全量模式：找出 AI表格中有但 PMS 没有的孤儿记录，删除
    to_delete = []
    if full_mode:
        for key, record_id in existing.items():
            if key not in pms_keys:
                to_delete.append(record_id)

    result = {"table": table_key, "existing": len(existing),
               "new": len(to_create), "updated": len(to_update),
               "skipped": skipped if skip_update else 0,
               "deleted": len(to_delete),
               "create_ok": 0, "create_fail": 0,
               "update_ok": 0, "update_fail": 0,
               "delete_ok": 0, "delete_fail": 0}
    if dry_run:
        result["dry_run"] = True
        return result

    # Create (batch 100)
    for i in range(0, len(to_create), 100):
        batch = to_create[i:i+100]
        resp = dws_cmd(["aitable","record","create","--base-id",AI_BASE_ID,"--table-id",AI_TABLES[table_key],
                 "--records", json.dumps(batch, ensure_ascii=False), "--format","json"])
        if resp.get("success"):
            result["create_ok"] += len(batch)
        else:
            result["create_fail"] += len(batch)
            log.warning(f"  [{table_key}] CREATE 批次失败 ({len(batch)}条): {resp.get('error','')[:100]}")

    # Update (batch 100)
    for i in range(0, len(to_update), 100):
        batch = to_update[i:i+100]
        resp = dws_cmd(["aitable","record","update","--base-id",AI_BASE_ID,"--table-id",AI_TABLES[table_key],
                 "--records", json.dumps(batch, ensure_ascii=False), "--format","json"])
        if resp.get("success"):
            result["update_ok"] += len(batch)
        else:
            result["update_fail"] += len(batch)
            log.warning(f"  [{table_key}] UPDATE 批次失败 ({len(batch)}条): {resp.get('error','')[:100]}")

    # Delete orphans（批量删除，最多100条/批；--yes 跳过交互确认，否则 dws 在非交互环境会卡住超时）
    for i in range(0, len(to_delete), 100):
        batch = to_delete[i:i+100]
        resp = dws_cmd(["aitable","record","delete","--base-id",AI_BASE_ID,"--table-id",AI_TABLES[table_key],
                 "--record-ids", ",".join(batch), "--yes", "--format","json"])
        if resp.get("success"):
            result["delete_ok"] += len(batch)
        else:
            result["delete_fail"] += len(batch)
            log.warning(f"  [{table_key}] DELETE 批次失败 ({len(batch)}条): {resp.get('error','')[:100]}")

    return result

def main():
    global PMS_TOKEN, _DWS_PATH

    # ====== PARSE ARGS ======
    parser = argparse.ArgumentParser(description="PMS → AI表格同步")
    parser.add_argument("--token", default=None, help="PMS Bearer token")
    parser.add_argument("--full", action="store_true", help="全量同步（默认增量）")
    parser.add_argument("--dry-run", action="store_true", help="只检查不写入")
    parser.add_argument("--dws-path", default=None, help="dws CLI 可执行文件路径（默认从 PATH 查找）")
    parser.add_argument("--date", default=None, help="指定同步日期 (YYYY-MM-DD)，默认最近3天")
    parser.add_argument("--days", type=int, default=3, help="增量同步最近N天 (默认3)，与--date同时指定则只取那1天")
    args = parser.parse_args()

    # ====== 目标日期计算 ======
    today = datetime.date.today()
    if args.date:
        # 用户指定了具体日期
        try:
            target_date = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            log.error(f"日期格式错误: {args.date}，应为 YYYY-MM-DD")
            sys.exit(1)
        if target_date > today:
            log.error(f"目标日期 {target_date} 不能超过今天 {today}")
            sys.exit(1)
        target_days = [target_date.strftime("%Y-%m-%d")]
        mode_label = f"增量(指定日期:{target_date})"
    else:
        # 默认：最近 N 天
        args.days = max(1, args.days)
        target_days = [(today - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, args.days + 1)]
        mode_label = f"增量(最近{args.days}天:{target_days[-1]}~{target_days[0]})"

    # Token 获取：参数 > 环境变量 PMS_TOKEN > 交互输入
    if not args.token:
        args.token = os.environ.get("PMS_TOKEN", "").strip()
    if not args.token:
        # 检查是否在交互式终端中
        if sys.stdin.isatty():
            print("=" * 60)
            print("  PMS → 钉钉AI表格 同步工具")
            print("=" * 60)
            print()
            print("  未提供 --token 参数。")
            print("  请粘贴 PMS Bearer Token:")
            print()
            args.token = input("  Token: ").strip()
            print()
            if not args.token:
                print("  [错误] Token 不能为空，程序退出。")
                print("  用法: pms_sync.exe --token \"Bearer YOUR_TOKEN\"")
                print()
                sys.exit(1)
        else:
            print("错误: 必须提供 --token 参数")
            print("用法: pms_sync.exe --token \"Bearer YOUR_TOKEN\"")
            sys.exit(1)

    # === Token 清洗（修复: 从 bat/命令行/剪贴板传入时可能混入不可见字符/引号/首尾空白）===
    raw_token = args.token
    # 去除首尾空白、回车换行、Tab、BOM、零宽字符
    PMS_TOKEN = raw_token.strip("\r\n\t ").strip("\ufeff").strip("\u200b\u200c\u200d\ufeff")
    # 去除可能误带的前后引号（从某些终端复制时常见）
    if (PMS_TOKEN.startswith('"') and PMS_TOKEN.endswith('"')) or \
       (PMS_TOKEN.startswith("'") and PMS_TOKEN.endswith("'")):
        PMS_TOKEN = PMS_TOKEN[1:-1].strip()
    # 统一 Bearer 前缀
    if not PMS_TOKEN.startswith("Bearer "):
        PMS_TOKEN = "Bearer " + PMS_TOKEN
    if args.dws_path:
        _DWS_PATH = args.dws_path

    mode = "全量" if args.full else mode_label

    # ====== 生命周期：启动 ======
    log.hr("=", 65)
    log.lifecycle(f"PMS → AI Table 同步启动 | 模式: {mode} | Dry-Run: {args.dry_run}")
    log.info(f"  时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"  目标日期: {', '.join(target_days)}")
    log.info(f"  程序: {SCRIPT_DIR}")
    log.info(f"  dws:  {_find_dws()}")
    log.info(f"  PMS:  {PMS_BASE} (baseId={BASE_ID_PMS})")
    log.info(f"  AI表: {AI_BASE_ID}")
    log.hr()

    # === Token 诊断（脱敏：只打印长度/前缀/异常字符，不泄露完整 token）===
    log.info(f"  Token: 原始长度={len(raw_token)} 清洗后={len(PMS_TOKEN)} 前缀={PMS_TOKEN[:12]!r}...")
    suspicious = [i for i, c in enumerate(raw_token)
                  if ord(c) < 32 or ord(c) in (0x200b, 0x200c, 0x200d, 0xfeff)]
    if suspicious:
        log.warning(f"  ⚠ Token 含 {len(suspicious)} 个不可见字符（已自动清洗）位置示例: {suspicious[:5]}")

    # === Token 自检：发一个轻量请求验证，失败直接退出，避免跑完全表才报错 ===
    log.info("  Token 自检中...")
    try:
        _resp = pms_get("/pms/system/warehouse/list",
                        {"baseId": BASE_ID_PMS, "current": 1, "size": 1})
        _code = _resp.get("code")
        if _code and _code not in (0, 200):
            log.error(f"  ✗ Token 自检失败: PMS code={_code}, msg={str(_resp.get('msg',''))[:100]}")
            log.error(f"  → 请重新登录 PMS 系统后复制最新 token")
            log.summary()
            sys.exit(1)
        log.info(f"  ✓ Token 自检通过 (仓库接口返回 {_resp.get('total',0)} 条)")
    except SystemExit:
        raise
    except Exception as e:
        log.error(f"  ✗ Token 自检异常: {e}")
        log.error(f"  → 请检查网络或 token 是否正确")
        log.summary()
        sys.exit(1)
    log.hr()

    results = []
    aborted_stages = []

    # ====== Stage 1: 物料表 ======
    try:
        log.stage_begin("物料表")
        mats = pms_fetch_all_post("/pms/system/kc/material/list", {"baseId":BASE_ID_PMS, "status": 1})
        log.debug(f"PMS 返回物料: {len(mats)} 条")
        r = sync_table("material", MATERIAL_FIELDS, [transform_material(m) for m in mats], "num", args.dry_run, full_mode=True)
        if r is None:
            log.stage_end("物料表", "跳过（无权限/认证失败）")
            results.append(("物料表", {"skipped": True, "reason": "dws权限不足"}))
        else:
            log.stage_end("物料表", f"{r['new']}新增/{r['updated']}更新 (已有{r['existing']})")
            results.append(("物料表", r))
    except Exception as e:
        log.exception(f"物料表同步异常")
        results.append(("物料表", {"error": str(e)}))
        aborted_stages.append("物料表")

    # ====== Stage 2: 仓库表 ======
    try:
        log.stage_begin("仓库表")
        whs = pms_fetch_all_get("/pms/system/warehouse/list", {"baseId":BASE_ID_PMS, "status": 1})
        log.debug(f"PMS 返回仓库: {len(whs)} 条")
        r = sync_table("warehouse", WAREHOUSE_FIELDS, [transform_warehouse(w) for w in whs], "code", args.dry_run, full_mode=True)
        if r is None:
            log.stage_end("仓库表", "跳过（无权限/认证失败）")
            results.append(("仓库表", {"skipped": True, "reason": "dws权限不足"}))
        else:
            log.stage_end("仓库表", f"{r['new']}新增/{r['updated']}更新 (已有{r['existing']})")
            results.append(("仓库表", r))
    except Exception as e:
        log.exception(f"仓库表同步异常")
        results.append(("仓库表", {"error": str(e)}))
        aborted_stages.append("仓库表")

    # ====== Stage 3: 订单主表 ======
    sync_orders = []
    order_skipped = False
    try:
        log.stage_begin("订单主表")
        orders = pms_fetch_all_post("/pms/kc/order/list", {"baseId":BASE_ID_PMS})
        log.debug(f"PMS 返回订单列表: {len(orders)} 条")

        # 获取完整订单详情
        full_orders = []
        fetch_errors = 0
        for i, o in enumerate(orders):
            oid = o.get("orderId")
            if oid:
                try:
                    detail = pms_get(f"/pms/kc/order/detail/{oid}")
                    full_orders.append(detail.get("data", detail))
                except Exception as e:
                    fetch_errors += 1
                    log.warning(f"订单详情获取失败 [{oid}]: {e}")
            else:
                full_orders.append(o)
        if fetch_errors:
            log.warning(f"订单详情获取: {fetch_errors}/{len(orders)} 失败")

        if not args.full:
            recent_orders = [o for o in full_orders if (o.get("planDeliveryDate") or "") in target_days]
            log.info(f"  目标日期({target_days[0]}{'~' + target_days[-1] if len(target_days) > 1 else ''})订单: {len(recent_orders)} 条")
            log.debug(f"待同步订单ID: {[o.get('orderId') for o in recent_orders]}")

            existing_orders = query_existing_ids("order_main", ORDER_FIELDS["orderId"])
            if existing_orders is None:
                # 查询失败 → 无法去重，跳过写入防止重复
                log.warning(f"  ⚠ 无法查询订单已有记录（权限不足），跳过订单同步")
                results.append(("订单主表", {"skipped": True, "reason": "dws权限不足"}))
                results.append(("订单明细", {"skipped": True, "reason": "dws权限不足"}))
                order_skipped = True
            else:
                already_synced = sum(1 for o in recent_orders if str(o.get("orderId")) in existing_orders)
                if already_synced == len(recent_orders) and len(recent_orders) > 0:
                    log.warning(f"  ⚠ {len(recent_orders)} 条订单已全部同步过，跳过")
                    results.append(("订单主表", {"skipped": True, "reason": "已同步", "existing": already_synced}))
                    results.append(("订单明细", {"skipped": True, "reason": "已同步"}))
                    order_skipped = True
                else:
                    sync_orders = recent_orders
        else:
            sync_orders = full_orders

        if not order_skipped and sync_orders:
            r = sync_table("order_main", ORDER_FIELDS, [transform_order(o) for o in sync_orders], "orderId", args.dry_run)
            if r is None:
                log.stage_end("订单主表", "跳过（无权限/认证失败）")
                results.append(("订单主表", {"skipped": True, "reason": "dws权限不足"}))
                order_skipped = True  # 订单明细也跳过
            else:
                log.stage_end("订单主表", f"{r['new']}新增/{r['updated']}更新 (已有{r['existing']})")
                results.append(("订单主表", r))
        elif not order_skipped:
            log.info("  订单主表: 无待同步订单")
            results.append(("订单主表", {"skipped": True, "reason": "无数据"}))
    except Exception as e:
        log.exception(f"订单主表同步异常")
        results.append(("订单主表", {"error": str(e)}))
        aborted_stages.append("订单主表")

    # ====== Stage 4: 订单明细 ======
    if not order_skipped and sync_orders:
        try:
            log.stage_begin("订单明细")
            details = []
            for o in sync_orders:
                for d in (o.get("details") or []):
                    details.append(transform_detail(o, d))
            if details:
                r = sync_table("order_detail", DETAIL_FIELDS, details, "detailId", args.dry_run)
                if r is None:
                    log.stage_end("订单明细", "跳过（无权限/认证失败）")
                    results.append(("订单明细", {"skipped": True, "reason": "dws权限不足"}))
                else:
                    log.stage_end("订单明细", f"{r['new']}新增/{r['updated']}更新 (已有{r['existing']})")
                    results.append(("订单明细", r))
            else:
                log.info("  订单明细: 无数据")
                results.append(("订单明细", {"skipped": True, "reason": "无数据"}))
        except Exception as e:
            log.exception(f"订单明细同步异常")
            results.append(("订单明细", {"error": str(e)}))
            aborted_stages.append("订单明细")

    # ====== Stage 5: 库存变动记录（增量：最近3天） ======
    try:
        log.stage_begin("库存变动记录")
        inv_all = pms_fetch_all_get("/pms/system/inventory/find-records", {"baseId":BASE_ID_PMS})
        log.debug(f"PMS 返回库存: {len(inv_all)} 条")

        # 按目标日期过滤库存记录
        recent_inv = [i for i in inv_all if any((i.get("operationTime") or "").startswith(d) for d in target_days)]
        log.info(f"  目标日期({target_days[0]}{'~' + target_days[-1] if len(target_days) > 1 else ''})库存变动: {len(recent_inv)} 条 (总{len(inv_all)})")
        if not recent_inv:
            log.info("  库存变动: 无目标日期数据, 跳过")
            results.append(("库存变动记录", {"skipped": True, "reason": "无目标日期数据"}))
        else:
            r = sync_table("inventory", INVENTORY_FIELDS, [transform_inventory(i) for i in recent_inv], "recordNum", args.dry_run, skip_update=not args.full)
            if r is None:
                log.stage_end("库存变动记录", "跳过（无权限/认证失败）")
                results.append(("库存变动记录", {"skipped": True, "reason": "dws权限不足"}))
            else:
                log.stage_end("库存变动记录", f"{r['new']}新增/{r.get('skipped',r.get('updated',0))}跳过 (已有{r['existing']}) 目标{len(recent_inv)}/总{len(inv_all)}条")
                results.append(("库存变动记录", r))
    except Exception as e:
        log.exception(f"库存变动记录同步异常")
        results.append(("库存变动记录", {"error": str(e)}))
        aborted_stages.append("库存变动记录")

    # ====== 生命周期：汇总 ======
    log.lifecycle("同步结束，生成汇总...")
    extra_errors = len(aborted_stages)
    if aborted_stages:
        log.error(f"以下阶段异常中断: {', '.join(aborted_stages)}")

    summary = {
        "mode": mode,
        "dryRun": args.dry_run,
        "date": datetime.datetime.now().isoformat(),
        "results": {n: r for n, r in results},
    }
    log.info(json.dumps(summary, ensure_ascii=False, indent=2))

    exit_code = log.summary(extra_errors)
    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.warning("用户中断 (Ctrl+C)")
        log.summary()
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as e:
        log.exception(f"未捕获的致命异常: {e}")
        log.summary(extra_errors=1)
        sys.exit(1)
