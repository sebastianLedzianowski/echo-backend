# Echo Backend API - Dokumentacja dla Frontendu React

## Opis Aplikacji

Echo Backend to platforma wsparcia emocjonalnego i filozoficznego zintegrowana z AI. Aplikacja oferuje:

- **Konwersacje z AI** w trybach empatycznym i praktycznym
- **Dziennik emocji** do zapisywania przemyśleń
- **Testy psychologiczne** (ASRS, GAD-7, PHQ-9) z analizą AI
- **System użytkowników** z autoryzacją JWT
- **Panel administracyjny** z zaawansowanymi statystykami
- **System kontaktowy** dla użytkowników

## Konfiguracja Środowiska

### Wymagania
- Python 3.8+
- PostgreSQL
- Ollama (dla AI)
- Redis (opcjonalnie)

### Instalacja
```bash
# Aktywacja środowiska wirtualnego
source .venv/bin/activate  # Linux/Mac
# lub
.venv\Scripts\activate     # Windows

# Instalacja zależności
pip install -r requirements.txt

# Uruchomienie migracji
alembic upgrade head

# Uruchomienie serwera
python main.py
```

### Zmienne Środowiskowe (.env)
```env
# Baza danych
POSTGRES_SERVER=localhost
POSTGRES_USER=echo_user
POSTGRES_PASSWORD=echo_password
POSTGRES_DB=echo_db
POSTGRES_PORT=5432

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password
MAIL_FROM=your-email@example.com
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com
MAIL_FROMT_NAME=Echo Platform

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

## API Endpoints

### Base URL
```
http://localhost:8000
```

### Dokumentacja API
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Autoryzacja

### System Tokenów JWT
- **Access Token**: 30 minut (domyślnie)
- **Refresh Token**: 7 dni
- **Header**: `Authorization: Bearer <access_token>`

### Endpointy Autoryzacji

#### Rejestracja
```http
POST /api/auth/signup
Content-Type: application/json

{
  "username": "string (5-55 znaków)",
  "password": "string (6-55 znaków)",
  "email": "string (opcjonalny)",
  "full_name": "string (opcjonalny, 5-64 znaki)"
}
```

#### Logowanie
```http
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=string&password=string
```

**Odpowiedź:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer"
}
```

#### Odświeżanie Tokenu
```http
GET /api/auth/refresh_token
Authorization: Bearer <refresh_token>
```

#### Potwierdzenie Email
```http
GET /api/auth/confirmed_email/{token}
```

#### Reset Hasła
```http
POST /api/auth/request_password_reset
Content-Type: application/json

{
  "email": "string"
}
```

```http
POST /api/auth/reset-password
Content-Type: application/json

{
  "token": "string",
  "new_password": "string"
}
```

## Modele Danych

### User
```typescript
interface User {
  id: number;
  username: string;
  email?: string;
  full_name?: string;
  created_at: string;
  confirmed: boolean;
  is_active: boolean;
  is_admin: boolean;
}
```

### ConversationMode
```typescript
type ConversationMode = "empathetic" | "practical" | "diary";
```

### TestType
```typescript
type TestType = "asrs" | "gad7" | "phq9";
```

### ContactMessageType
```typescript
type ContactMessageType = 
  | "general" 
  | "support" 
  | "bug_report" 
  | "feature_request" 
  | "complaint" 
  | "other";
```

## Endpointy Użytkownika

### Profil Użytkownika

#### Pobierz Dane Użytkownika
```http
GET /api/users/me/
Authorization: Bearer <access_token>
```

#### Aktualizuj Profil
```http
PATCH /api/users/me/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "full_name": "string (opcjonalny)",
  "email": "string (opcjonalny)"
}
```

#### Zmień Hasło
```http
PATCH /api/users/me/password/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "old_password": "string",
  "new_password": "string"
}
```

#### Usuń Konto
```http
DELETE /api/users/me/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "password": "string"
}
```

## Konwersacje z AI

### Tryb Empatyczny

#### Wyślij Wiadomość
```http
POST /api/echo/empathetic/send
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "text": "string (1-2000 znaków)"
}
```

**Odpowiedź:**
```json
{
  "ai_response": "string"
}
```

#### Historia Konwersacji
```http
GET /api/echo/empathetic/history?limit=100
Authorization: Bearer <access_token>
```

