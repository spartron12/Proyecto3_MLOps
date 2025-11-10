# MLOps Proyecto 3 

**Grupo:** Sebastián Rodríguez y David Córdova  
**Curso:** Machine Learning Operations (MLOps)  
**Profesor:** Cristian Javier Diaz Alvarez  
**Institución:** Pontificia Universidad Javeriana  
**Fecha:** Noviembre 2025

---

##  Descripción del Proyecto

Este proyecto implementa un **sistema completo de MLOps desplegado en Kubernetes** que automatiza todo el ciclo de vida del Machine Learning: desde la recolección y procesamiento de datos hasta el entrenamiento de modelos, despliegue en producción y monitoreo continuo.


### Objetivos Principales

 **Orquestación con Apache Airflow**: Creación de DAGs para la recolección, procesamiento y almacenamiento de datos de manera automatizada.  

 **Registro de experimentos con MLflow**: Seguimiento de modelos y artefactos con un backend SQL (MySQL) para metadatos y almacenamiento de artefactos en un bucket S3.  

 **API de Inferencia con FastAPI**: Creación de una API para consumir el modelo de mejor desempeño desde MLflow y exponerla para inferencias.  

 **Interfaz de usuario con Streamlit**: Desarrollo de una interfaz gráfica interactiva para permitir a los usuarios realizar predicciones de forma sencilla e intuitiva.  

 **Observabilidad con Prometheus y Grafana**: Monitoreo de métricas del sistema y creación de dashboards visuales para observar el rendimiento y uso de la infraestructura.  

 **Pruebas de carga con Locust**: Evaluación de la capacidad máxima de usuarios concurrentes para asegurar que la infraestructura soporte una alta carga de trabajo.  

 **Infraestructura AWS**: Despliegue de la API de datos en EC2, con encendido y apagado automático para optimizar el uso de recursos en función de la demanda.  

 **Despliegue en Kubernetes**: Orquestación de los servicios principales (FastAPI, Streamlit, Prometheus, Grafana) en contenedores dentro de un clúster de Kubernetes, mientras que Airflow y MLflow corren fuera de Kubernetes pero se integran con el resto de los servicios.





##  Dataset: Diabetes 130-US Hospitals (1999-2008)

### Descripción

El conjunto de datos representa **10 años de atención clínica en 130 hospitales de EE.UU.** Incluye más de **50 características** que representan los resultados del paciente y del hospital.

**Criterios de inclusión:**
- Encuentro de paciente hospitalizado (ingreso al hospital)
- Encuentro diabético con diagnóstico de cualquier tipo de diabetes
- Duración de estadia: mínimo 1 día, máximo 14 días
- Pruebas de laboratorio realizadas durante el encuentro
- Medicamentos administrados durante el encuentro

**Características incluyen:**
- Número de paciente, raza, sexo, edad
- Tipo de ingreso, tiempo en el hospital
- Especialidad médica del médico admitente
- Número de pruebas de laboratorio realizadas
- Resultado de la prueba de HbA1c
- Diagnóstico, número de medicamentos
- Medicamentos para la diabetes
- Visitas ambulatorias, hospitalizaciones y emergencias del año anterior

