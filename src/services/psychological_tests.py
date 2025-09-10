"""
Serwis dla testów psychologicznych
"""
from typing import Dict, Any, Tuple
from src.services.ai import get_ai_analysis_response


class PsychologicalTestService:
    """Serwis do obsługi testów psychologicznych"""
    
    @staticmethod
    def calculate_asrs_score(answers: Dict[str, Any]) -> Tuple[float, str]:
        """
        Oblicza wynik dla testu ASRS v1.1
        
        Args:
            answers: Słownik z odpowiedziami (part_a, part_b)
            
        Returns:
            Tuple[float, str]: (wynik, interpretacja)
        """
        part_a = answers.get('part_a', [])
        part_b = answers.get('part_b', [])
        
        # Część A - sprawdzamy ile odpowiedzi to "Często" (3) lub "Bardzo często" (4)
        high_scores_a = sum(1 for score in part_a if score >= 3)

        # Całkowity wynik to suma wszystkich odpowiedzi
        total_score = sum(part_a) + sum(part_b)
        # maksymalnie 4 punkty za pytanie
        max_possible = (len(part_a) + len(part_b)) * 4
        
        if max_possible == 0:
            return 0.0, "Brak odpowiedzi do analizy"

        # Interpretacja na podstawie części A
        if high_scores_a >= 4:
            interpretation = "Wysokie ryzyko ADHD"
        else:
            interpretation = "Niskie ryzyko ADHD"
            
        return total_score / max_possible * 100, interpretation
    
    @staticmethod
    def calculate_gad7_score(answers: Dict[str, Any]) -> Tuple[float, str]:
        """
        Oblicza wynik dla testu GAD-7
        
        Args:
            answers: Słownik z odpowiedziami
            
        Returns:
            Tuple[float, str]: (wynik, interpretacja)
        """
        answer_list = answers.get('answers', [])
        total_score = sum(answer_list)
        
        if total_score <= 4:
            interpretation = "Minimalny poziom lęku"
        elif total_score <= 9:
            interpretation = "Łagodny lęk"
        elif total_score <= 14:
            interpretation = "Umiarkowany lęk"
        else:
            interpretation = "Ciężki lęk"
            
        return float(total_score), interpretation
    
    @staticmethod
    def calculate_phq9_score(answers: Dict[str, Any]) -> Tuple[float, str]:
        """
        Oblicza wynik dla testu PHQ-9
        
        Args:
            answers: Słownik z odpowiedziami
            
        Returns:
            Tuple[float, str]: (wynik, interpretacja)
        """
        answer_list = answers.get('answers', [])
        total_score = sum(answer_list)
        
        if total_score <= 4:
            interpretation = "Brak objawów depresji"
        elif total_score <= 9:
            interpretation = "Łagodna depresja"
        elif total_score <= 14:
            interpretation = "Umiarkowana depresja"
        elif total_score <= 19:
            interpretation = "Umiarkowanie ciężka depresja"
        else:
            interpretation = "Ciężka depresja"
            
        return float(total_score), interpretation
    
    @staticmethod
    async def get_ai_analysis(test_type: str, answers: Dict[str, Any],
                              score: float, interpretation: str) -> str:
        """
        Generuje analizę AI dla wyniku testu

        Args:
            test_type: Typ testu (asrs, gad7, phq9)
            answers: Odpowiedzi użytkownika
            score: Obliczony wynik
            interpretation: Podstawowa interpretacja

        Returns:
            str: Szczegółowa analiza AI
        """
        
        # Przygotowanie promptu na podstawie typu testu
        if test_type == "asrs":
            prompt = f"""Jesteś doświadczonym psychologiem klinicznym specjalizującym się w diagnostyce ADHD u dorosłych.

Przeanalizuj wyniki testu ASRS v1.1 (Adult ADHD Self-Report Scale):

Część A (6 pytań kluczowych): {answers.get('part_a', [])}
Część B (12 pytań dodatkowych): {answers.get('part_b', [])}
Wynik procentowy: {score:.1f}%
Interpretacja: {interpretation}

Zadania:
1. Przeanalizuj wzorce odpowiedzi w części A i B
2. Oceń nasilenie objawów ADHD
3. Zidentyfikuj dominujące obszary problemowe
4. Zaproponuj konkretne kroki dalszej diagnostyki

WAŻNE:
- Test ma charakter PRZESIEWOWY, nie diagnostyczny
- Zawsze zalecaj konsultację ze specjalistą (psycholog/psychiatra)
- Używaj empatycznego, ale profesjonalnego tonu
- Unikaj stawiania ostatecznych diagnoz
- Skup się na praktycznych rekomendacjach
- Nie powtarzaj wyników w odpowiedzi.

Napisz analizę w kilku zdaniach, która będzie pomocna i wspierająca dla osoby badanej."""
            
        elif test_type == "gad7":
            prompt = f"""Jesteś doświadczonym psychologiem klinicznym specjalizującym się w zaburzeniach lękowych.

Przeanalizuj wyniki testu GAD-7 (Kwestionariusz Zaburzeń Lękowych):

Odpowiedzi na 7 pytań: {answers.get('answers', [])}
Wynik: {score} punktów
Interpretacja: {interpretation}

Zadania:
1. Przeanalizuj nasilenie objawów lęku
2. Zidentyfikuj dominujące symptomy lękowe
3. Oceń wpływ na codzienne funkcjonowanie
4. Zaproponuj strategie radzenia sobie z lękiem

WAŻNE:
- Test ma charakter PRZESIEWOWY, nie diagnostyczny
- Zawsze zalecaj konsultację ze specjalistą (psycholog/psychiatra)
- Używaj empatycznego, ale profesjonalnego tonu
- Unikaj stawiania ostatecznych diagnoz
- Skup się na praktycznych rekomendacjach
- Nie powtarzaj wyników w odpowiedzi.

Napisz analizę w kilku zdaniach, która będzie pomocna i wspierająca dla osoby badanej."""
            
        else:  # phq9
            answers_list = answers.get('answers', [])
            q9_warning = ""
            if len(answers_list) >= 9 and answers_list[8] >= 2:
                q9_warning = ("\n\n🚨 KRYTYCZNE: Wysokie ryzyko myśli samobójczych - "
                             "KONIECZNA PILNA KONSULTACJA Z PSYCHIATRĄ!")

            prompt = f"""Jesteś doświadczonym psychologiem klinicznym specjalizującym się w zaburzeniach nastroju.

Przeanalizuj wyniki testu PHQ-9 (Kwestionariusz Zdrowia Pacjenta-9):

Odpowiedzi na 9 pytań: {answers_list}
Wynik: {score} punktów
Interpretacja: {interpretation}{q9_warning}

Zadania:
1. Przeanalizuj nasilenie objawów depresyjnych
2. Zidentyfikuj dominujące symptomy depresji
3. Oceń wpływ na codzienne funkcjonowanie
4. Zaproponuj strategie wsparcia i leczenia

WAŻNE:
- Test ma charakter PRZESIEWOWY, nie diagnostyczny
- Zawsze zalecaj konsultację ze specjalistą (psycholog/psychiatra)
- Używaj empatycznego, ale profesjonalnego tonu
- Unikaj stawiania ostatecznych diagnoz
- Skup się na praktycznych rekomendacjach
- W przypadku myśli samobójczych podkreśl pilną potrzebę pomocy
- Nie powtarzaj wyników w odpowiedzi.

Napisz analizę w kilku zdaniach, która będzie pomocna i wspierająca dla osoby badanej."""
        
        # Wywołanie AI po zdefiniowaniu promptu
        try:
            ai_response = await get_ai_analysis_response(prompt)
            return ai_response
        except Exception as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Błąd generowania analizy AI: {e}")
            return (f"Nie udało się wygenerować szczegółowej analizy. "
                    f"Podstawowa interpretacja: {interpretation}")
