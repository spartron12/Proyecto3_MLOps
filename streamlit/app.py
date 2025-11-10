# app_streamlit.py
import streamlit as st
import requests
import os

# -------------------------------
# Configuración de la API
API_URL = os.getenv("API_URL", "http://fastapi-service:8000") + "/predict"
# -------------------------------

# -------------------------------
# Función de codificación interna
def encode_features(input_dict):
    # Edad -> one-hot
    age_ranges = ['0-10', '10-20', '20-30', '30-40', '40-50', '50-60', '60-70', '70-80', '80-90', '90-100']
    age_encoded = {f"age_{r.replace('-', '_')}": 0 for r in age_ranges}
    for r in age_ranges:
        low, high = map(int, r.split('-'))
        if low <= input_dict['age'] < high:
            age_encoded[f"age_{r.replace('-', '_')}"] = 1
            break

    # Género -> one-hot
    gender_encoded = {"gender_Female": 0, "gender_Male": 0}
    gender_encoded[f"gender_{input_dict['gender']}"] = 1

    # Raza -> one-hot
    race_encoded = {f"race_{r}": 0 for r in ["AfricanAmerican", "Asian", "Caucasian", "Hispanic", "Other"]}
    race_encoded[f"race_{input_dict['race']}"] = 1

    # Diagnósticos -> one-hot
    diag_categories = ["Circulatory", "Diabetes", "Digestive", "Genitourinary", "Injury",
                       "Musculoskeletal", "Neoplasms", "Other", "Respiratory"]
    diag_encoded = {}
    for i in [1, 2, 3]:
        for cat in diag_categories:
            key = f"diag_{i}_{cat}"
            diag_encoded[key] = 1 if input_dict[f"diag_{i}"] == cat else 0

    # Cambios y medicación -> one-hot
    cambio_encoded = {"cambio_Ch": 0, "cambio_No": 0}
    cambio_encoded[f"cambio_{input_dict['cambio']}"] = 1

    med_encoded = {"diabetesMed_No": 0, "diabetesMed_Yes": 0}
    med_encoded[f"diabetesMed_{input_dict['diabetesMed']}"] = 1

    # Combinar todo
    features_encoded = {
        **age_encoded,
        **gender_encoded,
        **race_encoded,
        **diag_encoded,
        **cambio_encoded,
        **med_encoded
    }

    # Agregar features numéricas
    num_features = [
        'time_in_hospital', 'num_lab_procedures', 'num_procedures', 'num_medications',
        'number_outpatient', 'number_emergency', 'number_inpatient', 'number_diagnoses',
        'max_glu_serum', 'A1Cresult'
    ]
    for f in num_features:
        features_encoded[f] = input_dict[f]

    # Agregar los nuevos campos obligatorios
    features_encoded["discharge_disposition_id"] = input_dict["discharge_disposition_id"]
    features_encoded["admission_source_id"] = input_dict["admission_source_id"]

    return features_encoded
# -------------------------------

# -------------------------------
# Interfaz Streamlit
st.title("Predicción de Reingreso Hospitalario en Pacientes Diabéticos")

st.header("Ingrese la información del paciente:")

# Campos amigables
age = st.number_input("Edad", min_value=0, max_value=120, value=50)
gender = st.selectbox("Género", ["Female", "Male"])
race = st.selectbox("Raza", ["AfricanAmerican", "Asian", "Caucasian", "Hispanic", "Other"])

st.subheader("Datos hospitalarios")
time_in_hospital = st.number_input("Tiempo en hospital (días)", min_value=0, value=5)
num_lab_procedures = st.number_input("Número de procedimientos de laboratorio", min_value=0, value=45)
num_procedures = st.number_input("Número de procedimientos", min_value=0, value=0)
num_medications = st.number_input("Número de medicamentos", min_value=0, value=13)
number_outpatient = st.number_input("Número de consultas ambulatorias", min_value=0, value=0)
number_emergency = st.number_input("Número de visitas a emergencia", min_value=0, value=0)
number_inpatient = st.number_input("Número de hospitalizaciones previas", min_value=0, value=0)
number_diagnoses = st.number_input("Número de diagnósticos", min_value=0, value=8)
max_glu_serum = st.number_input("Máximo glucosa sérica", min_value=0, value=0)
A1Cresult = st.number_input("Resultado A1C", min_value=0, value=0)

st.subheader("Tratamiento y medicación")
cambio = st.selectbox("Cambio de medicación", ["Ch", "No"])
diabetesMed = st.selectbox("Medicación para diabetes", ["Yes", "No"])

st.subheader("Diagnósticos principales")
diag_1 = st.selectbox("Diagnóstico principal 1", ["Circulatory", "Diabetes", "Digestive", "Genitourinary",
                                                  "Injury", "Musculoskeletal", "Neoplasms", "Other", "Respiratory"])
diag_2 = st.selectbox("Diagnóstico principal 2", ["Circulatory", "Diabetes", "Digestive", "Genitourinary",
                                                  "Injury", "Musculoskeletal", "Neoplasms", "Other", "Respiratory"])
diag_3 = st.selectbox("Diagnóstico principal 3", ["Circulatory", "Diabetes", "Digestive", "Genitourinary",
                                                  "Injury", "Musculoskeletal", "Neoplasms", "Other", "Respiratory"])

st.subheader("Información de admisión y alta")
discharge_disposition_id = st.selectbox(
    "Tipo de disposición al alta",
    [1, 2, 3, 4, 5],
    format_func=lambda x: {
        1: "Alta a casa",
        2: "Transferido a otro hospital",
        3: "Alta a cuidado domiciliario",
        4: "Fallecido",
        5: "Otra"
    }[x]
)

admission_source_id = st.selectbox(
    "Fuente de admisión",
    [1, 7, 8],
    format_func=lambda x: {
        1: "Referencia médica",
        7: "Emergencia",
        8: "Transferido desde otro hospital"
    }[x]
)

# Botón de predicción
if st.button("Predecir reingreso"):
    input_dict = {
        "age": age,
        "gender": gender,
        "race": race,
        "time_in_hospital": time_in_hospital,
        "num_lab_procedures": num_lab_procedures,
        "num_procedures": num_procedures,
        "num_medications": num_medications,
        "number_outpatient": number_outpatient,
        "number_emergency": number_emergency,
        "number_inpatient": number_inpatient,
        "number_diagnoses": number_diagnoses,
        "max_glu_serum": max_glu_serum,
        "A1Cresult": A1Cresult,
        "cambio": cambio,
        "diabetesMed": diabetesMed,
        "diag_1": diag_1,
        "diag_2": diag_2,
        "diag_3": diag_3,
        "discharge_disposition_id": discharge_disposition_id,
        "admission_source_id": admission_source_id
    }

    # Codificar a formato que espera el modelo
    features_encoded = encode_features(input_dict)

    # Enviar a FastAPI
    try:
        response = requests.post(API_URL, json=features_encoded)
        if response.status_code == 200:
            result = response.json()
            st.success(f"Predicción: {'Sí reingreso' if result['prediction'] == 1 else 'No reingreso'}")
            st.info(f"Mensaje: {result['message']}")
        else:
            st.error(f"Error en la API: {response.text}")
    except Exception as e:
        st.error(f"Error de conexión: {e}")
