from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime
# import psycopg2
import pandas as pd
import os

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 4, 4)
}

dag = DAG(
    'grocery_data',
    default_args=default_args,
    schedule_interval=None
)

def create_table():
    postgres_hook = PostgresHook(postgres_conn_id='postgres_localhost')
    conn = postgres_hook.get_conn()
    cur = conn.cursor()
    
    create_table_query = '''
        CREATE TABLE data_grocery (
            sku VARCHAR(255) PRIMARY KEY,
            product_name VARCHAR(255),
            qty INTEGER
        );
    '''
    cur.execute(create_table_query)
    conn.commit()
    print("Table created successfully")

create_table_task = PythonOperator(
    task_id='create_table',
    python_callable=create_table,
    dag=dag
)

def insert_data():
    postgres_hook = PostgresHook(postgres_conn_id='postgres_localhost')
    conn = postgres_hook.get_conn()
    cur = conn.cursor()

    data = pd.read_csv('/home/airflow/data/mock_data_grocery.csv')

    # Insert data to table
    for index, row in data.iterrows():
        cur.execute(
            "INSERT INTO data_grocery (sku, product_name, qty) VALUES (%s, %s, %s)",
            (row['sku'], row['product_name'], row['qty'])
        )

    conn.commit()
    print("Data inserted successfully")

insert_data_task = PythonOperator(
    task_id='insert_data',
    python_callable=insert_data,
    dag=dag
)

def update_data():
    postgres_hook = PostgresHook(postgres_conn_id='postgres_localhost')
    conn = postgres_hook.get_conn()
    cur = conn.cursor()

    # Read the CSV file data update
    data = pd.read_csv('/home/airflow/data/mock_data_grocery_update.csv')

    # looping for scenario update data
    for index, row in data.iterrows():
        sku = row['sku']
        product_name = row['product_name']
        qty = row['qty']

        # Check based on SKU
        cur.execute("SELECT * FROM data_grocery WHERE sku = %s", (sku,))
        result = cur.fetchone()

        if result:
            # SKU available, check jumlah qty
            existing_qty = result[2]

            if qty < 0:
                # If quantity new sku minus(-), exiting - quantity from file
                new_qty = existing_qty - abs(qty)
            else:
                # existing quantity + new quantity as quantity
                new_qty = existing_qty + qty

            # Check product name based on SKU
            if result[1] != product_name:
                # Update product name based on new data
                cur.execute(
                    "UPDATE data_grocery SET product_name = %s WHERE sku = %s",
                    (product_name, sku)
                )

            # Update qty for the sku
            cur.execute(
                "UPDATE data_grocery SET qty = %s WHERE sku = %s",
                (new_qty, sku)
            )
        else:
            # SKU doesn't exist in the table
            cur.execute(
                "INSERT INTO data_grocery (sku, product_name, qty) VALUES (%s, %s, %s)",
                (sku, product_name, qty)
            )

    conn.commit()
    print("Data updated successfully")

update_data_task = PythonOperator(
    task_id='update_data',
    python_callable=update_data,
    dag=dag
)

def delete_files():
    os.remove('/home/airflow/data/mock_data_grocery.csv')
    os.remove('/home/airflow/data/mock_data_grocery_update.csv')
    print("CSV files deleted")

delete_files_task = PythonOperator(
    task_id='delete_files',
    python_callable=delete_files,
    dag=dag
)


create_table_task >> insert_data_task >> update_data_task >> delete_files_task