**Odpowiedź:**
```json
{
  "history": [
    {
      "id": number,
      "user_id": number,
      "mode": "empathetic",
      "message": "string",
      "is_user_message": boolean,
      "created_at": "string"
    }
  ],
  "count": number
}
```

### Tryb Praktyczny

#### Wyślij Wiadomość
```http
POST /api/echo/practical/send
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "text": "string (1-2000 znaków)"
}
```

#### Historia Konwersacji
```http
GET /api/echo/practical/history?limit=100
Authorization: Bearer <access_token>
```

### Dziennik Emocji

#### Zapisz Wpis
```http
POST /api/echo/diary/send
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "text": "string (1-5000 znaków)"
}
```

**Odpowiedź:**
```json
{
  "message": "Wpis zapisany pomyślnie",
  "entry": {
    "id": number,
    "content": "string",
    "created_at": "string"
  }
}
```

#### Historia Dziennika
```http
GET /api/echo/diary/history?limit=100
Authorization: Bearer <access_token>
```

### Statystyki Użytkownika
```http
GET /api/echo/stats
Authorization: Bearer <access_token>
```

**Odpowiedź:**
```json
{
  "user_id": number,
  "empathetic_messages": number,
  "practical_messages": number,
  "diary_entries": number,
  "total_messages": number
}
```

## Testy Psychologiczne

### Pobierz Pytania Testu

#### ASRS (ADHD)
```http
GET /api/tests/questions/asrs
Authorization: Bearer <access_token>
```

#### GAD-7 (Lęk)
```http
GET /api/tests/questions/gad7
Authorization: Bearer <access_token>
```

#### PHQ-9 (Depresja)
```http
GET /api/tests/questions/phq9
Authorization: Bearer <access_token>
```

**Odpowiedź (przykład ASRS):**
```json
{
  "test_name": "ASRS v1.1",
  "description": "Adult ADHD Self-Report Scale...",
  "instructions": "Odpowiedz na pytania...",
  "scale": [
    {"label": "Nigdy", "value": 0},
    {"label": "Rzadko", "value": 1},
    {"label": "Czasami", "value": 2},
    {"label": "Często", "value": 3},
    {"label": "Bardzo często", "value": 4}
  ],
  "questions_part_a": ["Pytanie 1", "Pytanie 2", ...],
  "questions_part_b": ["Pytanie 1", "Pytanie 2", ...]
}
```

### Prześlij Odpowiedzi

#### Test ASRS
```http
POST /api/tests/asrs
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "part_a": [2, 3, 1, 4, 2, 3],
  "part_b": [1, 2, 3, 2, 1, 0, 2, 3, 1, 2, 1, 3]
}
```

#### Test GAD-7
```http
POST /api/tests/gad7
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "answers": [1, 2, 1, 3, 0, 2, 1]
}
```

#### Test PHQ-9
```http
POST /api/tests/phq9
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "answers": [2, 1, 3, 2, 1, 0, 2, 1, 0]
}
```

**Odpowiedź:**
```json
{
  "id": number,
  "test_type": "asrs|gad7|phq9",
  "score": number,
  "interpretation": "string",
  "ai_analysis": "string",
  "created_at": "string"
}
```

### Historia Testów
```http
GET /api/tests/history?test_type=asrs&limit=10&offset=0
Authorization: Bearer <access_token>
```

**Odpowiedź:**
```json
{
  "tests": [
    {
      "id": number,
      "test_type": "string",
      "score": number,
      "interpretation": "string",
      "ai_analysis": "string",
      "created_at": "string"
    }
  ],
  "total_count": number
}
```

### Szczegóły Testu
```http
GET /api/tests/result/{test_id}
Authorization: Bearer <access_token>
```

## System Kontaktowy

### Wyślij Wiadomość
```http
POST /api/contact
Content-Type: application/json

{
  "name": "string (2-100 znaków)",
  "email": "string",
  "subject": "string (5-200 znaków)",
  "message": "string (10-2000 znaków)",
  "message_type": "general|support|bug_report|feature_request|complaint|other",
  "priority": 1-5
}
```

**Odpowiedź:**
```json
{
  "id": number,
  "name": "string",
  "email": "string",
  "subject": "string",
  "message": "string",
  "message_type": "string",
  "priority": number,
  "status": "new",
  "created_at": "string",
  "updated_at": "string",
  "admin_notes": null
}
```

## Panel Administracyjny

> **Uwaga**: Wszystkie endpointy administracyjne wymagają uprawnień administratora (`is_admin: true`)

