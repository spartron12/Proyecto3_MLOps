import logging
import pandas as pd
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from airflow.providers.mysql.hooks.mysql import MySqlHook
import os
import requests
from datetime import datetime
import mlflow
from mlflow.tracking import MlflowClient
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
import re
import json

def safe_int(value):
    """Convierte a int si es posible, de lo contrario devuelve 0"""
    try:
        if pd.isna(value) or value is None:
            return 0
        return int(value)
    except Exception:
        return 0

def safe_bool(value):
    """Convierte a bool seguro"""
    try:
        if pd.isna(value) or value is None:
            return False
        return bool(int(value))
    except Exception:
        return bool(value)

def map_diag(diag):
    if pd.isnull(diag):
        return 'Unknown'
    diag = str(diag).strip()

    # Algunos registros tienen letras (como 'E11', 'V45', etc.)
    if diag.startswith('V') or diag.startswith('E'):
        return 'Other'

    try:
        code = float(diag)
    except ValueError:
        return 'Other'

    # Clasificación basada en rangos ICD-9
    if 390 <= code <= 459 or code == 785:
        return 'Circulatory'
    elif 460 <= code <= 519 or code == 786:
        return 'Respiratory'
    elif 520 <= code <= 579 or code == 787:
        return 'Digestive'
    elif 250 <= code < 251:
        return 'Diabetes'
    elif 800 <= code <= 999:
        return 'Injury'
    elif 710 <= code <= 739:
        return 'Musculoskeletal'
    elif 580 <= code <= 629:
        return 'Genitourinary'
    elif 140 <= code <= 239:
        return 'Neoplasms'
    else:
        return 'Other'


MODEL_PATH = "/opt/airflow/models/GradientBoosting.pkl"
TABLE_NAME = "diabetes_raw"
CONN_ID = "mysql_conn"


def load_data(api_url="http://54.172.84.220:5001/get_data"):
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()

        # Convertir respuesta a texto y reemplazar NaN por null
        text = response.text
        text = re.sub(r'\bNaN\b', 'null', text)

        data = json.loads(text)  # Parsear manualmente

        if "message" in data:
            print("No hay datos disponibles.")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        print(f"Cargado chunk con {len(df)} filas.")
        return df

    except Exception as e:
        print(f" Error en load_data: {e}")
        return pd.DataFrame()


def insert_data():
    """Inserta datos en la tabla diabetes_raw"""
    df = load_data()
    print(df.shape)

    df['A1Cresult'] = df['A1Cresult'].fillna('0')
    df['max_glu_serum'] = df['max_glu_serum'].fillna('0')
    print(f"DataFrame cargado con {len(df)} filas para insertar.")
    hook = MySqlHook(mysql_conn_id=CONN_ID)
    df.columns = df.columns.str.replace('-', '_').str.strip()
    df = df.rename(columns={'change': 'cambio'})
    df['gender'] = df['gender'].replace('Unknown/Invalid', 'Male')
    df['race'] = df['race'].replace('?', 'Hispanic')
    
    print("Insertando datos en la tabla diabetes_raw..."    )
    print(df.head())
    print("columnas")
    print(df.columns)

    insert_sql = f"""
    INSERT INTO {TABLE_NAME} 
        (A1Cresult, acarbose, acetohexamide, admission_source_id,
        admission_type_id, age, cambio, chlorpropamide, citoglipton,
        diabetesMed, diag_1, diag_2, diag_3, discharge_disposition_id,
        encounter_id, examide, gender, glimepiride,
        glimepiride_pioglitazone, glipizide, glipizide_metformin,
        glyburide, glyburide_metformin, insulin, max_glu_serum,
        medical_specialty, metformin, metformin_pioglitazone,
        metformin_rosiglitazone, miglitol, nateglinide,
        num_lab_procedures, num_medications, num_procedures,
        number_diagnoses, number_emergency, number_inpatient,
        number_outpatient, patient_nbr, payer_code, pioglitazone,
        race, readmitted, repaglinide, rosiglitazone,
        time_in_hospital, tolazamide, tolbutamide, troglitazone,
        weight)
    VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s
    )
"""

    values = [
        (
            row["A1Cresult"],
            row["acarbose"],
            row["acetohexamide"],
            int(row["admission_source_id"]),
            int(row["admission_type_id"]),
            row["age"],
            row["cambio"],                      # corresponde a "change"
            row["chlorpropamide"],
            row["citoglipton"],
            row["diabetesMed"],
            row["diag_1"],
            row["diag_2"],
            row["diag_3"],
            int(row["discharge_disposition_id"]),
            int(row["encounter_id"]),
            row["examide"],
            row["gender"],
            row["glimepiride"],
            row["glimepiride_pioglitazone"],
            row["glipizide"],
            row["glipizide_metformin"],
            row["glyburide"],
            row["glyburide_metformin"],
            row["insulin"],
            row["max_glu_serum"],
            row["medical_specialty"],
            row["metformin"],
            row["metformin_pioglitazone"],
            row["metformin_rosiglitazone"],
            row["miglitol"],
            row["nateglinide"],
            int(row["num_lab_procedures"]),
            int(row["num_medications"]),
            int(row["num_procedures"]),
            int(row["number_diagnoses"]),
            int(row["number_emergency"]),
            int(row["number_inpatient"]),
            int(row["number_outpatient"]),
            int(row["patient_nbr"]),
            row["payer_code"],
            row["pioglitazone"],
            row["race"],
            row["readmitted"],
            row["repaglinide"],
            row["rosiglitazone"],
            int(row["time_in_hospital"]),
            row["tolazamide"],
            row["tolbutamide"],
            row["troglitazone"],
            row["weight"],
        )
        for _, row in df.iterrows()
    ]
    conn = hook.get_conn()
    cursor = conn.cursor()
    cursor.executemany(insert_sql, values)
    conn.commit()
    cursor.close()
    conn.close()

    print(f"{len(values)} registros insertados en {TABLE_NAME}")


