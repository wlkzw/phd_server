import csv
import io
import re
from datetime import datetime
import openpyxl


def _read_file_content(filepath: str) -> list[list[str]]:
    """
    读取 CSV 或 Excel 文件，返回行列表
    """
    file_ext = filepath.lower().split('.')[-1]
    
    if file_ext in ['xlsx', 'xls']:
        # 读取 Excel 文件
        wb = openpyxl.load_workbook(filepath, data_only=True)
        ws = wb.active
        rows = []
        for row in ws.iter_rows(values_only=True):
            # 将所有值转换为字符串
            rows.append([str(cell) if cell is not None else '' for cell in row])
        return rows
    else:
        # 读取 CSV 文件
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin1']
        
        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding, newline='') as f:
                    reader = csv.reader(f)
                    return list(reader)
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        raise ValueError(f"无法识别文件编码: {filepath}")


def _parse_csv_format(rows: list[list[str]], debug: bool = False) -> list[dict]:
    """
    解析四种 CSV/Excel 格式，返回统一的数据结构
    [{"Name": "tag1", "Value": 123.45, "Time": "2024-01-01T00:00:00.000000Z"}, ...]
    """
    if len(rows) < 2:
        raise ValueError("文件至少需要 2 行数据")
    
    if debug:
        print(f"\n[DEBUG] 总行数: {len(rows)}")
        print(f"[DEBUG] 前5行内容:")
        for i, row in enumerate(rows[:5]):
            print(f"  行{i}: {row}")
    
    # 检测格式
    first_row = rows[0]
    second_row = rows[1] if len(rows) > 1 else []
    
    # 判断是否有索引列（第二种格式）
    has_index = False
    try:
        temp = int(rows[1][0])
        print(f"[DEBUG] 第一列值尝试转换为整数: {temp}")
        if temp == 1:
            has_index = True
    except (ValueError, IndexError, TypeError):
        pass
    
    if debug:
        print(f"[DEBUG] has_index: {has_index}")
    
    # 判断是否有描述行（第三种格式）或单位+描述行（第四种格式）
    has_description = False
    has_unit = False
    data_start_row = 1
    
    if len(rows) > 2:
        # 检查第二行是否为描述或单位
        second_row_sample = second_row[1] if len(second_row) > 1 else ""
        
        if debug:
            print(f"[DEBUG] 第二行第二列值: '{second_row_sample}'")
        
        # 如果第二行不是数字也不是时间戳，可能是描述或单位
        try:
            float(second_row_sample)
            is_numeric = True
        except (ValueError, TypeError):
            is_numeric = False
        
        is_ts = _is_timestamp(str(second_row_sample))
        
        if debug:
            print(f"[DEBUG] 是数字: {is_numeric}, 是时间戳: {is_ts}")
        
        if not is_numeric and not is_ts:
            has_description = True
            data_start_row = 2
            
            if debug:
                print(f"[DEBUG] 检测到描述行，data_start_row = {data_start_row}")
            
            # 检查第四种格式（单位+描述+重复tagname）
            if len(rows) > 3:
                # 检查第三行是否也是描述性内容
                third_row_sample = rows[2][1] if len(rows[2]) > 1 else ""
                try:
                    float(third_row_sample)
                    third_is_numeric = True
                except (ValueError, TypeError):
                    third_is_numeric = False
                
                third_is_ts = _is_timestamp(str(third_row_sample))
                
                if debug:
                    print(f"[DEBUG] 第三行第二列值: '{third_row_sample}'")
                    print(f"[DEBUG] 第三行是数字: {third_is_numeric}, 是时间戳: {third_is_ts}")
                
                if not third_is_numeric and not third_is_ts:
                    has_unit = True
                    data_start_row = 4
                    if debug:
                        print(f"[DEBUG] 检测到单位+描述行，data_start_row = {data_start_row}")
    
    # 确定时间戳列索引和 tag 名称列索引
    time_col_idx = 0
    tag_start_idx = 1
    
    if has_index:
        time_col_idx = 1
        tag_start_idx = 2
    
    if debug:
        print(f"[DEBUG] time_col_idx: {time_col_idx}, tag_start_idx: {tag_start_idx}")
        print(f"[DEBUG] data_start_row: {data_start_row}")
    
    # 提取 tag 名称
    tag_names = first_row[tag_start_idx:]
    
    if debug:
        print(f"[DEBUG] 提取的tag名称: {tag_names[:5]}... (共{len(tag_names)}个)")
    
    # 解析数据行
    result = []
    for row_idx in range(data_start_row, len(rows)):
        row = rows[row_idx]
        if len(row) <= time_col_idx:
            if debug and row_idx < data_start_row + 3:
                print(f"[DEBUG] 行{row_idx} 跳过: 列数不足")
            continue
            
        timestamp_str = str(row[time_col_idx]).strip()
        if not timestamp_str or timestamp_str == 'None':
            if debug and row_idx < data_start_row + 3:
                print(f"[DEBUG] 行{row_idx} 跳过: 时间戳为空")
            continue
        
        # 标准化时间戳
        try:
            timestamp = _normalize_timestamp(timestamp_str)
        except ValueError as e:
            if debug and row_idx < data_start_row + 3:
                print(f"[DEBUG] 行{row_idx} 时间戳解析失败: {timestamp_str} - {e}")
            continue
        
        if debug and row_idx < data_start_row + 3:
            print(f"[DEBUG] 行{row_idx} 时间戳: {timestamp_str} -> {timestamp}")
        
        # 提取每个 tag 的值
        row_values = 0
        for i, tag_name in enumerate(tag_names):
            value_idx = tag_start_idx + i
            if value_idx >= len(row):
                continue
                
            value_str = str(row[value_idx]).strip()
            if not value_str or value_str.lower() in ['', 'nan', 'null', 'none']:
                continue
            
            try:
                value = float(value_str)
                result.append({
                    "Name": str(tag_name).strip(),
                    "Value": value,
                    "Time": timestamp
                })
                row_values += 1
            except ValueError:
                if debug and row_idx < data_start_row + 3 and i < 3:
                    print(f"[DEBUG] 行{row_idx} tag{i}({tag_name}) 值解析失败: '{value_str}'")
                continue
        
        if debug and row_idx < data_start_row + 3:
            print(f"[DEBUG] 行{row_idx} 成功解析 {row_values} 个值")
    
    if debug:
        print(f"[DEBUG] 总计解析 {len(result)} 条记录\n")
    
    return result





