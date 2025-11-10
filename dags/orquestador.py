

import sys
import os
import time
from airflow import DAG
from airflow.providers.mysql.operators.mysql import MySqlOperator
from airflow.sensors.filesystem import FileSensor
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta
import mlflow

sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from funciones import insert_data, read_data, train_model,  insert_train_test_split, promote_best_model
from scripts.queries import DROP_TABLE_RAW, DROP_TABLE_CLEAN,DROP_TABLE_TRAIN,DROP_TABLE_VAL, DROP_TABLE_TEST ,CREATE_TABLE_RAW, CREATE_TABLE_CLEAN,  CREATE_TABLE_CLEAN_TRAIN, CREATE_TABLE_CLEAN_TEST, CREATE_TABLE_CLEAN_VAL 

MODEL_PATH = "/opt/airflow/models/GradientBoosting.pkl"

MYSQL_HOST = "172.17.0.1"
MYSQL_PORT = 30306
MYSQL_USER = "root"
MYSQL_PASSWORD = "root123"
MYSQL_DB = "MODELAME"

# DAG configuration
start_date = datetime(2023, 1, 1, 0, 0)
interval = timedelta(minutes=5)
end_date = start_date + interval * 7  # 10 corridas en total

default_args = {
    'owner': 'airflow',
    'depends_on_past': True,  
    'wait_for_downstream': True,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
}

# Función para determinar primera corrida
def check_if_first_run(**context):
    execution_date = context['execution_date']
    dag = context['dag']
    if execution_date == dag.start_date:
        return 'delete_table_raw'
    else:
        return 'skip_table_creation'

# Función para esperar 5 minutos
def wait_five_minutes():
    time.sleep(300)  # 5 minutos

with DAG(
    dag_id="orquestador",
    default_args=default_args,
    description="Pipeline completo: Carga, Limpieza, Entrenamiento y Despliegue",
    start_date=start_date,
    end_date=end_date,
    schedule_interval="*/5 * * * *",  # Cada 5 minutos
    catchup=True,
    max_active_runs=1,  
    tags=['ml', 'forest', 'classification'],
) as dag:

    # --- Branch para primera corrida ---

  
    check_first_run_task = BranchPythonOperator(
    task_id="check_first_run",
    python_callable=check_if_first_run,
    provide_context=True,
    )

    delete_table_raw = MySqlOperator(
    task_id="delete_table_raw",
    mysql_conn_id="mysql_conn",
    sql=DROP_TABLE_RAW,
    )

    delete_table_clean = MySqlOperator(
    task_id="delete_table_clean",
    mysql_conn_id="mysql_conn",
    sql=DROP_TABLE_CLEAN,
    )

    delete_table_train = MySqlOperator(
    task_id="delete_table_train",
    mysql_conn_id="mysql_conn",
    sql=DROP_TABLE_TRAIN,
    )

    delete_table_test = MySqlOperator(
    task_id="delete_table_test",
    mysql_conn_id="mysql_conn",
    sql=DROP_TABLE_TEST,
    )

    delete_table_val = MySqlOperator(
    task_id="delete_table_val",
    mysql_conn_id="mysql_conn",
    sql=DROP_TABLE_VAL,
    )

    create_table_raw = MySqlOperator(
        task_id="create_table_raw",
        mysql_conn_id="mysql_conn",
        sql=CREATE_TABLE_RAW,
    )

    create_table_clean = MySqlOperator(
    task_id="create_table_clean",
    mysql_conn_id="mysql_conn",
    sql=CREATE_TABLE_CLEAN,
    )

    create_table_clean_train = MySqlOperator(
    task_id="create_table_clean_train",
    mysql_conn_id="mysql_conn",
    sql=CREATE_TABLE_CLEAN_TRAIN
    )

    create_table_clean_test = MySqlOperator(
    task_id="create_table_clean_test",
    mysql_conn_id="mysql_conn",
    sql=CREATE_TABLE_CLEAN_TEST,
    )

    create_table_clean_val = MySqlOperator(
    task_id="create_table_clean_val",
    mysql_conn_id="mysql_conn",
    sql=CREATE_TABLE_CLEAN_VAL,
    )

    skip_table_creation = EmptyOperator(task_id="skip_table_creation")

    join_after_branch = EmptyOperator(
        task_id="join_after_branch",
        trigger_rule="none_failed_min_one_success"
    )

   
    insert_raw_data = PythonOperator(
        task_id="insert_raw_data",
        python_callable=insert_data,

    )

    clean_and_transform = PythonOperator(
        task_id="clean_and_transform",
        python_callable=read_data,
    )

    insert_train_test_val = PythonOperator(
        task_id="inserta_en_todas_las_tablas",
        python_callable=insert_train_test_split,
    )

    train_ml_model = PythonOperator(
        task_id="train_ml_model",
        python_callable=train_model,
    )

    promueve_a_produccion = PythonOperator(
    task_id="promueve_a_produccion",
    python_callable=promote_best_model,
    op_kwargs={'experiment_name': "proyecto_airflow",
               "metric": "accuracy",
               "model_name":"GradientBoostingModel"}
    ,
    dag=dag
    )


    # wait_for_model = FileSensor(
    #     task_id="wait_for_model_file",
    #     filepath=MODEL_PATH,
    #     fs_conn_id="fs_default",
    #     poke_interval=10,
    #     timeout=300,
    #     mode="poke",
    # )



    # --- Espera de 5 minutos entre corridas ---
    wait_between_runs = PythonOperator(
        task_id="wait_between_runs",
        python_callable=wait_five_minutes,
    )

    # --- Flujo del DAG ---S
    check_first_run_task >> [delete_table_raw,delete_table_clean,delete_table_test,delete_table_train,delete_table_val, skip_table_creation]
    delete_table_raw >> delete_table_clean >> delete_table_train >> delete_table_test >> delete_table_val >>create_table_raw >> create_table_clean >> create_table_clean_train>> create_table_clean_test >> create_table_clean_val  >>join_after_branch
    skip_table_creation >> join_after_branch
    join_after_branch >> insert_raw_data >> clean_and_transform >> insert_train_test_val >> train_ml_model >> promueve_a_produccion >> wait_between_runs