def clean(df):
    """Limpia el DataFrame y crea variables dummy"""
    df['max_glu_serum'] = df['max_glu_serum'].fillna('0')
    mapping_glu = {'0': 0, 'Norm': 1, '>200': 2, '>300': 3}
    df['max_glu_serum'] = df['max_glu_serum'].map(mapping_glu)

    df['A1Cresult'] = df['A1Cresult'].fillna('0')
    mapping_a1c = {'0': 0, 'Norm': 1, '>7': 2, '>8': 3}
    df['A1Cresult'] = df['A1Cresult'].map(mapping_a1c)

    for col in ['diag_1', 'diag_2', 'diag_3']:
        df[col] = df[col].apply(map_diag)

    df.drop(
        columns=[
            'encounter_id', 'patient_nbr', 'admission_type_id',
            'medical_specialty', 'weight', 'examide', 'citoglipton'
        ],
        inplace=True
    )

    cols_to_keep = [
        'race', 'gender', 'age',
        'discharge_disposition_id', 'admission_source_id',
        'time_in_hospital', 'num_lab_procedures', 'num_procedures',
        'num_medications', 'number_outpatient', 'number_emergency',
        'number_inpatient', 'number_diagnoses',
        'max_glu_serum', 'A1Cresult',
        'cambio', 'diabetesMed',
        'diag_1', 'diag_2', 'diag_3',
        'readmitted'
    ]

    df_clean = df[cols_to_keep]
    categorical_columns = [
        'race', 'gender', 'age', 'cambio', 'diabetesMed', 'diag_1', 'diag_2', 'diag_3'
    ]

    df_encoded = pd.get_dummies(df_clean, columns=categorical_columns, drop_first=False)
    return df_encoded