def _is_timestamp(value: str) -> bool:
    """检查字符串是否为时间戳格式"""
    timestamp_patterns = [
        r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',  # 日期
        r'\d{1,2}:\d{1,2}:\d{1,2}',       # 时间
    ]
    return any(re.search(pattern, value) for pattern in timestamp_patterns)


def _normalize_timestamp(ts_str: str) -> str:
    """
    将各种时间戳格式标准化为 QuestDB 接受的格式
    输出: 2024-01-01T00:00:00.000000Z
    """
    ts_str = ts_str.strip()
    
    # 常见格式
    formats = [
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(ts_str, fmt)
            return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "000Z"
        except ValueError:
            continue
    
    # 如果都不匹配，尝试 ISO 格式
    try:
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "000Z"
    except:
        raise ValueError(f"无法解析时间戳: {ts_str}")

def test_from_file(filepath: str, debug: bool = True):
    """从文件测试（支持 CSV 和 Excel）"""
    try:
        rows = _read_file_content(filepath)
        print(f"文件 {filepath}:")
        print(f"  成功读取，共 {len(rows)} 行")
        
        result = _parse_csv_format(rows, debug=debug)
        print(f"  解析成功，共 {len(result)} 条记录")
        if result:
            print(f"  示例数据:")
            for item in result[:5]:
                print(f"    {item}")
    except Exception as e:
        print(f"文件 {filepath} 处理失败: {e}")
        import traceback
        traceback.print_exc()
    print()


if __name__ == "__main__":
    print("=== CSV/Excel 解析器测试 ===\n")
    
    # 测试四种预定义格式
    # test_format_1()
    # test_format_2()
    # test_format_3()
    # test_format_4()
    
    # 测试实际文件
    # test_from_file("supcon-dcs.csv")
    # test_from_file("holysis-dcs.csv")
    test_from_file("yogokawa-dcs.xlsx")
    # test_from_file("锅炉dcs.xlsx")
    
    # 如果有 Excel 文件，也可以测试
    # test_from_file("test.xlsx")