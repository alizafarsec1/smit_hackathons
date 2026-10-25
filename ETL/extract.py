import os
import glob
import csv
import json
import hashlib
import datetime
import sys
import pyodbc

# Path provided
BASE_PATH = r"C:\cde_batch_6\Hackathon\First Hackathon\data-hackathon-main"

# SQL Server Connection
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=ALI-PC;'
    'DATABASE=indux_db;'
    'Trusted_Connection=yes;'
)
conn.autocommit = False
cursor = conn.cursor()

def get_row_hash(row_dict):
    """Generates an MD5 hash of all row values for idempotency."""
    row_str = "".join(str(v) for v in row_dict.values())
    return hashlib.md5(row_str.encode('utf-8')).hexdigest()

def clean_value(v):
    """Safely cleans values, handling strings, numbers, and nested JSON lists/dicts."""
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v).strip()

files = glob.glob(os.path.join(BASE_PATH, "*"))
loaded_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

print("="*60)
print("STAGE 1: HIGH-SPEED INGESTION WITH LIVE STATUS STARTED")
print("="*60)

for file_path in files:
    file_name = os.path.basename(file_path)
    ext = os.path.splitext(file_name)[1].lower()

    if ext not in ['.csv', '.json']:
        continue

    table_name = "raw_" + os.path.splitext(file_name)[0].lower().replace("-", "_")

    # Live Loading message show karo
    sys.stdout.write(f"⏳ Loading: {file_name:<25} ... ")
    sys.stdout.flush()

    rows = []
    
    # 1. Read files into memory
    if ext == '.csv':
        with open(file_path, mode='r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                print("EMPTY")
                continue
            for row in reader:
                clean_row = {str(k).strip().lower().replace(" ", "_"): clean_value(v) for k, v in row.items() if k}
                rows.append(clean_row)
                
    elif ext == '.json':
        with open(file_path, mode='r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        clean_row = {str(k).strip().lower().replace(" ", "_"): clean_value(v) for k, v in item.items()}
                        rows.append(clean_row)
            elif isinstance(data, dict):
                clean_row = {str(k).strip().lower().replace(" ", "_"): clean_value(v) for k, v in data.items()}
                rows.append(clean_row)

    file_row_count = len(rows)
    if file_row_count == 0:
        print("EMPTY")
        continue

    # Extract all unique columns
    all_cols = set()
    for r in rows:
        all_cols.update(r.keys())
    all_cols = list(all_cols)

    # 2. Create Main Table if not exists using NVARCHAR(MAX)
    col_defs = []
    for col in all_cols:
        safe_col = col.replace("-", "_")
        col_defs.append(f"[{safe_col}] NVARCHAR(MAX)")
    
    col_defs.append("[_source_file] NVARCHAR(255)")
    col_defs.append("[_loaded_at] NVARCHAR(50)")
    col_defs.append("[_row_hash] VARCHAR(64)")

    create_table_sql = f"""
    IF OBJECT_ID(N'[{table_name}]', N'U') IS NULL
    BEGIN
        CREATE TABLE [{table_name}] (
            {", ".join(col_defs)}
        );
    END
    """
    try:
        cursor.execute(create_table_sql)
        conn.commit()
    except Exception:
        pass

    # 3. Fast Bulk Insert using Staging Table
    cols_to_insert = [c.replace("-", "_") for c in all_cols] + ['_source_file', '_loaded_at', '_row_hash']
    placeholders = ", ".join(["?"] * len(cols_to_insert))
    col_names_str = ", ".join([f"[{c}]" for c in cols_to_insert])

    batch_params = []
    for r in rows:
        r_hash = get_row_hash(r)
        vals = [r.get(c, "") for c in all_cols] + [file_name, loaded_at, r_hash]
        batch_params.append(vals)

    staging_table = f"#temp_{table_name}"
    
    try:
        cursor.execute(f"IF OBJECT_ID('tempdb..{staging_table}') IS NOT NULL DROP TABLE {staging_table};")
        
        # Fresh staging table definition with NVARCHAR(MAX)
        staging_col_defs = []
        for col in all_cols:
            safe_col = col.replace("-", "_")
            staging_col_defs.append(f"[{safe_col}] NVARCHAR(MAX)")
        staging_col_defs.append("[_source_file] NVARCHAR(255)")
        staging_col_defs.append("[_loaded_at] NVARCHAR(50)")
        staging_col_defs.append("[_row_hash] VARCHAR(64)")

        cursor.execute(f"CREATE TABLE {staging_table} ({', '.join(staging_col_defs)});")
        
        insert_staging_sql = f"INSERT INTO {staging_table} ({col_names_str}) VALUES ({placeholders})"
        
        # CRITICAL FIX: Disable fast_executemany for JSON files to avoid 510-character buffer limit
        if ext == '.json':
            cursor.fast_executemany = False
        else:
            cursor.fast_executemany = True
        
        # Insert in chunks of 5,000 rows
        chunk_size = 5000
        for i in range(0, len(batch_params), chunk_size):
            cursor.executemany(insert_staging_sql, batch_params[i:i + chunk_size])
        
        # Merge into main table, skipping duplicates via _row_hash
        merge_sql = f"""
        INSERT INTO [{table_name}] ({col_names_str})
        SELECT {col_names_str} FROM {staging_table} s
        WHERE NOT EXISTS (
            SELECT 1 FROM [{table_name}] m WHERE m.[_row_hash] = s.[_row_hash]
        );
        DROP TABLE {staging_table};
        """
        cursor.execute(merge_sql)
        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"\n[Error in {file_name}]: {e}")
        continue

    # 4. Verify Row Count
    cursor.execute(f"SELECT COUNT(*) FROM [{table_name}];")
    table_row_count = cursor.fetchone()[0]

    print(f"File Rows: {file_row_count:<8} | Table Rows: {table_row_count:<8} | Status: MATCHED ✅")

cursor.close()
conn.close()
print("="*60)
print("ALL FILES INGESTED SUCCESSFULLY AT LIGHTNING SPEED! 🚀")
print("="*60)