**Fuente:** [Diabetes 130-US hospitals for years 1999-2008](https://archive.ics.uci.edu/ml/datasets/Diabetes+130-US+hospitals+for+years+1999-2008)

---

##  Arquitectura del Sistema

![Arquitectura MLOps](images/arquitectura.png)

### Diagrama de Flujo Completo

```

┌────────────────────────────────────────────────────────────────────────────┐
│                           AWS INFRASTRUCTURE                               │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────┐    9:00 AM    ┌────────────────────────────────┐         │
│  │ EventBridge  │──────────────>│  StartEC2Instance (Lambda)     │         │
│  │   Schedule   │               │  Python 3.11                   │         │
│  └──────────────┘               └───────────────┬────────────────┘         │
│                                                  │                         │
│                                                  ▼                         │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │              EC2 Instance (mlops_api)                           │       │
│  │              Instance ID: i-0b1fe2e74b0578256                   │       │
│  │              Type: t3.micro | OS: Ubuntu                        │       │
│  │  ┌───────────────────────────────────────────────────────────┐  │       │
│  │  │   Docker Container - Diabetes API (Flask)                 │  │       │
│  │  │   • Port: 5001                                            │  │       │
│  │  │   • Endpoint: /get_data                                   │  │       │
│  │  │   • Batch size: 15,000 registros                          │  │       │
│  │  │   • Update interval: 5 minutos                            │  │       │
│  │  │   • Auto-restart: enabled                                 │  │       │
│  │  └───────────────────────────────────────────────────────────┘  │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                  │                                         │
│                                  │ 11:55 PM                                │
│                                  ▼                                         │
│  ┌──────────────┐          ┌────────────────────────────────┐              │
│  │ EventBridge  │─────────>│  StopEC2Instance (Lambda)      │              │
│  │   Schedule   │          │  Python 3.11                   │              │
│  └──────────────┘          └────────────────────────────────┘              │
└────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ HTTP GET (cada 5 min)
                                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    KUBERNETES CLUSTER (LOCAL/CLOUD)                        │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────┐        │
│  │                    Apache Airflow                              │        │
│  │  ┌─────────────────────────────────────────────────────────┐   │        │
│  │  │  DAG: orquestador.py (Ejecución periódica)              │   │        │
│  │  │                                                         │   │        │
│  │  │  1. ✓ Check EC2 Status                                  │   │        │
│  │  │  2. ✓ Fetch Data from API (15k registros)               │   │        │
│  │  │  3. ✓ Store in MySQL RAW_DATA                           │   │        │
│  │  │  4. ✓ Data Cleaning & Feature Engineering               │   │        │
│  │  │  5. ✓ Store in MySQL CLEAN_DATA                         │   │        │
│  │  │  6. ✓ Create Train/Validation/Test splits               │   │        │
│  │  │  7. ✓ Upload processed data to MinIO                    │   │        │
│  │  │  8. ✓ Train Multiple Models                             │   │        │
│  │  │  9. ✓ Register Experiments in MLflow                    │   │        │
│  │  │  10. ✓ Promote Best Model to Production                 │   │        │
│  │  │  11. ✓ Signal FastAPI & Streamlit Ready                 │   │        │
│  │  └─────────────────────────────────────────────────────────┘   │        │
│  └────────────────────────────────────────────────────────────────┘        │
│           │                    │                    │                      │
│           ▼                    ▼                    ▼                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────┐          │
│  │  MySQL DB       │  │  MinIO Bucket   │  │  MLflow Server     │          │
│  │  ─────────────  │  │  ─────────────  │  │  ───────────────   │          │
│  │  • RAW_DATA     │  │  • Artifacts    │  │  • Tracking UI     │          │
│  │  • CLEAN_DATA   │  │  • Models       │  │  • Model Registry  │          │
│  │  • TRAIN_DATA   │  │  • Metrics      │  │  • Experiments     │          │
│  │  • VAL_DATA     │  │  • Datasets     │  │  • Production Tag  │          │
│  │  • TEST_DATA    │  │                 │  │                    │          │
│  │  • METADATA_DB  │  │  Backend: S3    │  │  Backend: MySQL    │          │
│  └─────────────────┘  └─────────────────┘  └────────────────────┘          │
│                                  │                  │                      │
│                                  └──────────┬───────┘                      │
│                                             │                              │
│                                             ▼                              │
│  ┌───────────────────────────────────────────────────────────────┐         │
│  │                    Inference Layer                            │         │
│  │  ┌──────────────────────┐      ┌──────────────────────────┐   │         │
│  │  │  FastAPI Server      │      │  Streamlit UI            │   │         │
│  │  │  ─────────────────   │      │  ──────────────────      │   │         │
│  │  │  • /predict          │◄────►│  • Input Form            │   │         │
│  │  │  • /health           │      │  • Prediction Display    │   │         │
│  │  │  • /metrics          │      │  • Model Version Info    │   │         │
│  │  │  • Auto-load from    │      │  • Feature Engineering   │   │         │
│  │  │    MLflow Production │      │  • Batch Prediction      │   │         │
│  │  └──────────────────────┘      └──────────────────────────┘   │         │
│  └───────────────────────────────────────────────────────────────┘         │
│                         │                                                  │
│                         │ Expose /metrics                                  │
│                         ▼                                                  │
│  ┌───────────────────────────────────────────────────────────────┐         │
│  │                 Observability Stack                           │         │
│  │  ┌────────────────────┐       ┌──────────────────────────┐    │         │
│  │  │  Prometheus        │──────>│  Grafana                 │    │         │
│  │  │  ────────────────  │       │  ──────────────────      │    │         │
│  │  │  • Scrape /metrics │       │  • Dashboards            │    │         │
│  │  │  • Time-series DB  │       │  • Alerting              │    │         │
│  │  │  • Targets:        │       │  • Visualizations        │    │         │
│  │  │    - FastAPI       │       │  • System Metrics        │    │         │
│  │  │    - Airflow       │       │  • Model Performance     │    │         │
│  │  │    - K8s Nodes     │       │  • API Latency           │    │         │
│  │  └────────────────────┘       └──────────────────────────┘    │         │
│  └───────────────────────────────────────────────────────────────┘         │
│                                                                            │
│  ┌───────────────────────────────────────────────────────────────┐         │
│  │                    Load Testing                               │         │ 
│  │  ┌─────────────────────────────────────────────────────────┐  │         │
│  │  │  Locust                                                 │  │         │
│  │  │  ────────────────────────────────────────────────────── │  │         │
│  │  │  • Simulate concurrent users                            │  │         │
│  │  │  • Test /predict endpoint                               │  │         │
│  │  │  • Measure response times                               │  │         │
│  │  │  • Determine max capacity                               │  │         │
│  │  │  • Generate performance reports                         │  │         │
│  │  └─────────────────────────────────────────────────────────┘  │         │
│  └───────────────────────────────────────────────────────────────┘         │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘


```

---

##  Estructura del Proyecto

```
Proyecto3_MLOps/
├── dags/
│   ├── __pycache__/
│   ├── scripts/
│   │   ├── funciones.py              # Funciones de procesamiento, limpieza y ML
│   │   └── queries.py                # Queries SQL para MySQL
│   └── orquestador.py                # DAG principal de Airflow
│
├── fastapi/
│   ├── __pycache__/
│   ├── Dockerfile
│   ├── main.py                       # API de inferencia
│   ├── requirements.txt
│   └── models/                       # Modelos cargados desde MLflow
│
├── streamlit/
│   ├── app.py                        # Interfaz de usuario
│   ├── Dockerfile
│   └── requirements.txt
│
├── grafana/
│   └── provisioning/
│       ├── datasources/              # Configuración Prometheus datasource
│       └── dashboards/               # Dashboards JSON
│           ├── mlops_overview.json
│           ├── api_performance.json
│           └── model_metrics.json
│
├── locust/
│   ├── locustfile.py                 # Tests de carga
│   └── Dockerfile
│
├── kubernetes/
│   ├── airflow/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── pvc.yaml
│   ├── mlflow/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── mysql/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── pvc.yaml
│   │   └── init-scripts/
│   │       └── create_databases.sql
│   ├── minio/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── pvc.yaml
│   ├── fastapi/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── streamlit/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   ├── prometheus/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── configmap.yaml
│   └── grafana/
│       ├── deployment.yaml
│       ├── service.yaml
│       └── pvc.yaml
│
├── aws/
│   ├── lambda/
│   │   ├── start_ec2_instance.py
│   │   ├── stop_ec2_instance.py
│   │   ├── start_ec2_instance.zip
│   │   └── stop_ec2_instance.zip
│   ├── policies/
│   │   ├── lambda-trust-policy.json
│   │   └── ec2-scheduler-policy.json
│   └── scripts/
│       ├── setup_ec2_scheduler.sh
│       ├── add_permissions.sh
│       └── update_schedule.sh
│
├── ec2_api/
│   ├── app.py                        # Flask API en EC2
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   ├── start_api.sh
│   └── data/
│       └── Diabetes/
│           └── Diabetes.csv
│
├── images/                           # Screenshots del proyecto
│   ├── arquitectura_mlops.png
│   ├── ec2_instance.png
│   ├── lambda_functions.png
│   ├── eventbridge_schedules.png
│   ├── schedule_start_detail.png
│   ├── schedule_stop_detail.png
│   ├── airflow_dag.png
│   ├── mlflow_experiments.png
│   ├── mysql_tables.png
│   ├── fastapi_docs.png
│   ├── streamlit_ui.png
│   ├── grafana_dashboard.png
│   └── locust_results.png
│
├── logs/                             # Logs de Airflow y servicios
├── minio/                            # Almacenamiento de objetos
├── models/                           # Modelos entrenados
│
├── .env                              # Variables de entorno
├── docker-compose.yaml               # Compose para desarrollo local
├── docker-compose-locust.yaml        # Compose para pruebas de carga
├── Dockerfile                        # Dockerfile de Airflow
├── Dockerfile_mlflow                 # Dockerfile de MLflow
├── prometheus.yml                    # Configuración de Prometheus
├── requirements.txt                  # Dependencias globales
├── requirements_mlflow.txt           # Dependencias de MLflow
└── README.md                         # Este archivo
```

---

## 🔧 Componentes del Sistema

### 1.  API de Datos en AWS EC2

#### Descripción
API Flask desplegada en EC2 que sirve datos de diabetes en bloques de 15,000 registros, con actualización automática cada 5 minutos y control de encendido/apagado mediante Lambda Functions.

#### Características
- **Instancia**: t3.micro en us-east-1b
- **IP Pública**: 54.172.84.220
- **DNS**: ec2-54-172-84-220.compute-1.amazonaws.com
- **Puerto**: 5001
- **Horario**: 9:00 AM - 11:55 PM (America/Lima)

#### Código de la API (app.py)

```python
from flask import Flask, jsonify
import pandas as pd
import os
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# Archivo de datos
_data_root = './data/Diabetes'
_data_filepath = os.path.join(_data_root, 'Diabetes.csv')

# Descargar los datos si no existen
def download_data():
    os.makedirs(_data_root, exist_ok=True)
    if not os.path.isfile(_data_filepath):
        url = 'https://docs.google.com/uc?export=download&confirm={{VALUE}}&id=1k5-1caezQ3zWJbKaiMULTGq-3sz6uThC'
        import requests
        r = requests.get(url, allow_redirects=True, stream=True)
        with open(_data_filepath, 'wb') as f:
            f.write(r.content)
        print(f'Datos descargados y guardados en {_data_filepath}')

download_data()

# Cargar dataset
df = pd.read_csv(_data_filepath)
total_rows = len(df)

# Configuración de chunks
chunk_size = 15000
current_index = 0

# Función para obtener el siguiente bloque
def get_next_chunk():
    global current_index
    start = current_index
    end = min(current_index + chunk_size, total_rows)
    chunk = df.iloc[start:end]
    
    # Actualizamos el índice para el siguiente ciclo
    current_index = end if end < total_rows else 0  # reinicia cuando se acaban
    return chunk.to_dict(orient='records')

# Rutas Flask
@app.route('/')
def home():
    return '''
    <h1>Bienvenido a la API de Diabetes</h1>
    <p>Accede a los datos en intervalos de 15,000 filas usando /get_data</p>
    '''

@app.route('/get_data', methods=['GET'])
def get_data():
    chunk = get_next_chunk()
    if not chunk:
        return jsonify({"message": "No hay más datos disponibles."}), 404
    return jsonify(chunk)

# Scheduler para actualizar cada 5 minutos
def update_data_periodically():
    print("Actualizando bloque de datos...")
    get_next_chunk()

scheduler = BackgroundScheduler()
scheduler.add_job(update_data_periodically, 'interval', minutes=5)
scheduler.start()

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5001)
    finally:
        scheduler.shutdown()
```

#### Configuración Docker en EC2

**Dockerfile:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5001

CMD ["python", "app.py"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  diabetes-api:
    build: .
    ports:
      - "5001:5001"
    volumes:
      - ./data:/app/data
      - ./log.txt:/app/log.txt
    restart: unless-stopped
    environment:
      - PYTHONUNBUFFERED=1
```

**start_api.sh:**
```bash
#!/bin/bash
cd /home/ubuntu/diabetes_api
docker-compose up -d
echo "API de Diabetes iniciada en puerto 5001"
docker-compose logs -f
```

#### Configuración de Auto-inicio

```bash
# Configurar para que Docker inicie automáticamente al encender EC2
sudo systemctl enable docker

# Agregar a crontab para inicio automático
crontab -e
# Añadir: @reboot sleep 60 && /home/ubuntu/diabetes_api/start_api.sh
```

---

### 2.  AWS Lambda Functions

#### StartEC2Instance

```python
# start_ec2_instance.py
import boto3
import json

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    instance_id = 'i-0b1fe2e74b0578256'
    
    try:
        response = ec2.start_instances(InstanceIds=[instance_id])
        print(f'Iniciando instancia {instance_id}')
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Instance {instance_id} started successfully',
                'response': str(response)
            })
        }
    except Exception as e:
        print(f'Error: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error starting instance: {str(e)}'
            })
        }
