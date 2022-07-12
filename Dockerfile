FROM python:3.10.2-slim

# Prevents Python from writing pyc files to disc (equivalent to python -B option)
ENV PYTHONDONTWRITEBYTECODE 1
# Prevents Python from buffering stdout and stderr (equivalent to python -u option)
ENV PYTHONUNBUFFERED 1

WORKDIR /code

COPY ./requirements.txt .
RUN python -m pip install --upgrade pip

RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn",  "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