def insert_data_clean(df = None, table_name="diabetes_clean"):
    """Inserta datos en la tabla diabetes_clean"""

    df = df.replace({None: np.nan}).fillna(0)
    
    # Reemplazar todos los tipos de valores nulos posibles

    hook = MySqlHook(mysql_conn_id=CONN_ID)
    TABLE_NAME = "diabetes_clean"

    insert_sql = f"""
    INSERT INTO {table_name} (
        discharge_disposition_id, admission_source_id, time_in_hospital,
        num_lab_procedures, num_procedures, num_medications,
        number_outpatient, number_emergency, number_inpatient,
        number_diagnoses, max_glu_serum, A1Cresult, readmitted,
        race_AfricanAmerican, race_Asian, race_Caucasian, race_Hispanic, race_Other,
        gender_Female, gender_Male,
        `age_[0-10)`, `age_[10-20)`, `age_[20-30)`, `age_[30-40)`, `age_[40-50)`,
        `age_[50-60)`, `age_[60-70)`, `age_[70-80)`, `age_[80-90)`, `age_[90-100)`,
        cambio_Ch, cambio_No, diabetesMed_No, diabetesMed_Yes,
        diag_1_Circulatory, diag_1_Diabetes, diag_1_Digestive, diag_1_Genitourinary,
        diag_1_Injury, diag_1_Musculoskeletal, diag_1_Neoplasms, diag_1_Other, diag_1_Respiratory,
        diag_2_Circulatory, diag_2_Diabetes, diag_2_Digestive, diag_2_Genitourinary,
        diag_2_Injury, diag_2_Musculoskeletal, diag_2_Neoplasms, diag_2_Other, diag_2_Respiratory,
        diag_3_Circulatory, diag_3_Diabetes, diag_3_Digestive, diag_3_Genitourinary,
        diag_3_Injury, diag_3_Musculoskeletal, diag_3_Neoplasms, diag_3_Other, diag_3_Respiratory
    )
    VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s
    )
"""
    def safe_int(value):
        """Convierte a int de forma segura"""
        if value is None or pd.isna(value):
            return None
        try:
            return int(float(value))  # float primero por si es decimal
        except (ValueError, TypeError):
            return None
    
    def safe_bool(value):
        """Convierte a bool de forma segura"""
        if value is None or pd.isna(value):
            return False
        try:
            return bool(int(float(value)))
        except (ValueError, TypeError):
            return False
        
    values = [
        (
            safe_int(row["discharge_disposition_id"]),
            safe_int(row["admission_source_id"]),
            safe_int(row["time_in_hospital"]),
            safe_int(row["num_lab_procedures"]),
            safe_int(row["num_procedures"]),
            safe_int(row["num_medications"]),
            safe_int(row["number_outpatient"]),
            safe_int(row["number_emergency"]),
            safe_int(row["number_inpatient"]),
            safe_int(row["number_diagnoses"]),
            safe_int(row["max_glu_serum"]),
            safe_int(row["A1Cresult"]),
            row["readmitted"],
            safe_bool(row["race_AfricanAmerican"]),
            safe_bool(row["race_Asian"]),
            safe_bool(row["race_Caucasian"]),
            safe_bool(row["race_Hispanic"]),
            safe_bool(row["race_Other"]),
            safe_bool(row["gender_Female"]),
            safe_bool(row["gender_Male"]),
            safe_bool(row["age_[0-10)"]),
            safe_bool(row["age_[10-20)"]),
            safe_bool(row["age_[20-30)"]),
            safe_bool(row["age_[30-40)"]),
            safe_bool(row["age_[40-50)"]),
            safe_bool(row["age_[50-60)"]),
            safe_bool(row["age_[60-70)"]),
            safe_bool(row["age_[70-80)"]),
            safe_bool(row["age_[80-90)"]),
            safe_bool(row["age_[90-100)"]),
            safe_bool(row["cambio_Ch"]),
            safe_bool(row["cambio_No"]),
            safe_bool(row["diabetesMed_No"]),
            safe_bool(row["diabetesMed_Yes"]),
            safe_bool(row["diag_1_Circulatory"]),
            safe_bool(row["diag_1_Diabetes"]),
            safe_bool(row["diag_1_Digestive"]),
            safe_bool(row["diag_1_Genitourinary"]),
            safe_bool(row["diag_1_Injury"]),
            safe_bool(row["diag_1_Musculoskeletal"]),
            safe_bool(row["diag_1_Neoplasms"]),
            safe_bool(row["diag_1_Other"]),
            safe_bool(row["diag_1_Respiratory"]),
            safe_bool(row["diag_2_Circulatory"]),
            safe_bool(row["diag_2_Diabetes"]),
            safe_bool(row["diag_2_Digestive"]),
            safe_bool(row["diag_2_Genitourinary"]),
            safe_bool(row["diag_2_Injury"]),
            safe_bool(row["diag_2_Musculoskeletal"]),
            safe_bool(row["diag_2_Neoplasms"]),
            safe_bool(row["diag_2_Other"]),
            safe_bool(row["diag_2_Respiratory"]),
            safe_bool(row["diag_3_Circulatory"]),
            safe_bool(row["diag_3_Diabetes"]),
            safe_bool(row["diag_3_Digestive"]),
            safe_bool(row["diag_3_Genitourinary"]),
            safe_bool(row["diag_3_Injury"]),
            safe_bool(row["diag_3_Musculoskeletal"]),
            safe_bool(row["diag_3_Neoplasms"]),
            safe_bool(row["diag_3_Other"]),
            safe_bool(row["diag_3_Respiratory"])
        )
        for _, row in df.iterrows()
    ]

    conn = hook.get_conn()
    cursor = conn.cursor()
    cursor.executemany(insert_sql, values)
    conn.commit()
    cursor.close()
    conn.close()

    print(f"{len(values)} registros insertados en {table_name}")