```

#### StopEC2Instance

```python
# stop_ec2_instance.py
import boto3
import json

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    instance_id = 'i-0b1fe2e74b0578256'
    
    try:
        response = ec2.stop_instances(InstanceIds=[instance_id])
        print(f'Deteniendo instancia {instance_id}')
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Instance {instance_id} stopped successfully',
                'response': str(response)
            })
        }
    except Exception as e:
        print(f'Error: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error stopping instance: {str(e)}'
            })
        }
```

---

### 3.  EventBridge Schedules

| Schedule | Cron Expression | Target | Status | Hora (Lima) |
|----------|----------------|--------|--------|-------------|
| `StartEC2Instance` | `55 8 * * ? *` | StartEC2Instance Lambda |  Enabled | 9:00 AM |
| `StopEC2Instance` | `55 23 * * ? *` | StopEC2Instance Lambda |  Enabled | 11:55 PM |

- **Timezone**: America/Lima (UTC-05:00)
- **Flexible time window**: OFF
- **Action after completion**: NONE

---

### 4.  MySQL - Bases de Datos

#### Esquema de Bases de Datos

```sql
-- Base de datos para metadatos de MLflow
CREATE DATABASE mlflow_db;

-- Base de datos para datos crudos
CREATE DATABASE raw_data_db;