### Zarządzanie Użytkownikami

#### Lista Użytkowników
```http
GET /api/admin/users?skip=0&limit=100
Authorization: Bearer <access_token>
```

#### Szczegóły Użytkownika
```http
GET /api/admin/user/?user_id=1
GET /api/admin/user/?username=testuser
GET /api/admin/user/?email=test@example.com
Authorization: Bearer <access_token>
```

#### Aktualizuj Profil Użytkownika
```http
PATCH /api/admin/users/{user_id}/profile
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "username": "string (opcjonalny)",
  "email": "string (opcjonalny)",
  "full_name": "string (opcjonalny)",
  "is_active": boolean
}
```

#### Potwierdź Email Użytkownika
```http
PATCH /api/admin/users/{user_id}/confirm-email
Authorization: Bearer <access_token>
```

#### Zmień Status Administratora
```http
PATCH /api/admin/users/{user_id}/admin-status
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "is_admin": boolean
}
```

#### Usuń Użytkownika
```http
DELETE /api/admin/users/{user_id}
Authorization: Bearer <access_token>
```

### Zarządzanie Wiadomościami Kontaktowymi

#### Lista Wiadomości
```http
GET /api/contact?page=1&per_page=10&status_filter=new&message_type=support&priority=3&sort_by=created_at&sort_order=desc
Authorization: Bearer <access_token>
```

#### Szczegóły Wiadomości
```http
GET /api/contact/{message_id}
Authorization: Bearer <access_token>
```

#### Aktualizuj Wiadomość
```http
PUT /api/contact/{message_id}
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "status": "new|in_progress|resolved|closed",
  "admin_notes": "string (opcjonalny)",
  "priority": 1-5
}
```

#### Usuń Wiadomość
```http
DELETE /api/contact/{message_id}
Authorization: Bearer <access_token>
```

#### Statystyki Wiadomości
```http
GET /api/contact/stats/summary
Authorization: Bearer <access_token>
```

### Statystyki Systemu

#### Przegląd Ogólny
```http
GET /api/admin/stats/overview
Authorization: Bearer <access_token>
```

**Odpowiedź:**
```json
{
  "users": {
    "total": number,
    "active": number,
    "confirmed": number,
    "admins": number,
    "new_24h": number
  },
  "diary": {
    "total_entries": number,
    "recent_7_days": number,
    "new_24h": number
  },
  "conversations": {
    "total": number,
    "recent_7_days": number,
    "new_24h": number
  },
  "api": {
    "total_hits": number,
    "hits_24h": number,
    "avg_response_time_24h_ms": number
  },
  "tests": {
    "total": number,
    "recent_7_days": number
  },
  "llm": {
    "total_calls": number,
    "calls_24h": number,
    "avg_response_time_24h_ms": number,
    "avg_response_time_7d_ms": number,
    "avg_response_time_30d_ms": number
  }
}
```

#### Statystyki Użytkowników
```http
GET /api/admin/stats/users/stats
Authorization: Bearer <access_token>
```

#### Statystyki Dziennika
```http
GET /api/admin/stats/diary/stats
Authorization: Bearer <access_token>
```

#### Statystyki Konwersacji
```http
GET /api/admin/stats/conversations/stats
Authorization: Bearer <access_token>
```

#### Statystyki API
```http
GET /api/admin/stats/api/stats
Authorization: Bearer <access_token>
```

#### Statystyki Wydajności
```http
GET /api/admin/stats/performance/stats
Authorization: Bearer <access_token>
```

#### Statystyki Testów
```http
GET /api/admin/stats/tests/stats
Authorization: Bearer <access_token>
```

#### Statystyki LLM
```http
GET /api/admin/stats/llm/stats
Authorization: Bearer <access_token>
```

#### Wszystkie Dane
```http
GET /api/admin/stats/all-data
Authorization: Bearer <access_token>
```

#### Eksport Danych
```http
GET /api/admin/stats/export?format=json
GET /api/admin/stats/export?format=csv
GET /api/admin/stats/export?format=xml
Authorization: Bearer <access_token>
```

## Przykłady Implementacji React

### Konfiguracja Axios

```typescript
// api/client.ts
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor dla tokenów
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor dla odświeżania tokenów
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/api/auth/refresh_token`, {}, {
            headers: { Authorization: `Bearer ${refreshToken}` }
          });
          const { access_token } = response.data;
          localStorage.setItem('access_token', access_token);
          return apiClient.request(error.config);
        } catch (refreshError) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);
