import pandas as pd
import random
import time

random.seed(42) ##for reproducing purpose
NUM_POINTS = 2000

tables = [
    ("users", "id, email, signup_date, country, status"),
    ("orders", "id, user_id, amount, created_at, status"),
    ("products", "id, name, price, stock_level, category"),
    ("logs", "id, timestamp, level, message, service_name"),
    ("subscriptions", "id, user_id, plan_type, start_date, mrr"),
    ("events", "event_id, session_id, event_type, url, timestamp")
]

dialects = ["Postgres", "Snowflake", "BigQuery"]
departments = ["Finance", "Engineering", "Sales", "Marketing", "Product", "Support"]

templates = [
    {
        "desc": "Calculate average {col} in {table}",
        "sql": "SELECT avg({col}) FROM {table} WHERE created_at >= NOW() - INTERVAL '30 days'",
        "type": "metric"
    },
    {
        "desc": "Count total {table} by {group_col}",
        "sql": "SELECT {group_col}, count(*) FROM {table} GROUP BY {group_col} ORDER BY 2 DESC",
        "type": "agg"
    },
    {
        "desc": "Find {table} with {col} greater than {val}",
        "sql": "SELECT * FROM {table} WHERE {col} > {val} LIMIT 100",
        "type": "filter"
    },
    {
        "desc": "Monthly trend of {col} for {table}",
        "sql": "SELECT DATE_TRUNC('month', created_at) as month, sum({col}) FROM {table} GROUP BY 1 ORDER BY 1",
        "type": "timeseries"
    },
    {
        "desc": "List inactive {table} (no activity 90 days)",
        "sql": "SELECT * FROM {table} WHERE last_active < CURRENT_DATE - 90",
        "type": "risk"
    }
]

data = []

print(f'Generating {NUM_POINTS} rows of synthetic sql queries...')
IN = time.time()

for _ in range(NUM_POINTS):
    ## desc, sql , tag, dialect 
    table_name,columns = random.choice(tables)
    column_names = [c.strip() for c in columns.split(',')]
    template = random.choice(templates)

    target_col = random.choice(column_names)
    group_col = random.choice(column_names)

    numeric_cols = [c for c in column_names if c in ['amount', 'price', 'mrr', 'stock_level', 'id']]
    if template["type"] in ["metric", "timeseries"] and numeric_cols:
        target_col = random.choice(numeric_cols)
    

    desc = template["desc"].format(col=target_col, table=table_name, group_col=group_col, val=random.randint(10, 1000))
    sql = template["sql"].format(col=target_col, table=table_name, group_col=group_col, val=random.randint(10, 1000))

    data.append({
        'desc':desc,
        'sql':sql,
        'tag':random.choice(departments),
        'dialect':random.choice(dialects)
    })

##save to csv
df=pd.DataFrame(data=data)
file_name = r'./sql_data/¸sql_file.csv'
df.to_csv(file_name,index=False)
print('Generated synthetic sql data and stored in {file_name}'.format(file_name=file_name))
print(f'Exited in {time.time()-IN:3f} seconds')