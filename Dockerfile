FROM python:3.9
WORKDIR /code
COPY ./app/backend/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY . /code
ENV PYTHONPATH=/code
CMD ["uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