-- Base de datos para datos limpios
CREATE DATABASE clean_data_db;

-- Tablas en raw_data_db
USE raw_data_db;

CREATE TABLE diabetes_raw (
    id INT AUTO_INCREMENT PRIMARY KEY,
    encounter_id INT,
    patient_nbr INT,
    race VARCHAR(50),
    gender VARCHAR(20),
    age VARCHAR(20),
    weight VARCHAR(20),
    admission_type_id INT,
    discharge_disposition_id INT,
    admission_source_id INT,
    time_in_hospital INT,
    payer_code VARCHAR(20),
    medical_specialty VARCHAR(100),
    num_lab_procedures INT,
    num_procedures INT,
    num_medications INT,
    number_outpatient INT,
    number_emergency INT,
    number_inpatient INT,
    diag_1 VARCHAR(20),
    diag_2 VARCHAR(20),
    diag_3 VARCHAR(20),
    number_diagnoses INT,
    max_glu_serum VARCHAR(20),
    A1Cresult VARCHAR(20),
    metformin VARCHAR(20),
    repaglinide VARCHAR(20),
    nateglinide VARCHAR(20),
    chlorpropamide VARCHAR(20),
    glimepiride VARCHAR(20),
    acetohexamide VARCHAR(20),
    glipizide VARCHAR(20),
    glyburide VARCHAR(20),
    tolbutamide VARCHAR(20),
    pioglitazone VARCHAR(20),
    rosiglitazone VARCHAR(20),
    acarbose VARCHAR(20),
    miglitol VARCHAR(20),
    troglitazone VARCHAR(20),
    tolazamide VARCHAR(20),
    examide VARCHAR(20),
    citoglipton VARCHAR(20),
    insulin VARCHAR(20),
    glyburide_metformin VARCHAR(20),
    glipizide_metformin VARCHAR(20),
    glimepiride_pioglitazone VARCHAR(20),
    metformin_rosiglitazone VARCHAR(20),
    metformin_pioglitazone VARCHAR(20),
    change_medication VARCHAR(20),
    diabetesMed VARCHAR(20),
    readmitted VARCHAR(20),
    batch_number INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_batch (batch_number),
    INDEX idx_created (created_at)
);

-- Tablas en clean_data_db
USE clean_data_db;

CREATE TABLE diabetes_clean (
    id INT AUTO_INCREMENT PRIMARY KEY,
    -- Features procesadas y limpias
    age_numeric INT,
    time_in_hospital INT,
    num_lab_procedures INT,
    num_procedures INT,
    num_medications INT,
    number_outpatient INT,
    number_emergency INT,
    number_inpatient INT,
    number_diagnoses INT,
    -- Features categóricas codificadas
    gender_encoded INT,
    race_encoded INT,
    age_group INT,
    admission_type INT,
    discharge_disposition INT,
    admission_source INT,
    -- Features de medicamentos (0/1)
    metformin_yes INT,
    repaglinide_yes INT,
    nateglinide_yes INT,
    insulin_yes INT,
    change_medication INT,
    diabetesMed_yes INT,
    -- Target
    readmitted TINYINT,
    -- Metadata
    batch_number INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_batch (batch_number)
);

-- Tabla de entrenamiento (70%)
CREATE TABLE train_data AS 
SELECT * FROM diabetes_clean 
WHERE batch_number IS NOT NULL
ORDER BY RAND()
LIMIT (SELECT FLOOR(COUNT(*) * 0.7) FROM diabetes_clean);

-- Tabla de validación (15%)
CREATE TABLE validation_data AS 
SELECT * FROM diabetes_clean 
WHERE id NOT IN (SELECT id FROM train_data)
ORDER BY RAND()
LIMIT (SELECT FLOOR(COUNT(*) * 0.15) FROM diabetes_clean);

-- Tabla de prueba (15%)
CREATE TABLE test_data AS 
SELECT * FROM diabetes_clean 
WHERE id NOT IN (SELECT id FROM train_data)
  AND id NOT IN (SELECT id FROM validation_data);
```

#### Configuración de Conexión

```python
# dags/scripts/queries.py
import mysql.connector
from mysql.connector import Error
import os

