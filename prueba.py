import sys
import os
import time
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import palmerpenguins as pp


def prueba_modelo():
    # ============================================================
    # 1. Cargar y preparar los datos
    # ============================================================
    print("📘 Cargando datos de penguins...")
    df = pp.load_penguins()
    df.dropna(inplace=True)

    # Codificar variables categóricas
    df_encoded = pd.get_dummies(df, columns=['island', 'sex'])
    bool_cols = df_encoded.select_dtypes(include='bool').columns
    df_encoded[bool_cols] = df_encoded[bool_cols].astype(int)

    df_encoded['species'] = df_encoded['species'].apply(lambda x:
                            1 if x == 'Adelie' else
                            2 if x == 'Chinstrap' else
                            3 if x == 'Gentoo' else None)

    # ============================================================
    # 2. Configurar MLflow
    # ============================================================
    os.environ['MLFLOW_S3_ENDPOINT_URL'] = "http://minio:9000"
    os.environ['AWS_ACCESS_KEY_ID'] = 'admin'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'supersecret'
    mlflow.set_tracking_uri("http://10.43.100.98:8084")
    print(f"🔗 Conectando a MLflow en http://10.43.100.98:8084")
    mlflow.set_experiment("experimento")

    # ============================================================
    # 3. Entrenar el modelo
    # ============================================================
    print("⚙️ Entrenando modelo...")
    X = df_encoded.drop("species", axis=1)
    y = df_encoded["species"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = LogisticRegression(max_iter=5000)
    model.fit(X_train, y_train)

    # ============================================================
    # 4. Loguear y registrar el modelo en MLflow
    # ============================================================
    print("🧾 Registrando modelo en MLflow...")

   

    with mlflow.start_run(run_name="logistic_regression_run") as run:
        mlflow.log_param("artifact_bucket", "s3://mlflow")
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        mlflow.log_metric("accuracy", acc)

        # Log del modelo
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            input_example=X_test.head(1)
        )

        print(f"✅ Modelo logueado con accuracy = {acc:.4f}")

        # Guardar el run_id antes de cerrar el contexto
        run_id = run.info.run_id

    # ============================================================
    # 5. Registrar modelo en el Model Registry
    # ============================================================
    run_uri = f"runs:/{run_id}/model"
    mlflow.register_model(run_uri, "logistic_regression")
    # 6. Promover el modelo a Producción

    client = MlflowClient()

    # ============================================================
    model_name = "logistic_regression"
    model_version = 1  # Asumiendo que es la versión 1
    try:
        client.transition_model_version_stage(
            name=model_name,
            version=model_version,
            stage="Production",
            archive_existing_versions=True
        )
        print(f"🚀 Modelo {model_name} v{model_version} promovido a 'Production'")
    except Exception as e:
        print(f"⚠️ Error al promover modelo: {e}")

    print("🎉 ¡Proceso completado exitosamente!")


# ============================================================
# DAG de Airflow
# ============================================================
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id="orquestador",
    default_args=default_args,
    description="Pipeline de entrenamiento y registro con MLflow",
    start_date=datetime(2025, 11, 1),
    schedule_interval="*/10 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["ml", "mlflow", "penguins"],
) as dag:

    inicio = EmptyOperator(task_id="inicio")

    tarea_prueba_modelo = PythonOperator(
        task_id="prueba_modelo",
        python_callable=prueba_modelo
    )

    fin = EmptyOperator(task_id="fin")

    inicio >> tarea_prueba_modelo >> fin