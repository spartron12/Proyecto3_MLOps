# Usamos la imagen de Airflow como base
FROM apache/airflow:2.6.0-python3.9

# Cambiar al usuario root temporalmente para crear el directorio de trabajo y ajustar permisos
#USER root
USER airflow
#RUN mkdir /work && chown airflow: /work
#WORKDIR /work

# Copiar el archivo requirements.txt al contenedor
COPY requirements.txt /work/requirements.txt

# Instalar dependencias adicionales desde requirements.txt
# Asegúrate de que tu requirements.txt no incluya jupyter o jupyterlab si decides excluirlos
RUN pip install --user --no-cache-dir -r /work/requirements.txt

# Exponer puertos necesarios (ejemplo: el puerto web de Airflow y otros que necesites)
EXPOSE 8080 8081 8082
