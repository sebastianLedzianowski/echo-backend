#!/bin/sh
set -e

echo "START ENTRYPOINT"

# Czekaj na bazę danych
echo "Czekam na bazę danych..."
until pg_isready -h postgres -p 5432 -U postgres; do
  sleep 2
done
echo "Baza danych jest gotowa."

# Sprawdź Ollama
echo "Sprawdzam dostępność Ollama..."
until curl -f http://ollama:11434/api/tags > /dev/null 2>&1; do
  echo "Czekam na Ollama..."
  sleep 2
done
echo "Ollama jest dostępne."

# Sprawdź model
MODEL_NAME=${OLLAMA_MODEL:-llama2}
echo "Sprawdzam model: $MODEL_NAME"
until curl -f http://ollama:11434/api/show -d "{\"name\":\"$MODEL_NAME\"}" > /dev/null 2>&1; do
    echo "Model $MODEL_NAME nie jest dostępny. Próbuję pobrać..."
    curl -f http://ollama:11434/api/pull -d "{\"name\":\"$MODEL_NAME\"}" > /dev/null 2>&1
    sleep 5
done
echo "Model $MODEL_NAME jest gotowy."

# Migracje Alembic
echo "Aktualizuję bazę danych..."
alembic upgrade head

# Uruchomienie Uvicorn w miejscu entrypoint
echo "Uruchamiam Uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --no-access-log