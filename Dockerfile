FROM python:3.10-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /code

# Instalar dependencias (solo dejamos utilidades muy ligeras si es necesario)
RUN apt-get update && rm -rf /var/lib/apt/lists/*

# Copiar el archivo de requerimientos e instalar dependencias
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copiar todo el código de la aplicación
COPY ./app /code/app
COPY ./alembic /code/alembic
COPY ./alembic.ini /code/alembic.ini
COPY ./seed.py /code/seed.py
COPY ./seed_inventory.py /code/seed_inventory.py
COPY ./seed_tallas.py /code/seed_tallas.py
COPY ./seed_colores.py /code/seed_colores.py
COPY ./seed_colecciones.py /code/seed_colecciones.py

# Exponer el puerto en el que correrá FastAPI
EXPOSE 8000

# Comando para correr la aplicación usando uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