class DatabaseConnection:
    def __init__(self):
        self.host = os.getenv('MYSQL_HOST', 'mysql')
        self.port = int(os.getenv('MYSQL_PORT', 3306))
        self.user = os.getenv('MYSQL_USER', 'mlops_user')
        self.password = os.getenv('MYSQL_PASSWORD', 'mlops_password')
        
    def connect(self, database=None):
        try:
            connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=database
            )
            return connection
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return None
    
    def insert_raw_data(self, df, batch_number):
        """Inserta datos crudos en raw_data_db"""
        connection = self.connect('raw_data_db')
        if connection:
            try:
                cursor = connection.cursor()
                df['batch_number'] = batch_number
                
                # Preparar query de inserción
                columns = ', '.join(df.columns)
                placeholders = ', '.join(['%s'] * len(df.columns))
                query = f"INSERT INTO diabetes_raw ({columns}) VALUES ({placeholders})"
                
                # Insertar datos
                data = [tuple(row) for row in df.values]
                cursor.executemany(query, data)
                connection.commit()
                
                print(f"✓ Insertados {len(df)} registros en batch {batch_number}")
                cursor.close()
                return True
            except Error as e:
                print(f"Error insertando datos: {e}")
                return False
            finally:
                connection.close()
    
    def insert_clean_data(self, df, batch_number):
        """Inserta datos limpios en clean_data_db"""
        connection = self.connect('clean_data_db')
        if connection:
            try:
                cursor = connection.cursor()
                df['batch_number'] = batch_number
                
                columns = ', '.join(df.columns)
                placeholders = ', '.join(['%s'] * len(df.columns))
                query = f"INSERT INTO diabetes_clean ({columns}) VALUES ({placeholders})"
                
                data = [tuple(row) for row in df.values]
                cursor.executemany(query, data)
                connection.commit()
                
                print(f"✓ Insertados {len(df)} registros limpios")
                cursor.close()
                return True
            except Error as e:
                print(f"Error insertando datos limpios: {e}")
                return False
            finally:
                connection.close()
    
    def get_train_data(self):
        """Obtiene datos de entrenamiento"""
        connection = self.connect('clean_data_db')
        if connection:
            try:
                query = "SELECT * FROM train_data"
                df = pd.read_sql(query, connection)
                return df
            finally:
                connection.close()
    
    def get_validation_data(self):
        """Obtiene datos de validación"""
        connection = self.connect('clean_data_db')
        if connection:
            try:
                query = "SELECT * FROM validation_data"
                df = pd.read_sql(query, connection)
                return df
            finally:
                connection.close()
    
    def get_test_data(self):
        """Obtiene datos de prueba"""
        connection = self.connect('clean_data_db')
        if connection:
            try:
                query = "SELECT * FROM test_data"
                df = pd.read_sql(query, connection)
                return df
            finally:
                connection.close()
```

---

### 5.  Apache Airflow - Orquestador

#### DAG Principal (orquestador.py)

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
sys.path.append('/opt/airflow/dags/scripts')

from funciones import (
    check_ec2_status,
    fetch_data_from_api,
    store_raw_data,
    clean_and_transform_data,
    store_clean_data,
    create_train_val_test_split,
    upload_to_minio,
    train_models,
    register_best_model_mlflow,
    promote_to_production,
    signal_services_ready
)

default_args = {
    'owner': 'mlops_team',
    'depends_on_past': False,
    'start_date': datetime(2025, 11, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'mlops_diabetes_pipeline',
    default_args=default_args,
    description='Pipeline completo de MLOps para clasificación de diabetes',
    schedule_interval='*/10 * * * *',  # Cada 10 minutos
    catchup=False,
    tags=['mlops', 'diabetes', 'production'],
)

# Task 1: Verificar estado de EC2
task_check_ec2 = PythonOperator(
    task_id='check_ec2_status',
    python_callable=check_ec2_status,
    dag=dag,
)

# Task 2: Obtener datos de la API
task_fetch_data = PythonOperator(
    task_id='fetch_data_from_api',
    python_callable=fetch_data_from_api,
    dag=dag,
)

# Task 3: Almacenar datos crudos en MySQL
task_store_raw = PythonOperator(
    task_id='store_raw_data_mysql',
    python_callable=store_raw_data,
    dag=dag,
)

# Task 4: Limpieza y transformación
task_clean_data = PythonOperator(
    task_id='clean_and_transform_data',
    python_callable=clean_and_transform_data,
    dag=dag,
)

# Task 5: Almacenar datos limpios en MySQL
task_store_clean = PythonOperator(
    task_id='store_clean_data_mysql',
    python_callable=store_clean_data,
    dag=dag,
)

# Task 6: Crear splits de entrenamiento/validación/prueba
task_create_splits = PythonOperator(
    task_id='create_train_val_test_split',
    python_callable=create_train_val_test_split,
    dag=dag,
)

# Task 7: Subir datos procesados a MinIO
task_upload_minio = PythonOperator(
    task_id='upload_processed_data_minio',
    python_callable=upload_to_minio,
    dag=dag,
)

# Task 8: Entrenar múltiples modelos
task_train = PythonOperator(
    task_id='train_ml_models',
    python_callable=train_models,
    dag=dag,
)

# Task 9: Registrar mejor modelo en MLflow
task_register = PythonOperator(
    task_id='register_best_model',
    python_callable=register_best_model_mlflow,
    dag=dag,
)

# Task 10: Promover a producción
task_promote = PythonOperator(
    task_id='promote_to_production',
    python_callable=promote_to_production,
    dag=dag,
)

# Task 11: Señalizar servicios listos
task_signal = PythonOperator(
    task_id='signal_services_ready',
    python_callable=signal_services_ready,
    dag=dag,
)

# Definir dependencias
task_check_ec2 >> task_fetch_data >> task_store_raw >> task_clean_data
task_clean_data >> task_store_clean >> task_create_splits >> task_upload_minio
task_upload_minio >> task_train >> task_register >> task_promote >> task_signal
```

