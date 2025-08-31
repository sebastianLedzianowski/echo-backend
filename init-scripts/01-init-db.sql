-- Inicjalizacja bazy danych Echo Backend
-- Ten skrypt jest uruchamiany automatycznie przy pierwszym uruchomieniu kontenera

-- Tworzenie rozszerzeń
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Ustawienie kodowania i collation
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

-- Komentarz do bazy danych
COMMENT ON DATABASE echo_db IS 'Baza danych dla aplikacji Echo Backend - platforma wsparcia emocjonalnego i filozoficznego';

-- Ustawienie timezone
SET timezone = 'UTC';