def read_data():
    """Lee, limpia y carga datos en diabetes_clean de forma dinámica"""
    hook = MySqlHook(mysql_conn_id=CONN_ID)

    print("Leyendo datos desde diabetes_raw...")
    query = "SELECT * FROM diabetes_raw"
    df = hook.get_pandas_df(sql=query)
    print(f"{len(df)} registros leídos")

    print("Limpiando datos y creando variables dummy...")
    cleaned_df = clean(df)
    dag_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(dag_dir, "datos_fast.csv")
    cleaned_df.to_csv(output_path, index=False, encoding="utf-8")
    print("base exportada exitosamente")
    print(f"DataFrame limpio: {cleaned_df.shape}")
    print(f"Columnas generadas: {len(cleaned_df.columns)}")

    
    insert_data_clean(cleaned_df, table_name="diabetes_clean")
    print("\nProceso completo: Limpieza e inserción terminada")
    return cleaned_df

def insert_train_test_split():
    """Realiza el split de los datos limpios en train y test e inserta en sus respectivas tablas"""
    hook = MySqlHook(mysql_conn_id=CONN_ID)
    query = "SELECT * FROM diabetes_clean"
    df = hook.get_pandas_df(sql=query)

    x = df.drop(columns=['readmitted'])
    y = df['readmitted'].replace({'>30': 1, '<30': 1, 'NO': 0})

    X_train, X_temp, y_train, y_temp = train_test_split(
        x, y, test_size=0.3, random_state=42, stratify=y
    )

    X_Val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.33, random_state=42, stratify=y_temp
    )
    
    x_train_concat = pd.concat([X_train, y_train.reset_index(drop=True)], axis=1)
    x_val_concat = pd.concat([X_Val, y_val.reset_index(drop=True)], axis=1)
    x_test_concat = pd.concat([X_test, y_test.reset_index(drop  =True)], axis=1)    


    train_df = X_train.copy()
    train_df['readmitted'] = y_train

    test_df = X_test.copy()
    test_df['readmitted'] = y_test

    insert_data_clean(x_train_concat , table_name="diabetes_clean_train")
    insert_data_clean(x_val_concat, table_name="diabetes_clean_val")
    insert_data_clean(x_test_concat , table_name="diabetes_clean_test")

    print("Datos de entrenamiento y prueba insertados correctamente.")