```

### Hook do Autoryzacji

```typescript
// hooks/useAuth.ts
import { useState, useEffect } from 'react';
import { apiClient } from '../api/client';

interface User {
  id: number;
  username: string;
  email?: string;
  full_name?: string;
  created_at: string;
  confirmed: boolean;
  is_active: boolean;
  is_admin: boolean;
}

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      fetchUser();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchUser = async () => {
    try {
      const response = await apiClient.get('/api/users/me/');
      setUser(response.data);
    } catch (error) {
      console.error('Błąd pobierania użytkownika:', error);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    } finally {
      setLoading(false);
    }
  };

  const login = async (username: string, password: string) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const response = await apiClient.post('/api/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });

    const { access_token, refresh_token } = response.data;
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    
    await fetchUser();
    return response.data;
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  return { user, loading, login, logout, fetchUser };
};
```

### Komponent Logowania

```tsx
// components/LoginForm.tsx
import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';

export const LoginForm: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      await login(username, password);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Błąd logowania');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>Nazwa użytkownika:</label>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
      </div>
      <div>
        <label>Hasło:</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </div>
      {error && <div style={{ color: 'red' }}>{error}</div>}
      <button type="submit">Zaloguj się</button>
    </form>
  );
};
```

### Hook do Konwersacji z AI

```typescript
// hooks/useConversation.ts
import { useState } from 'react';
import { apiClient } from '../api/client';

interface ConversationMessage {
  id: number;
  user_id: number;
  mode: string;
  message: string;
  is_user_message: boolean;
  created_at: string;
}

