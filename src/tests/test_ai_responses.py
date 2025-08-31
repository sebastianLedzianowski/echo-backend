import httpx
import pytest
import asyncio

from src.services.ai import (
    generate_empathetic_response,
    generate_practical_response, OLLAMA_URL, OLLAMA_MODEL
)

# Przykładowa historia rozmowy
sample_history = [
    {"message": "Miałem ciężki dzień.", "is_user_message": True},
    {"message": "Rozumiem, to musiało być trudne.", "is_user_message": False},
]


@pytest.mark.asyncio
async def test_generate_empathetic_response():
    user_input = "Czuję się bardzo zmęczony."
    response = await generate_empathetic_response(user_input, sample_history)
    print("\n[Empatyczna odpowiedź] ->", response)
    assert isinstance(response, str)
    assert len(response.strip()) > 0


@pytest.mark.asyncio
async def test_generate_practical_response():
    user_input = "Jak mogę lepiej zarządzać czasem?"
    response = await generate_practical_response(user_input, sample_history)
    print("\n[Praktyczna odpowiedź] ->", response)
    assert isinstance(response, str)
    assert len(response.strip()) > 0