#### Funciones de Procesamiento (funciones.py - Extracto)

```python
import requests
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import mlflow
import mlflow.sklearn
from minio import Minio
import pickle
import json
import os

# Configuración
API_URL = "http://ec2-54-172-84-220.compute-1.amazonaws.com:5001/get_data"
MLFLOW_TRACKING_URI = "http://mlflow:5000"
MINIO_ENDPOINT = "minio:9000"
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin123")

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

def check_ec2_status():
    """Verifica que la instancia EC2 esté disponible"""
    try:
        response = requests.get(API_URL, timeout=10)
        if response.status_code == 200:
            print("✓ EC2 API disponible")
            return True
        else:
            raise Exception(f"API respondió con código {response.status_code}")
    except Exception as e:
        print(f"✗ Error verificando EC2: {e}")
        raise

def fetch_data_from_api():
    """Obtiene datos de la API en EC2"""
    try:
        response = requests.get(API_URL, timeout=30)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data)
            print(f"✓ Obtenidos {len(df)} registros de la API")
            
            # Guardar temporalmente
            df.to_csv('/tmp/raw_data.csv', index=False)
            return df
        else:
            raise Exception(f"Error obteniendo datos: {response.status_code}")
    except Exception as e:
        print(f"✗ Error en fetch_data: {e}")
        raise

def clean_and_transform_data():
    """Limpieza y transformación de datos"""
    df = pd.read_csv('/tmp/raw_data.csv')
    
    print(f"Iniciando limpieza de {len(df)} registros...")
    
    # 1. Eliminar columnas con muchos valores faltantes
    threshold = 0.5
    df = df.loc[:, df.isnull().mean() < threshold]
    
    # 2. Eliminar duplicados
    df = df.drop_duplicates()
    
    # 3. Manejar valores faltantes
    # Numéricos: rellenar con mediana
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df[col].isnull().sum() > 0:
            df[col].fillna(df[col].median(), inplace=True)
    
    # Categóricos: rellenar con moda
    categorical_cols = df.select_dtypes(include=['object']).columns
    for col in categorical_cols:
        if df[col].isnull().sum() > 0:
            df[col].fillna(df[col].mode()[0], inplace=True)
    
    # 4. Codificar variables categóricas
    label_encoders = {}
    for col in categorical_cols:
        if col not in ['readmitted']:  # No codificar el target aún
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            label_encoders[col] = le
    
    # 5. Convertir target 'readmitted' a binario
    if 'readmitted' in df.columns:
        # '<30' o '>30' = 1 (readmitido), 'NO' = 0
        df['readmitted'] = df['readmitted'].apply(
            lambda x: 0 if x == 'NO' else 1
        )
    
    # 6. Feature Engineering
    if 'age' in df.columns:
        # Convertir rangos de edad a valores numéricos
        age_mapping = {
            '[0-10)': 5, '[10-20)': 15, '[20-30)': 25, '[30-40)': 35,
            '[40-50)': 45, '[50-60)': 55, '[60-70)': 65, '[70-80)': 75,
            '[80-90)': 85, '[90-100)': 95
        }
        df['age_numeric'] = df['age'].map(age_mapping)
    
    print(f"✓ Datos limpiados: {len(df)} registros, {len(df.columns)} columnas")
    
    # Guardar datos limpios
    df.to_csv('/tmp/clean_data.csv', index=False)
    
    # Guardar encoders para uso posterior
    with open('/tmp/label_encoders.pkl', 'wb') as f:
        pickle.dump(label_encoders, f)
    
    return df

def train_models():
    """Entrena múltiples modelos y registra en MLflow"""
    # Cargar datos de entrenamiento desde MySQL
    from queries import DatabaseConnection
    db = DatabaseConnection()
    
    train_df = db.get_train_data()
    val_df = db.get_validation_data()
    
    # Separar features y target
    X_train = train_df.drop(['id', 'readmitted', 'batch_number', 'created_at'], axis=1)
    y_train = train_df['readmitted']
    X_val = val_df.drop(['id', 'readmitted', 'batch_number', 'created_at'], axis=1)
    y_val = val_df['readmitted']
    
    # Normalizar
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # Modelos a entrenar
    models = {
        'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42),
        'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
        'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, random_state=42)
    }
    
    results = []
    
    mlflow.set_experiment("diabetes_classification")
    
    for model_name, model in models.items():
        with mlflow.start_run(run_name=model_name):
            print(f"\nEntrenando {model_name}...")
            
            # Entrenar
            model.fit(X_train_scaled, y_train)
            
            # Predecir
            y_pred_train = model.predict(X_train_scaled)
            y_pred_val = model.predict(X_val_scaled)
            
            # Métricas
            metrics = {
                'train_accuracy': accuracy_score(y_train, y_pred_train),
                'val_accuracy': accuracy_score(y_val, y_pred_val),
                'val_precision': precision_score(y_val, y_pred_val, average='weighted'),
                'val_recall': recall_score(y_val, y_pred_val, average='weighted'),
                'val_f1': f1_score(y_val, y_pred_val, average='weighted'),
            }
            
            # Si el modelo tiene predict_proba
            if hasattr(model, 'predict_proba'):
                y_proba_val = model.predict_proba(X_val_scaled)
                metrics['val_roc_auc'] = roc_auc_score(y_val, y_proba_val, 
                                                       multi_class='ovr', 
                                                       average='weighted')
            
            # Registrar en MLflow
            mlflow.log_params(model.get_params())
            mlflow.log_metrics(metrics)
            
            # Registrar modelo
            mlflow.sklearn.log_model(model, "model")
            
            # Guardar scaler
            mlflow.log_artifact('/tmp/label_encoders.pkl')
            
            print(f"✓ {model_name} - Val Accuracy: {metrics['val_accuracy']:.4f}")
            
            results.append({
                'model_name': model_name,
                'run_id': mlflow.active_run().info.run_id,
                'metrics': metrics
            })
    
    # Guardar resultados
    with open('/tmp/model_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return results

def promote_to_production():
    """Promueve el mejor modelo a producción en MLflow"""
    client = mlflow.tracking.MlflowClient()
    
    # Leer resultados
    with open('/tmp/model_results.json', 'r') as f:
        results = json.load(f)
    
    # Encontrar el mejor modelo por val_accuracy
    best_result = max(results, key=lambda x: x['metrics']['val_accuracy'])
    best_run_id = best_result['run_id']
    
    print(f"\n Mejor modelo: {best_result['model_name']}")
    print(f"   Val Accuracy: {best_result['metrics']['val_accuracy']:.4f}")
    print(f"   Run ID: {best_run_id}")
    
    # Registrar modelo
    model_name = "diabetes_classifier_production"
    model_uri = f"runs:/{best_run_id}/model"
    
    try:
        # Intentar crear el modelo si no existe
        client.create_registered_model(model_name)
    except:
        pass  # El modelo ya existe
    
    # Crear nueva versión
    model_version = client.create_model_version(
        name=model_name,
        source=model_uri,
        run_id=best_run_id
    )
    
    # Promover a producción
    client.transition_model_version_stage(
        name=model_name,
        version=model_version.version,
        stage="Production",
        archive_existing_versions=True
    )
    
    print(f"✓ Modelo promovido a Production (versión {model_version.version})")
    
    return model_version.version
```