def train_model():
    hook = MySqlHook(mysql_conn_id=CONN_ID)
    query = "SELECT * FROM diabetes_clean_train"
    df = hook.get_pandas_df(sql=query)
    df = df.rename(columns={
    'age_[0-10)': 'age_0_10',
    'age_[10-20)': 'age_10_20',
    'age_[20-30)': 'age_20_30',
    'age_[30-40)': 'age_30_40',
    'age_[40-50)': 'age_40_50',
    'age_[50-60)': 'age_50_60',
    'age_[60-70)': 'age_60_70',
    'age_[70-80)': 'age_70_80',
    'age_[80-90)': 'age_80_90',
    'age_[90-100)': 'age_90_100'})

    print("Columnas después del rename:", df.columns.tolist())

    X_train = df.drop(columns=['readmitted'])
    y_train = df['readmitted']
    print('='*100)
    print("\n Tipos de variables en X_train:")
    for col, dtype in X_train.dtypes.items():
        print(f"  {col}: {dtype}")
    print("\n Tipo de variable objetivo (y_train):", y_train.dtype)


    model = GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=3,
        random_state=42
    )
    model.fit(X_train, y_train)

    # Validación
    query = "SELECT * FROM diabetes_clean_val"


    df_val = hook.get_pandas_df(sql=query)
    df_val = df_val.rename(columns={
    'age_[0-10)': 'age_0_10',
    'age_[10-20)': 'age_10_20',
    'age_[20-30)': 'age_20_30',
    'age_[30-40)': 'age_30_40',
    'age_[40-50)': 'age_40_50',
    'age_[50-60)': 'age_50_60',
    'age_[60-70)': 'age_60_70',
    'age_[70-80)': 'age_70_80',
    'age_[80-90)': 'age_80_90',
    'age_[90-100)': 'age_90_100'})

    print("Columnas después del rename:", df_val.columns.tolist())
    X_val = df_val.drop(columns=['readmitted'])
    y_val = df_val['readmitted']

    print("Columnas después del rename:", X_val.columns.tolist())
    y_pred = model.predict(X_val)
    accuracy = accuracy_score(y_val, y_pred)
    print("Accuracy:", accuracy)

    # === Configuración MLflow ===
    experiment_name = "proyecto_airflow"
    os.environ['MLFLOW_S3_ENDPOINT_URL'] = "http://minio:9000"
    os.environ['AWS_ACCESS_KEY_ID'] = 'admin'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'supersecret'
    mlflow.set_tracking_uri("http://10.43.100.98:8084")
    mlflow.set_experiment(experiment_name)
    print(f" Conectando a MLflow en http://10.43.100.98:8084")

    # Obtener ID del experimento
    experiment = mlflow.get_experiment_by_name(experiment_name)
    experiment_id = experiment.experiment_id

    # Nombrar corrida incrementalmente
    runs = mlflow.search_runs(experiment_ids=[experiment_id])
    run_number = len(runs) + 1
    run_name = f"GradientBoosting{run_number}"

    # === Registro de la corrida ===
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_param("random_state", 42)
        mlflow.log_metric("accuracy", accuracy)
        mlflow.sklearn.log_model(model, artifact_path="GradientBoostingModel")

        print(f" Run registrado en MLflow con nombre: {run_name}")

        # Registrar modelo en el Model Registry
        model_uri = f"runs:/{run.info.run_id}/GradientBoostingModel"
        result = mlflow.register_model(model_uri=model_uri, name="GradientBoostingModel")
        print(f" Modelo registrado con nombre='GradientBoostingModel' y versión={result.version}")

    # Guardar modelo localmente también (opcional)
    os.makedirs('/opt/airflow/models', exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"Modelo guardado localmente en: {MODEL_PATH}")


logger = logging.getLogger(__name__)

def promote_best_model():
    print(" Promoviendo el mejor modelo a Production...")

    # Configuración MLflow (igual que en train_model)
    os.environ['MLFLOW_S3_ENDPOINT_URL'] = "http://minio:9000"
    os.environ['AWS_ACCESS_KEY_ID'] = 'admin'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'supersecret'
    mlflow.set_tracking_uri("http://10.43.100.98:8084")

    client = MlflowClient()
    model_name = "GradientBoostingModel"

    try:
        # Obtener todas las versiones registradas
        versions = client.search_model_versions(f"name='{model_name}'")

        if not versions:
            print(" No hay versiones del modelo registradas.")
            return

        # Buscar la versión con mejor accuracy (loggeada como metric)
        best_version = None
        best_accuracy = -1

        for v in versions:
            run_id = v.run_id
            run_data = client.get_run(run_id).data
            acc = run_data.metrics.get("accuracy", 0)

            if acc > best_accuracy:
                best_accuracy = acc
                best_version = v.version

        print(f" Mejor modelo encontrado: versión {best_version} con accuracy={best_accuracy:.4f}")

        # Promover a Production
        client.transition_model_version_stage(
            name=model_name,
            version=best_version,
            stage="Production",
            archive_existing_versions=True
        )

        print(f" Modelo {model_name} v{best_version} promovido a Production con accuracy={best_accuracy:.4f}")

    except Exception as e:
        print(f" Error al promover modelo: {e}")

    print(" ¡Proceso completado exitosamente!")

    
def check_table_exists(**kwargs):
    from airflow.providers.mysql.hooks.mysql import MySqlHook
    hook = MySqlHook(mysql_conn_id="mysql_conn")
    query = "SHOW TABLES LIKE 'diabetes_raw';"
    df = hook.get_pandas_df(query)
    if df.empty:
        return "create_table_raw"
    else:
        return "insert_raw_data"
