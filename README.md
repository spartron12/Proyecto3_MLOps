# MLOps Proyecto 3

**Grupo:** Sebastián Rodríguez y David Córdova  
**Curso:** Machine Learning Operations (MLOps)  
**Profesor:** Cristian Diaz Alvarez

Este proyecto implementa un pipeline completo de Machine Learning Operations (MLOps) que automatiza desde la limpieza de datos hasta el entrenamiento de modelos y despliegue de API, utilizando Apache Airflow como orquestador principal, con integración de Grafana, Prometheus y MinIO para monitoreo y almacenamiento de objetos.

---

##  Descripción General

Este proyecto implementa un **pipeline completo de MLOps** que automatiza el proceso de:

1. Recolección de datos desde una **API externa** (http://10.43.100.103:8080)
2. Limpieza, almacenamiento y transformación con **Apache Airflow**
3. **Almacenamiento de datos en MinIO** (S3-compatible object storage)
4. Entrenamiento automático de modelos con **scikit-learn**
5. Registro y seguimiento de experimentos en **MLflow**
6. Despliegue de modelo en una **API FastAPI**
7. **Monitoreo con Grafana y Prometheus** para métricas del sistema
8. Exposición del modelo entrenado como servicio REST para realizar predicciones en tiempo real

---

##  Características Principales

- **Orquestación automática** del pipeline mediante **Airflow**
- **Contenerización total** con **Docker Compose**
- **Auto-disparo del DAG** al iniciar los contenedores
- **Recolección dinámica** de datos desde la API del profesor (nuevos datos cada 5 min)
- **Almacenamiento en MinIO** para gestión de datos y artefactos
- **Entrenamiento reproducible** y versionado de modelos con MLflow
- **Servicio FastAPI** que permite consumir el modelo para predicciones
- **Monitoreo en tiempo real** con Grafana y Prometheus
- **Volúmenes compartidos** entre servicios para acceso a modelos `.pkl` y configuraciones `.json`

---

## 📁 Estructura del Proyecto
