FROM python:3.13-slim

RUN pip install --upgrade pip && pip install poetry
WORKDIR /app
COPY poetry.lock pyproject.toml ./
RUN poetry install --no-root
COPY . .
EXPOSE 8000
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]