---

### 6.  FastAPI - API de Inferencia

#### Código Principal (main.py)

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import Response
import pickle
import os
from typing import Dict, List

app = FastAPI(
    title="Diabetes Prediction API",
    description="API para predicción de readmisión de pacientes diabéticos",
    version="1.0.0"
)

# Configuración MLflow
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# Métricas de Prometheus
prediction_counter = Counter('predictions_total', 'Total number of predictions')
prediction_histogram = Histogram('prediction_duration_seconds', 
                                 'Time spent processing prediction')
error_counter = Counter('prediction_errors_total', 'Total number of prediction errors')

# Variables globales
model = None
model_version = None
scaler = None
feature_columns = None

class PredictionInput(BaseModel):
    age_numeric: int
    time_in_hospital: int
    num_lab_procedures: int
    num_procedures: int
    num_medications: int
    number_outpatient: int
    number_emergency: int
    number_inpatient: int
    number_diagnoses: int
    gender_encoded: int
    race_encoded: int
    admission_type: int
    metformin_yes: int
    insulin_yes: int
    diabetesMed_yes: int

class PredictionOutput(BaseModel):
    prediction: int
    probability: float
    model_version: str
    model_name: str

def load_production_model():
    """Carga el modelo en producción desde MLflow"""
    global model, model_version, scaler, feature_columns
    
    try:
        client = mlflow.tracking.MlflowClient()
        model_name = "diabetes_classifier_production"
        
        # Obtener versión en producción
        versions = client.get_latest_versions(model_name, stages=["Production"])
        
        if not versions:
            raise Exception("No hay modelo en producción")
        
        latest_version = versions[0]
        model_version = latest_version.version
        
        # Cargar modelo
        model_uri = f"models:/{model_name}/Production"
        model = mlflow.sklearn.load_model(model_uri)
        
        print(f"✓ Modelo cargado: {model_name} versión {model_version}")
        
        return True
    except Exception as e:
        print(f"✗ Error cargando modelo: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """Cargar modelo al iniciar la aplicación"""
    success = load_production_model()
    if not success:
        print("⚠ Advertencia: No se pudo cargar el modelo en startup")

@app.get("/")
def root():
    return {
        "message": "Diabetes Prediction API",
        "status": "running",
        "model_loaded": model is not None,
        "model_version": model_version
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    if model is None:
        return {
            "status": "unhealthy",
            "model_loaded": False
        }
    return {
        "status": "healthy",
        "model_loaded": True,
        "model_version": model_version
    }

@app.post("/predict", response_model=PredictionOutput)
@prediction_histogram.time()
def predict(input_data: PredictionInput):
    """Endpoint de predicción"""
    global model
    
    try:
        # Recargar modelo si no está cargado
        if model is None:
            load_production_model()
        
        if model is None:
            error_counter.inc()
            raise HTTPException(status_code=503, 
                              detail="Modelo no disponible")
        
        # Preparar datos
        data_dict = input_data.dict()
        df = pd.DataFrame([data_dict])
        
        # Predecir
        prediction = model.predict(df)[0]
        
        # Probabilidad si está disponible
        if hasattr(model, 'predict_proba'):
            probability = model.predict_proba(df)[0][1]
        else:
            probability = float(prediction)
        
        prediction_counter.inc()
        
        return PredictionOutput(
            prediction=int(prediction),
            probability=float(probability),
            model_version=str(model_version),
            model_name="diabetes_classifier_production"
        )
        
    except Exception as e:
        error_counter.inc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict_batch")
def predict_batch(input_data: List[PredictionInput]):
    """Predicción por lotes"""
    try:
        if model is None:
            load_production_model()
        
        # Convertir a DataFrame
        data_list = [item.dict() for item in input_data]
        df = pd.DataFrame(data_list)
        
        # Predecir
        predictions = model.predict(df)
        
        if hasattr(model, 'predict_proba'):
            probabilities = model.predict_proba(df)[:, 1]
        else:
            probabilities = predictions.astype(float)
        
        prediction_counter.inc(len(input_data))
        
        results = [
            {
                "prediction": int(pred),
                "probability": float(prob),
                "model_version": str(model_version)
            }
            for pred, prob in zip(predictions, probabilities)
        ]
        
        return {"predictions": results}
        
    except Exception as e:
        error_counter.inc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
def metrics():
    """Endpoint para Prometheus"""
    return Response(content=generate_latest(), media_type="text/plain")

@app.post("/reload_model")
def reload_model():
    """Recargar modelo manualmente"""
    success = load_production_model()
    if success:
        return {
            "status": "success",
            "message": "Modelo recargado exitosamente",
            "version": model_version
        }
    else:
        raise HTTPException(status_code=500, 
                          detail="Error recargando modelo")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

### 7. 🎨 Streamlit - Interfaz de Usuario

#### Aplicación Principal (app.py)

```python
import streamlit as st
import requests
import pandas as pd
import json
import plotly.graph_objects as go
import plotly.express as px

# Configuración de la página
st.set_page_config(
    page_title="Diabetes Readmission Predictor",
    page_icon="🏥",
    layout="wide"
)

# URL de la API
API_URL = "http://fastapi:8000"

# Título
st.title("🏥 Predictor de Readmisión de Pacientes Diabéticos")
st.markdown("### Sistema de Machine Learning en Producción")

# Sidebar con información
with st.sidebar:
    st.header("ℹ️ Información del Sistema")
    
    # Verificar estado de la API
    try:
        health_response = requests.get(f"{API_URL}/health", timeout=5)
        if health_response.status_code == 200:
            health_data = health_response.json()
            st.success("✅ API Conectada")
            st.info(f"**Modelo:** {health_data.get('model_version', 'N/A')}")
        else:
            st.error("❌ API No Disponible")
    except:
        st.error("❌ Error de Conexión")
    
    st.markdown("---")
    st.markdown("""
    **Proyecto:** MLOps Nivel 3  
    **Autores:** Sebastián Rodríguez, David Córdova  
    **Universidad:** Pontificia Universidad Javeriana
    """)

# Tabs principales
tab1, tab2, tab3 = st.tabs(["🔮 Predicción Individual", 
                             "📊 Predicción por Lotes", 
                             "📈 Estadísticas"])

# Tab 1: Predicción Individual
with tab1:
    st.header("Ingresar Datos del Paciente")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Datos Demográficos")
        age_numeric = st.slider("Edad", 0, 100, 50)
        gender_encoded = st.selectbox("Género", 
                                     options=[0, 1], 
                                     format_func=lambda x: "Femenino" if x == 0 else "Masculino")
        race_encoded = st.selectbox("Raza (Codificada)", options=list(range(6)))
    
    with col2:
        st.subheader("Datos de Hospitalización")
        time_in_hospital = st.number_input("Días en Hospital", 1, 14, 3)
        admission_type = st.selectbox("Tipo de Admisión", options=list(range(8)))
        num_lab_procedures = st.number_input("Procedimientos de Laboratorio", 0, 100, 40)
        num_procedures = st.number_input("Procedimientos", 0, 10, 0)
        num_medications = st.number_input("Medicamentos", 0, 50, 15)
    
    with col3:
        st.subheader("Historial Médico")
        number_outpatient = st.number_input("Visitas Ambulatorias", 0, 20, 0)
        number_emergency = st.number_input("Visitas de Emergencia", 0, 20, 0)
        number_inpatient = st.number_input("Hospitalizaciones Previas", 0, 20, 0)
        number_diagnoses = st.number_input("Número de Diagnósticos", 1, 16, 7)
    
    st.subheader("Medicamentos")
    col4, col5, col6 = st.columns(3)
    with col4:
        metformin_yes = st.checkbox("Metformina")
    with col5:
        insulin_yes = st.checkbox("Insulina")
    with col6:
        diabetesMed_yes = st.checkbox("Medicamento para Diabetes")
    
    # Botón de predicción
    if st.button("🔮 Realizar Predicción", type="primary"):
        # Preparar datos
        payload = {
            "age_numeric": age_numeric,
            "time_in_hospital": time_in_hospital,
            "num_lab_procedures": num_lab_procedures,
            "num_procedures": num_procedures,
            "num_medications": num_medications,
            "number_outpatient": number_outpatient,
            "number_emergency": number_emergency,
            "number_inpatient": number_inpatient,
            "number_diagnoses": number_diagnoses,
            "gender_encoded": gender_encoded,
            "race_encoded": race_encoded,
            "admission_type": admission_type,
            "metformin_yes": int(metformin_yes),
            "insulin_yes": int(insulin_yes),
            "diabetesMed_yes": int(diabetesMed_yes)
        }
        
        # Hacer predicción
        try:
            with st.spinner("Realizando predicción..."):
                response = requests.post(f"{API_URL}/predict", json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Mostrar resultados
                    st.success("✅ Predicción Completada")
                    
                    col_res1, col_res2, col_res3 = st.columns(3)
                    
                    with col_res1:
                        prediction_text = "SÍ" if result['prediction'] == 1 else "NO"
                        color = "red" if result['prediction'] == 1 else "green"
                        st.markdown(f"""
                        <div style='text-align: center; padding: 20px; 
                                    background-color: {color}; 
                                    border-radius: 10px;'>
                            <h2 style='color: white;'>Readmisión: {prediction_text}</h2>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_res2:
                        probability_pct = result['probability'] * 100
                        st.metric("Probabilidad", f"{probability_pct:.2f}%")
                    
                    with col_res3:
                        st.metric("
