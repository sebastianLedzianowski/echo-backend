"""
Routes dla testów psychologicznych (ASRS, GAD-7, PHQ-9)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.database.db import get_db
from src.database.models import User, PsychologicalTest
from src.schemas import (
    TestResult, TestHistoryResponse,
    ASRSAnswers, GAD7Answers, PHQ9Answers, TestTypeEnum
)
from src.services.auth import auth_service
from src.services.psychological_tests import PsychologicalTestService

router = APIRouter(prefix="/tests", tags=["Testy psychologiczne"])


@router.post("/asrs", response_model=TestResult, 
             summary="Prześlij test ASRS v1.1")
async def submit_asrs_test(
    answers: ASRSAnswers,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Prześlij odpowiedzi na test ASRS v1.1 (Adult ADHD Self-Report Scale)
    
    Test składa się z:
    - Części A: 6 pytań (kluczowe dla diagnozy) Jeśli w części A ≥4 odpowiedzi to 'Często' lub 'Bardzo często' – wysokie ryzyko ADHD.
    - Części B: 12 pytań (dodatkowe informacje) Część B dostarcza dodatkowych informacji o nasileniu objawów. Wszystkie pytania w części B mają taką samą wagę.
    
    Skala odpowiedzi: 0-4 (Nigdy, Rzadko, Czasami, Często, Bardzo często)
    """
    try:
        # Walidacja odpowiedzi
        for answer in answers.part_a + answers.part_b:
            if not 0 <= answer <= 4:
                raise HTTPException(
                    status_code=400,
                    detail="Odpowiedzi muszą być w zakresie 0-4"
                )
        
        # Przygotowanie danych
        answers_dict = {
            "part_a": answers.part_a,
            "part_b": answers.part_b
        }
        
        # Obliczenie wyniku
        score, interpretation = PsychologicalTestService.calculate_asrs_score(answers_dict)
        
        # Generowanie analizy AI
        ai_analysis = await PsychologicalTestService.get_ai_analysis(
            "asrs", answers_dict, score, interpretation
        )
        
        # Zapisanie w bazie danych
        test_result = PsychologicalTest(
            user_id=current_user.id,
            test_type="asrs",
            answers=answers_dict,
            score=score,
            interpretation=interpretation,
            ai_analysis=ai_analysis
        )
        
        db.add(test_result)
        await db.commit()
        await db.refresh(test_result)
        
        return TestResult.model_validate(test_result)
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Błąd podczas przetwarzania testu: {str(e)}"
        )


@router.post("/gad7", response_model=TestResult, summary="Prześlij test GAD-7")
async def submit_gad7_test(
    answers: GAD7Answers,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Prześlij odpowiedzi na test GAD-7 (Kwestionariusz Zaburzeń Lękowych)
    
    Test składa się z 7 pytań o objawy lęku w ciągu ostatnich 2 tygodni.
    
    Skala odpowiedzi: 0-3 (Wcale, Kilka dni, Ponad połowę dni, Prawie codziennie)
    Interpretacja:
    - 0-4: Minimalny poziom lęku
    - 5-9: Łagodny lęk
    - 10-14: Umiarkowany lęk
    - 15-21: Ciężki lęk
    """
    try:
        # Walidacja odpowiedzi
        for answer in answers.answers:
            if not 0 <= answer <= 3:
                raise HTTPException(
                    status_code=400,
                    detail="Odpowiedzi muszą być w zakresie 0-3"
                )
        
        # Przygotowanie danych
        answers_dict = {"answers": answers.answers}
        
        # Obliczenie wyniku
        score, interpretation = PsychologicalTestService.calculate_gad7_score(answers_dict)
        
        # Generowanie analizy AI
        ai_analysis = await PsychologicalTestService.get_ai_analysis(
            "gad7", answers_dict, score, interpretation
        )
        
        # Zapisanie w bazie danych
        test_result = PsychologicalTest(
            user_id=current_user.id,
            test_type="gad7",
            answers=answers_dict,
            score=score,
            interpretation=interpretation,
            ai_analysis=ai_analysis
        )
        
        db.add(test_result)
        await db.commit()
        await db.refresh(test_result)
        
        return TestResult.model_validate(test_result)
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Błąd podczas przetwarzania testu: {str(e)}"
        )


@router.post("/phq9", response_model=TestResult, summary="Prześlij test PHQ-9")
async def submit_phq9_test(
    answers: PHQ9Answers,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Prześlij odpowiedzi na test PHQ-9 (Kwestionariusz Zdrowia Pacjenta-9)
    
    Test składa się z 9 pytań o objawy depresji w ciągu ostatnich 2 tygodni.
    
    Skala odpowiedzi: 0-3 (Wcale, Kilka dni, Ponad połowę dni, Prawie codziennie)
    Interpretacja:
    - 0-4: Brak objawów depresji
    - 5-9: Łagodna depresja
    - 10-14: Umiarkowana depresja
    - 15-19: Umiarkowanie ciężka depresja
    - 20-27: Ciężka depresja
    
    **UWAGA**: Pytanie 9 dotyczy myśli samobójczych - w przypadku wysokiej odpowiedzi
    zaleca się natychmiastową konsultację z lekarzem psychiatrą.
    """
    try:
        # Walidacja odpowiedzi
        for answer in answers.answers:
            if not 0 <= answer <= 3:
                raise HTTPException(
                    status_code=400,
                    detail="Odpowiedzi muszą być w zakresie 0-3"
                )
        
        # Sprawdzenie pytania 9 (myśli samobójcze)
        if len(answers.answers) >= 9 and answers.answers[8] >= 2:
            # Dodanie ostrzeżenia do analizy jeśli są myśli samobójcze
            pass
        
        # Przygotowanie danych
        answers_dict = {"answers": answers.answers}
        
        # Obliczenie wyniku
        score, interpretation = PsychologicalTestService.calculate_phq9_score(answers_dict)
        
        # Generowanie analizy AI
        ai_analysis = await PsychologicalTestService.get_ai_analysis(
            "phq9", answers_dict, score, interpretation
        )
        
        # Zapisanie w bazie danych
        test_result = PsychologicalTest(
            user_id=current_user.id,
            test_type="phq9",
            answers=answers_dict,
            score=score,
            interpretation=interpretation,
            ai_analysis=ai_analysis
        )
        
        db.add(test_result)
        await db.commit()
        await db.refresh(test_result)
        
        return TestResult.model_validate(test_result)
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Błąd podczas przetwarzania testu: {str(e)}"
        )


