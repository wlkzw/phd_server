from __future__ import annotations
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, jsonify, request
from flask_cors import CORS
from ssl import CERT_NONE
from ldap3 import ALL, Connection, Server, Tls
from io import StringIO
import jwt
import csv
import io
import re
import requests
from script.csv_parser import _read_file_content, _parse_csv_format

app = Flask(__name__)
CORS(app)

app.config.update(
    SECRET_KEY="iloveoptimumprocess",
    LDAP_SERVER="backbonetech.cn",
    LDAP_PORT=636,
    LDAP_DOMAIN="BACKBONETECH",
    LDAP_UPN_SUFFIX="backbonetech.cn",
    LDAP_BASE_DN="OU=Backbonetech,DC=backbonetech,DC=cn",
    LDAP_BIND_DN="CN=gitlab-ldap,OU=Backbonetech,DC=backbonetech,DC=cn",
    LDAP_BIND_PASSWORD="Abcd1234",
    TOKEN_TTL_HOURS=24,
    ADMIN_USERS=["zhitong.jiang", "kaizhen.wu"],
    QUESTDB_IMPORT_URL="http://10.0.0.233:9000/imp",
    QUESTDB_EXEC_URL="http://10.0.0.233:9000/exec",
)

TLS = Tls(validate=CERT_NONE)

SQL_PATTERN = re.compile(
    r"\(\s*(?P<id>-?\d+)\s*,\s*'(?P<name>(?:[^'\\]|\\.)*)'\s*,\s*(?P<value>-?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+\-]?\d+)?)\s*,\s*'(?P<time>[^']+)'\s*,\s*(?P<status>-?\d+)\s*,\s*'(?P<dcstime>[^']+)'\s*\)"
)

def _sql_to_csv(sql_text: str) -> tuple[str, int]:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Name", "Value", "Time::timestamp"])
    count = 0
    for match in SQL_PATTERN.finditer(sql_text):
        name = match.group("name")
        value = match.group("value")
        iso_time = match.group("time").replace(" ", "T") + ".000000Z"
        writer.writerow([name, value, iso_time])
        count += 1
    return buffer.getvalue(), count

def _ldap_bind(username: str, password: str) -> tuple[bool, dict | None]:
    server = Server(
        app.config["LDAP_SERVER"],
        port=app.config["LDAP_PORT"],
        use_ssl=True,
        tls=TLS,
        get_info=ALL,
    )
    try:
        with Connection(
            server,
            user=app.config["LDAP_BIND_DN"],
            password=app.config["LDAP_BIND_PASSWORD"],
            authentication="SIMPLE",
            auto_bind=True,
        ) as conn:
            conn.search(
                search_base=app.config["LDAP_BASE_DN"],
                search_filter=f"(sAMAccountName={username})",
                attributes=["displayName", "mail", "department"],
            )
            if not conn.entries:
                return False, None

            entry = conn.entries[0]
            user_upn = f"{username}@{app.config['LDAP_UPN_SUFFIX']}"
            if not conn.rebind(
                user=user_upn,
                password=password,
                authentication="SIMPLE",
            ):
                return False, None

            return True, {
                "username": username,
                "name": str(getattr(entry, "displayName", username)),
                "email": str(getattr(entry, "mail", "")),
                "department": str(getattr(entry, "department", "")),
            }
    except Exception as exc:
        app.logger.error("LDAP bind failed for %s: %s", username, exc)
        return False, None

def _is_admin(username: str) -> bool:
    return username.lower() in [u.lower() for u in app.config["ADMIN_USERS"]]

def _issue_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=app.config["TOKEN_TTL_HOURS"]),
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")