export const useConversation = (mode: 'empathetic' | 'practical') => {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async (text: string) => {
    setLoading(true);
    try {
      const response = await apiClient.post(`/api/echo/${mode}/send`, { text });
      const aiResponse = response.data.ai_response;
      
      // Dodaj wiadomość użytkownika
      const userMessage: ConversationMessage = {
        id: Date.now(),
        user_id: 0,
        mode,
        message: text,
        is_user_message: true,
        created_at: new Date().toISOString()
      };
      
      // Dodaj odpowiedź AI
      const aiMessage: ConversationMessage = {
        id: Date.now() + 1,
        user_id: 0,
        mode,
        message: aiResponse,
        is_user_message: false,
        created_at: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, userMessage, aiMessage]);
    } catch (error) {
      console.error('Błąd wysyłania wiadomości:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async (limit = 100) => {
    try {
      const response = await apiClient.get(`/api/echo/${mode}/history?limit=${limit}`);
      setMessages(response.data.history);
    } catch (error) {
      console.error('Błąd ładowania historii:', error);
    }
  };

  return { messages, loading, sendMessage, loadHistory };
};
```

### Komponent Testu Psychologicznego

```tsx
// components/PsychologicalTest.tsx
import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';

interface TestQuestion {
  test_name: string;
  description: string;
  instructions: string;
  scale: Array<{ label: string; value: number }>;
  questions: string[];
  questions_part_a?: string[];
  questions_part_b?: string[];
}

export const PsychologicalTest: React.FC<{ testType: 'asrs' | 'gad7' | 'phq9' }> = ({ testType }) => {
  const [testData, setTestData] = useState<TestQuestion | null>(null);
  const [answers, setAnswers] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadTestData();
  }, [testType]);

  const loadTestData = async () => {
    try {
      const response = await apiClient.get(`/api/tests/questions/${testType}`);
      setTestData(response.data);
      setAnswers(new Array(response.data.questions.length).fill(0));
    } catch (error) {
      console.error('Błąd ładowania testu:', error);
    }
  };

  const handleAnswerChange = (questionIndex: number, value: number) => {
    const newAnswers = [...answers];
    newAnswers[questionIndex] = value;
    setAnswers(newAnswers);
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      let requestData;
      
      if (testType === 'asrs') {
        requestData = {
          part_a: answers.slice(0, 6),
          part_b: answers.slice(6, 18)
        };
      } else {
        requestData = { answers };
      }

      const response = await apiClient.post(`/api/tests/${testType}`, requestData);
      console.log('Wynik testu:', response.data);
      // Obsłuż wynik testu
    } catch (error) {
      console.error('Błąd przesyłania testu:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!testData) return <div>Ładowanie...</div>;

  return (
    <div>
      <h2>{testData.test_name}</h2>
      <p>{testData.description}</p>
      <p>{testData.instructions}</p>
      
      <div>
        {testData.questions.map((question, index) => (
          <div key={index}>
            <p>{question}</p>
            <div>
              {testData.scale.map((option) => (
                <label key={option.value}>
                  <input
                    type="radio"
                    name={`question_${index}`}
                    value={option.value}
                    checked={answers[index] === option.value}
                    onChange={() => handleAnswerChange(index, option.value)}
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>
      
      <button onClick={handleSubmit} disabled={loading}>
        {loading ? 'Przesyłanie...' : 'Prześlij test'}
      </button>
    </div>
  );
};
```

## Obsługa Błędów

### Typowe Kody Błędów
- **400**: Błędne żądanie (walidacja danych)
- **401**: Nieautoryzowany (błędny/brak tokenu)
- **403**: Zabroniony (brak uprawnień)
- **404**: Nie znaleziono
- **409**: Konflikt (np. użytkownik już istnieje)
- **500**: Błąd serwera

### Przykład Obsługi Błędów

```typescript
// utils/errorHandler.ts
export const handleApiError = (error: any) => {
  if (error.response) {
    // Serwer odpowiedział z kodem błędu
    const { status, data } = error.response;
    
    switch (status) {
      case 400:
        return data.detail || 'Błędne dane';
      case 401:
        return 'Sesja wygasła. Zaloguj się ponownie.';
      case 403:
        return 'Brak uprawnień do wykonania tej operacji';
      case 404:
        return 'Nie znaleziono zasobu';
      case 409:
        return data.detail || 'Konflikt danych';
      case 500:
        return 'Błąd serwera. Spróbuj ponownie później.';
      default:
        return 'Wystąpił nieoczekiwany błąd';
    }
  } else if (error.request) {
    // Żądanie zostało wysłane, ale nie otrzymano odpowiedzi
    return 'Brak połączenia z serwerem';
  } else {
    // Coś innego się stało
    return 'Wystąpił błąd podczas konfiguracji żądania';
  }
};
```

## Najlepsze Praktyki

### 1. Zarządzanie Stanem
- Używaj Context API lub Redux do globalnego stanu
- Przechowuj tokeny w localStorage
- Implementuj automatyczne odświeżanie tokenów

### 2. Bezpieczeństwo
- Nigdy nie loguj tokenów w konsoli
- Waliduj dane po stronie klienta
- Używaj HTTPS w produkcji

### 3. UX/UI
- Pokaż loading states podczas żądań
- Implementuj error boundaries
- Używaj toast notifications dla komunikatów

### 4. Wydajność
- Implementuj paginację dla długich list
- Używaj React.memo dla komponentów
- Lazy load komponenty administracyjne

### 5. Testowanie
- Testuj komponenty z mockowanymi danymi API
- Używaj MSW (Mock Service Worker) do testów integracyjnych
- Testuj różne scenariusze błędów

## Struktura Projektu React (Sugerowana)

```
src/
├── api/
│   ├── client.ts
│   ├── auth.ts
│   ├── conversations.ts
│   ├── tests.ts
│   └── admin.ts
├── components/
│   ├── auth/
│   │   ├── LoginForm.tsx
│   │   └── RegisterForm.tsx
│   ├── conversations/
│   │   ├── ChatInterface.tsx
│   │   └── MessageList.tsx
│   ├── tests/
│   │   ├── TestSelector.tsx
│   │   └── TestForm.tsx
│   └── admin/
│       ├── UserManagement.tsx
│       └── Statistics.tsx
├── hooks/
│   ├── useAuth.ts
│   ├── useConversation.ts
│   └── useTests.ts
├── context/
│   └── AuthContext.tsx
├── types/
│   └── api.ts
└── utils/
    ├── errorHandler.ts
    └── constants.ts
```

## Wsparcie

W przypadku problemów z integracją:
1. Sprawdź dokumentację API pod adresem `/docs`
2. Sprawdź logi serwera
3. Upewnij się, że wszystkie zmienne środowiskowe są ustawione
4. Sprawdź połączenie z bazą danych i Ollama

---

**Uwaga**: Ten README zawiera wszystkie informacje potrzebne do stworzenia kompletnego frontendu React. Wszystkie endpointy są udokumentowane z przykładami żądań i odpowiedzi, a także zawiera przykłady implementacji komponentów React.