@router.get("/history", response_model=TestHistoryResponse, summary="Historia testów użytkownika")
async def get_test_history(
    test_type: TestTypeEnum = None,
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Pobierz historię testów psychologicznych dla zalogowanego użytkownika
    
    Parametry:
    - test_type: Opcjonalnie filtruj po typie testu (asrs, gad7, phq9)
    - limit: Maksymalna liczba wyników (domyślnie 10)
    - offset: Przesunięcie dla paginacji (domyślnie 0)
    """
    query = select(PsychologicalTest).filter(
        PsychologicalTest.user_id == current_user.id
    )
    
    if test_type:
        query = query.filter(PsychologicalTest.test_type == test_type.value)
    
    # Pobierz liczbę wszystkich wyników
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total_count = count_result.scalar()
    
    # Pobierz wyniki z paginacją
    paginated_query = query.order_by(PsychologicalTest.created_at.desc())\
                          .offset(offset)\
                          .limit(limit)
    
    result = await db.execute(paginated_query)
    tests = result.scalars().all()
    
    return TestHistoryResponse(
        tests=[TestResult.model_validate(test) for test in tests],
        total_count=total_count
    )


@router.get("/result/{test_id}", response_model=TestResult, summary="Pobierz wynik konkretnego testu")
async def get_test_result(
    test_id: int,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Pobierz szczegółowy wynik konkretnego testu
    """
    query = select(PsychologicalTest).filter(
        PsychologicalTest.id == test_id,
        PsychologicalTest.user_id == current_user.id
    )
    result = await db.execute(query)
    test_result = result.scalar_one_or_none()
    
    if not test_result:
        raise HTTPException(
            status_code=404,
            detail="Test nie został znaleziony"
        )
    
    return TestResult.model_validate(test_result)


@router.get("/questions/{test_type}", summary="Pobierz pytania dla konkretnego testu")
async def get_test_questions(
        test_type: TestTypeEnum,
        current_user: User = Depends(auth_service.get_current_user),
):
    """
    Pobierz pytania dla konkretnego typu testu
    """
    questions_data = {
        "asrs": {
            "test_name": "ASRS v1.1",
            "description": "Adult ADHD Self-Report Scale (ASRS v1.1) to narzędzie przesiewowe opracowane przez WHO do oceny objawów ADHD u dorosłych.",
            "instructions": "Odpowiedz na pytania na podstawie swoich odczuć i doświadczeń w ciągu ostatnich 6 miesięcy.",
            "source": [
                "authors": "Kessler RC, Adler L, Ames M, Demler O, Faraone S, Hiripi E, et al. (2005)",
                "link_original": "https://pubmed.ncbi.nlm.nih.gov/15841682/",
                "link_official": "https://www.hcp.med.harvard.edu/ncs/asrs.php"
            ],
            "scale": [
                {"label": "Nigdy", "value": 0},
                {"label": "Rzadko", "value": 1},
                {"label": "Czasami", "value": 2},
                {"label": "Często", "value": 3},
                {"label": "Bardzo często", "value": 4}
            ],
            "questions_part_a": [
                "Jak często ma Pan(i) trudności ze skupieniem się na szczegółach podczas wykonywania nudnych lub powtarzalnych zadań?",
                "Jak często ma Pan(i) trudności z utrzymaniem uwagi przy wykonywaniu nudnych lub powtarzalnych zadań?",
                "Jak często ma Pan(i) trudności z kończeniem rzeczy, które Pan(i) rozpoczął(a)?",
                "Jak często ma Pan(i) trudności z uporządkowaniem działań wymagających organizacji?",
                "Jak często unika Pan(i) lub odkłada na później zadania, które wymagają dużo myślenia?",
                "Jak często gubi Pan(i) rzeczy potrzebne do wykonywania zadań lub czynności?"
            ],
            "questions_part_b": [
                "Jak często czuje się Pan(i) niespokojny/a lub porusza rękami/nogami podczas siedzenia?",
                "Jak często czuje się Pan(i) nadmiernie aktywny/a i zmuszony/a do robienia różnych rzeczy, jakby był Pan(i) \"napędzany silnikiem\"?",
                "Jak często ma Pan(i) trudności ze słuchaniem, gdy ktoś mówi bezpośrednio do Pana(i)?",
                "Jak często ma Pan(i) trudności z przestrzeganiem instrukcji lub kończeniem pracy?",
                "Jak często ma Pan(i) problemy z pamiętaniem terminów lub zobowiązań?",
                "Jak często przerywa Pan(i) innym, zanim skończą mówić?",
                "Jak często kończy Pan(i) zdania innych ludzi?",
                "Jak często odpowiada Pan(i), zanim pytanie zostanie w pełni zadane?",
                "Jak często ma Pan(i) trudności z czekaniem na swoją kolej?",
                "Jak często przerywa Pan(i) innym w trakcie rozmowy lub przeszkadza im?",
                "Jak często odczuwa Pan(i) wewnętrzny niepokój?",
                "Jak często robi Pan(i) kilka rzeczy naraz, ale rzadko którąś kończy?"
            ]
        },
        "gad7": {
            "test_name": "GAD-7",
            "description": "Kwestionariusz GAD-7 służy do oceny nasilenia objawów lęku uogólnionego.",
            "instructions": "Odpowiedz na pytania na podstawie swoich odczuć i doświadczeń w ciągu ostatnich 2 tygodni.",
            "source": [
                "authors": "Spitzer RL, Kroenke K, Williams JBW, B广ay-Jones D (2006)",
                "link_original": "https://pubmed.ncbi.nlm.nih.gov/16717171/",
                "link_official": "https://www.psychiatry.org/patients-families/anxiety/gad-7"
            ],
            "scale": [
                {"label": "Wcale", "value": 0},
                {"label": "Kilka dni", "value": 1},
                {"label": "Ponad połowę dni", "value": 2},
                {"label": "Prawie codziennie", "value": 3}
            ],
            "questions": [
                "Uczucie nerwowości, lęku lub napięcia.",
                "Brak możliwości powstrzymania się od zamartwiania.",
                "Zamartwianie się zbyt wieloma różnymi sprawami.",
                "Trudności z odprężeniem się.",
                "Bycie tak niespokojnym, że trudno usiedzieć w miejscu.",
                "Łatwe irytowanie się lub bycie poirytowanym.",
                "Uczucie strachu, jakby coś złego miało się wydarzyć."
            ]
        },
        "phq9": {
            "test_name": "PHQ-9",
            "description": "Kwestionariusz Zdrowia Pacjenta-9 (PHQ-9) to narzędzie przesiewowe do oceny nasilenia objawów depresyjnych.",
            "instructions": "Odpowiedz na pytania na podstawie swoich odczuć i doświadczeń w ciągu ostatnich 2 tygodni.",
            "source": [
                "authors": "Spitzer RL, Kroenke K, Williams JB (2001)",
                "link_original": "https://pubmed.ncbi.nlm.nih.gov/11556941/",
                "link_polish": "https://www.ecfs.eu/sites/default/files/general-content-files/working-groups/Mental%20Health/PHQ9_Polish%20for%20Poland.pdf"
            ],
            "scale": [
                {"label": "Wcale", "value": 0},
                {"label": "Kilka dni", "value": 1},
                {"label": "Ponad połowę dni", "value": 2},
                {"label": "Prawie codziennie", "value": 3}
            ],
            "questions": [
                "Mało zainteresowania lub przyjemności z wykonywania różnych czynności.",
                "Przygnębienie, depresja lub poczucie beznadziei.",
                "Problemy z zasypianiem, przesypianiem nocy lub nadmierna senność.",
                "Zmęczenie lub brak energii.",
                "Słaby apetyt lub przejadanie się.",
                "Złe myślenie o sobie – że jest się nieudacznikiem albo że zawiodło się rodzinę lub samego siebie.",
                "Trudności z koncentracją, np. podczas czytania gazety lub oglądania telewizji.",
                "Spowolnienie ruchów i mowy zauważalne przez innych lub przeciwnie – nadmierny niepokój i podenerwowanie.",
                "Myśli, że lepiej byłoby nie żyć albo chęć zrobienia sobie krzywdy."
            ]
        }
    }
    
    if test_type.value not in questions_data:
        raise HTTPException(
            status_code=404,
            detail="Nieznany typ testu"
        )
    
    return questions_data[test_type.value]