def _list_questdb_tables() -> list[dict]:
    try:
        response = requests.get(
            app.config["QUESTDB_EXEC_URL"],
            params={"query": "tables();"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        app.logger.error(
            "QuestDB tables fetch failed for %s: %s",
            getattr(request, "user", "?"),
            exc,
        )
        raise
    
    columns = [col.get("name") for col in payload.get("columns", [])]
    dataset = payload.get("dataset", [])
    tables = []
    
    for row in dataset:
        item = {columns[i]: row[i] for i in range(min(len(columns), len(row)))}
        table_name = item.get("table_name") or item.get("name") or row[0]
        
        # 获取每个表的最老和最新时间戳
        oldest = None
        newest = None
        try:
            time_response = requests.get(
                app.config["QUESTDB_EXEC_URL"],
                params={"query": f"SELECT min(Time) as oldest, max(Time) as newest FROM {table_name};"},
                timeout=5,
            )
            if time_response.ok:
                time_data = time_response.json()
                if time_data.get("dataset") and time_data["dataset"][0]:
                    oldest = time_data["dataset"][0][0]
                    newest = time_data["dataset"][0][1]
        except Exception as e:
            app.logger.warning(f"Failed to get time range for {table_name}: {e}")
        
        tables.append(
            {
                "table_name": table_name,
                "oldest": oldest,
                "newest": newest,
            }
        )
    return tables

def _get_table_detail(table_name: str) -> dict:
    try:
        # 1. 时间范围和总量
        stats_query = f"""
        SELECT 
            min(Time) as oldest, 
            max(Time) as newest, 
            count() as total_rows 
        FROM {table_name};
        """
        stats_resp = requests.get(
            app.config["QUESTDB_EXEC_URL"],
            params={"query": stats_query},
            timeout=10,
        )
        stats_resp.raise_for_status()
        stats_data = stats_resp.json()
        
        oldest = None
        newest = None
        total_rows = 0
        
        if stats_data.get("dataset") and len(stats_data["dataset"]) > 0:
            row = stats_data["dataset"][0]
            oldest = row[0] if row[0] else None
            newest = row[1] if row[1] else None
            total_rows = row[2] if row[2] else 0

        # 2. Name标签列表及计数
        names_query = f"""
        SELECT Name, count() as cnt 
        FROM {table_name} 
        GROUP BY Name 
        ORDER BY cnt DESC;
        """
        names_resp = requests.get(
            app.config["QUESTDB_EXEC_URL"],
            params={"query": names_query},
            timeout=10,
        )
        names_resp.raise_for_status()
        names_data = names_resp.json()
        
        names_list = []
        if names_data.get("dataset"):
            for row in names_data["dataset"]:
                names_list.append({
                    "name": row[0],
                    "count": row[1]
                })

        return {
            "table_name": table_name,
            "oldest": oldest,
            "newest": newest,
            "total_rows": total_rows,
            "names_count": len(names_list),
            "names": names_list
        }
    except requests.RequestException as exc:
        app.logger.error("QuestDB table detail failed for %s: %s", table_name, exc)
        raise

def _generate_clc_file(table_name: str, tags: list[str], start_time: str, end_time: str) -> str:
    """生成 CLC 格式文件内容"""
    TAGS_PER_GROUP = 13
    
    # 1. 查询数据
    time_filter = ""
    if start_time and end_time:
        time_filter = f"AND Time >= '{start_time}' AND Time <= '{end_time}'"
    elif start_time:
        time_filter = f"AND Time >= '{start_time}'"
    elif end_time:
        time_filter = f"AND Time <= '{end_time}'"
    
    # 构建查询，获取所有选中标签的数据
    tag_list_str = "','".join(tags)
    query = f"""
    SELECT Time, Name, Value
    FROM {table_name}
    WHERE Name IN ('{tag_list_str}')
    {time_filter}
    ORDER BY Time ASC;
    """
    
    response = requests.get(
        app.config["QUESTDB_EXEC_URL"],
        params={"query": query},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    
    # 2. 组织数据：按时间戳分组
    from collections import defaultdict
    time_data = defaultdict(dict)  # {timestamp: {tag: value}}
    
    for row in data.get("dataset", []):
        timestamp = row[0]
        tag_name = row[1]
        value = row[2]
        time_data[timestamp][tag_name] = value
    
    if not time_data:
        raise ValueError("时间范围内没有数据")
    
    timestamps = sorted(time_data.keys())
    first_timestamp = timestamps[0]
    rows_count = len(timestamps)
    
    # 3. 生成 CLC 文件内容
    buffer = StringIO()
    
    # 第1-7行：头部信息
    buffer.write(f"{table_name}\n")
    buffer.write("PHD Data Export\n")
    buffer.write(f"{len(tags)}\n")
    buffer.write(f"{TAGS_PER_GROUP}\n")
    
    # 格式化开始时间为 M-D-YYYY HH:MM:SS
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(first_timestamp.replace('Z', '+00:00'))
        formatted_time = dt.strftime("%m-%d-%Y %H:%M:%S")
    except:
        formatted_time = first_timestamp
    
    buffer.write(f"{formatted_time}\n")
    buffer.write("60\n")
    buffer.write(f"{rows_count}\n")
    
    # 第8行：分隔线
    buffer.write("=" * 80 + "\n")
    
    # 第9行开始：标签列表（格式化为固定长度）
    for tag in tags:
        formatted_tag = f"{tag}~~~{tag}~~~~~~"[:40]  # 固定40字符长度
        buffer.write(f"{formatted_tag}\n")
    
    # 再次分隔
    buffer.write("=" * 80 + "\n")
    
    # 4. 按组写入数据
    # 计算需要分成多少组
    num_groups = (len(tags) + TAGS_PER_GROUP - 1) // TAGS_PER_GROUP
    
    for group_idx in range(num_groups):
        # 如果不是第一组，添加分隔线
        if group_idx > 0:
            buffer.write("=" * 80 + "\n")
        
        # 当前组的标签
        start_idx = group_idx * TAGS_PER_GROUP
        end_idx = min(start_idx + TAGS_PER_GROUP, len(tags))
        group_tags = tags[start_idx:end_idx]
        
        # 数据行：每行包含时间戳和当前组的标签值
        for timestamp in timestamps:
            row_values = time_data[timestamp]
            
            # 格式化时间戳
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime("%m-%d-%Y %H:%M:%S")
            except:
                time_str = timestamp
            
            buffer.write(time_str)
            
            # 写入当前组的标签值
            for tag in group_tags:
                value = row_values.get(tag, 0.0)
                buffer.write(f",{value},G")
            
            buffer.write("\n")
    
    return buffer.getvalue()

def _auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(success=False, message="缺少凭证"), 401
        token = header.removeprefix("Bearer ").strip()
        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            request.user = data["sub"]
        except jwt.ExpiredSignatureError:
            return jsonify(success=False, message="Token 已过期"), 401
        except jwt.InvalidTokenError:
            return jsonify(success=False, message="Token 无效"), 401
        return fn(*args, **kwargs)

    return wrapper

@app.post("/api/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "").strip()
    password = payload.get("password", "")
    if not username or not password:
        return jsonify(success=False, message="用户名和密码不能为空"), 400

    ok, user_info = _ldap_bind(username, password)
    if not ok:
        return jsonify(success=False, message="用户名或密码错误"), 401

    token = _issue_token(username)
    return jsonify(success=True, token=token, user=user_info), 200

@app.get("/api/profile")
@_auth_required
def profile():
    return jsonify(success=True, username=request.user), 200

@app.post("/api/questdb/import")
@_auth_required
def questdb_import():
    uploaded = request.files.get("file")
    if not uploaded:
        return jsonify(success=False, message="缺少上传文件"), 400

    sql_text = uploaded.read().decode("utf-8", errors="ignore")
    csv_payload, rows = _sql_to_csv(sql_text)

    try:
        response = requests.post(
            app.config["QUESTDB_IMPORT_URL"],
            params={"fmt": "csv"},
            files={"data": ("import.csv", csv_payload, "text/csv")},
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        app.logger.error("QuestDB import failed for %s: %s", request.user, exc)
        return jsonify(success=False, message="QuestDB 导入失败"), 502

    return jsonify(success=True, imported=rows), 200

@app.get("/api/questdb/tables")
@_auth_required
def questdb_tables():
    try:
        tables = _list_questdb_tables()
        return jsonify(success=True, tables=tables), 200
    except requests.RequestException:
        return jsonify(success=False, message="无法获取 QuestDB 表列表"), 502

@app.post("/api/questdb/create-table")
@_auth_required
def questdb_create_table():
    if not _is_admin(request.user):
        return jsonify(success=False, message="权限不足：只有管理员可以创建项目"), 403
     
    payload = request.get_json(silent=True) or {}
    table_name = payload.get("table_name", "").strip()
    
    if not table_name:
        return jsonify(success=False, message="表名不能为空"), 400
    
    # 验证表名只包含字母、数字和下划线
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        return jsonify(success=False, message="表名只能包含字母、数字和下划线"), 400

    # 创建表的 SQL
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        Name SYMBOL,
        Value DOUBLE,
        Time TIMESTAMP
    ) timestamp(Time) PARTITION BY DAY;
    """

    try:
        response = requests.get(
            app.config["QUESTDB_EXEC_URL"],
            params={"query": create_table_sql},
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
        
        # 检查是否有错误
        if result.get("error"):
            return jsonify(success=False, message=f"创建表失败: {result['error']}"), 500
            
        return jsonify(success=True, message=f"表 {table_name} 创建成功"), 200
    except requests.RequestException as exc:
        app.logger.error("QuestDB create table failed for %s: %s", request.user, exc)
        return jsonify(success=False, message="无法连接到 QuestDB"), 502
    
@app.get("/api/user/permissions")
@_auth_required
def user_permissions():
    return jsonify(
        success=True,
        username=request.user,
        is_admin=_is_admin(request.user),
    ), 200

@app.get("/api/questdb/table-detail/<table_name>")
@_auth_required
def questdb_table_detail(table_name: str):
    try:
        detail = _get_table_detail(table_name)
        return jsonify(success=True, detail=detail), 200
    except requests.RequestException:
        return jsonify(success=False, message="无法获取表详情"), 502

@app.post("/api/questdb/import-csv/<table_name>")
@_auth_required
def questdb_import_csv(table_name: str):
    """导入 CSV/Excel 文件到指定表"""
    uploaded = request.files.get("file")
    if not uploaded:
        return jsonify(success=False, message="缺少上传文件"), 400
    
    # 保存临时文件
    import tempfile
    import os
    
    temp_fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(uploaded.filename)[1])
    try:
        with os.fdopen(temp_fd, 'wb') as f:
            f.write(uploaded.read())
        
        # 读取并解析文件
        rows = _read_file_content(temp_path)
        parsed_data = _parse_csv_format(rows, debug=False)
        
        if not parsed_data:
            return jsonify(success=False, message="文件中没有有效数据"), 400
        
        # 转换为 CSV 格式
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Name", "Value", "Time::timestamp"])
        
        for item in parsed_data:
            writer.writerow([item["Name"], item["Value"], item["Time"]])
        
        csv_payload = buffer.getvalue()
        
        # 导入到 QuestDB
        response = requests.post(
            app.config["QUESTDB_IMPORT_URL"],
            params={"name": table_name, "fmt": "csv", "overwrite": "false"},
            files={"data": ("import.csv", csv_payload, "text/csv")},
            timeout=60,
        )
        response.raise_for_status()
        
        return jsonify(success=True, imported=len(parsed_data)), 200
        
    except ValueError as e:
        app.logger.error("CSV parse failed for %s: %s", request.user, e)
        return jsonify(success=False, message=f"文件格式错误: {str(e)}"), 400
    except requests.RequestException as exc:
        app.logger.error("QuestDB import failed for %s: %s", request.user, exc)
        return jsonify(success=False, message="QuestDB 导入失败"), 502
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)

@app.post("/api/questdb/chart-data/<table_name>")
@_auth_required
def questdb_chart_data(table_name: str):
    """获取指定标签的时序数据用于绘图"""
    payload = request.get_json(silent=True) or {}
    tags = payload.get("tags", [])
    start_time = payload.get("start_time")
    end_time = payload.get("end_time")
    
    if not tags:
        return jsonify(success=False, message="请至少选择一个标签"), 400

    try:
        result = {}
        for tag in tags:
            # 构建时间筛选条件
            time_filter = ""
            if start_time and end_time:
                time_filter = f"AND Time >= '{start_time}' AND Time <= '{end_time}'"
            elif start_time:
                time_filter = f"AND Time >= '{start_time}'"
            elif end_time:
                time_filter = f"AND Time <= '{end_time}'"
            
            query = f"""
            SELECT Time, Value 
            FROM {table_name} 
            WHERE Name = '{tag}' {time_filter}
            ORDER BY Time ASC 
            LIMIT 10000;
            """
            response = requests.get(
                app.config["QUESTDB_EXEC_URL"],
                params={"query": query},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            
            result[tag] = [
                {"time": row[0], "value": row[1]}
                for row in data.get("dataset", [])
            ]
        
        return jsonify(success=True, data=result), 200
    except requests.RequestException as exc:
        app.logger.error("QuestDB chart data failed for %s: %s", table_name, exc)
        return jsonify(success=False, message="无法获取图表数据"), 502

@app.post("/api/questdb/export-clc/<table_name>")
@_auth_required
def questdb_export_clc(table_name: str):
    """导出 CLC 格式文件"""
    payload = request.get_json(silent=True) or {}
    tags = payload.get("tags", [])
    start_time = payload.get("start_time")
    end_time = payload.get("end_time")
    
    if not tags:
        return jsonify(success=False, message="请至少选择一个标签"), 400
    
    try:
        clc_content = _generate_clc_file(table_name, tags, start_time, end_time)
        
        from flask import Response
        return Response(
            clc_content,
            mimetype="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename={table_name}.clc"
            }
        )
    except ValueError as e:
        return jsonify(success=False, message=str(e)), 400
    except requests.RequestException as exc:
        app.logger.error("CLC export failed for %s: %s", table_name, exc)
        return jsonify(success=False, message="导出失败"), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)