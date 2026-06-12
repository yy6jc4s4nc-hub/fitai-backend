# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class HealthData(BaseModel):
    resting_heart_rate: float = 0
    hrv: float = 0
    sleep_hours: float = 0
    steps: float = 0
    readiness_score: int = 0
    goal: str = "набор мышечной массы"
    age: int = 20
    weight: float = 75
    name: str = ""
    active_minutes: float = 0
    stand_hours: int = 0
    height: int = 175
    sport: str = "общая физическая форма"
    experience: str = "средний"
    detailed: bool = False
    wellness_feeling: int = 0
    wellness_soreness: int = 0
    wellness_sleep: int = 0
    wellness_description: str = ""

@app.get("/")
def root():
    return {"status": "FitAI backend работает"}

@app.post("/get-plan")
async def get_plan(data_in: HealthData):
    rhr_status = "в норме"
    if data_in.resting_heart_rate > 70:
        rhr_status = "повышенный — признак усталости"
    elif data_in.resting_heart_rate > 63:
        rhr_status = "немного выше нормы"

    sleep_status = "хороший"
    if data_in.sleep_hours < 5:
        sleep_status = "очень мало"
    elif data_in.sleep_hours < 6.5:
        sleep_status = "недостаточно"
    elif data_in.sleep_hours < 7:
        sleep_status = "нормально, но можно лучше"

    hrv_status = "нет данных"
    if data_in.hrv > 0:
        if data_in.hrv > 60:
            hrv_status = "отличный"
        elif data_in.hrv > 40:
            hrv_status = "хороший"
        elif data_in.hrv > 25:
            hrv_status = "средний"
        else:
            hrv_status = "низкий"

    # Определяем, есть ли данные с часов
    has_wearable_data = data_in.hrv > 0 or data_in.resting_heart_rate > 0
    has_wellness_data = data_in.wellness_description != ""

    name_part = ""
    if data_in.name:
        name_part = f"Обращайся к пользователю по имени {data_in.name}, правильно склоняя его по падежам в зависимости от контекста предложения. "

    # КРАТКИЙ ПЛАН
    if not data_in.detailed:
        # Специальный промпт для пользователей без часов (есть опросник, нет данных с часов)
        if not has_wearable_data and has_wellness_data:
            prompt = f"""Ты персональный AI-тренер. Отвечай строго на русском языке. {name_part}
Правила оформления текста:
- Никаких английских слов, символов или иероглифов
- Никаких символов * или ** в тексте
- Заголовки пиши так: "Оценка состояния:", "Тренировка на сегодня:", "Важно сегодня:"
- После каждого заголовка сразу текст на новой строке
- Упражнения перечисляй через дефис
- НЕ упоминай отсутствие данных с часов, пульса или HRV
- Строй план ТОЛЬКО на основе субъективной оценки пользователя

Пользователь не использует умные часы.
Субъективная оценка состояния сегодня: {data_in.wellness_description}
Готовность по ощущениям: {data_in.readiness_score}%
Цель: {data_in.goal}
Вид спорта: {data_in.sport}
Опыт: {data_in.experience}
Возраст: {data_in.age} лет
Вес: {data_in.weight:.1f} кг
Рост: {data_in.height} см

Составь КРАТКИЙ ТЕЗИСНЫЙ план тренировки на основе самочувствия.

Оценка состояния:
(2-3 предложения о состоянии на основе субъективной оценки пользователя)

Тренировка на сегодня:
(тезисно: 3-5 упражнений без весов и подходов)

Важно сегодня:
(2-3 тезиса по питанию и восстановлению)

Если самочувствие плохое — предложи отдых или лёгкую активность."""

        else:
            # Обычный промпт с данными часов или если нет ни часов, ни опросника
            prompt = f"""Ты персональный AI-тренер. Отвечай строго на русском языке. {name_part}
Правила оформления текста:
- Никаких английских слов, символов или иероглифов
- Никаких символов * или ** в тексте
- Заголовки пиши так: "Оценка состояния:", "Тренировка на сегодня:", "Важно сегодня:"
- После каждого заголовка сразу текст на новой строке
- Упражнения перечисляй через дефис
- Без детализации весов, времени и подходов

Данные пользователя:
- Пульс покоя: {data_in.resting_heart_rate:.0f} уд/мин ({rhr_status})
- Вариабельность пульса: {data_in.hrv:.0f} мс ({hrv_status})
- Сон: {data_in.sleep_hours:.1f} часов ({sleep_status})
- Шагов сегодня: {data_in.steps:.0f}
- Активных минут сегодня: {data_in.active_minutes:.0f} мин
- Часов стояния: {data_in.stand_hours} ч
- Готовность: {data_in.readiness_score}%
- Цель пользователя: {data_in.goal}
- Вид спорта: {data_in.sport}
- Опыт: {data_in.experience}
- Возраст: {data_in.age} лет
- Вес: {data_in.weight:.1f} кг
- Рост: {data_in.height} см
{f"- Субъективное самочувствие: {data_in.wellness_description}" if data_in.wellness_description else ""}

Составь КРАТКИЙ ТЕЗИСНЫЙ план тренировки.

Оценка состояния:
(напиши 2-3 предложения подробно о состоянии тела на основе показателей пульса, сна, HRV и готовности)

Тренировка на сегодня:
(только тезисы: какие упражнения или группы мышц тренируем, 3-5 пунктов, без весов, подходов и времени)

Важно сегодня:
(короткие тезисы по питанию, водному балансу и восстановлению, 2-3 пункта)

Если восстановление плохое — предложи отдых или лёгкую активность."""

    # ПОДРОБНЫЙ ПЛАН
    else:
        # Для подробного плана тоже убираем упоминания об отсутствии данных, если нет часов
        if not has_wearable_data and has_wellness_data:
            prompt = f"""Ты персональный AI-тренер. Отвечай строго на русском языке. {name_part}
Правила оформления текста:
- Никаких английских слов, символов или иероглифов
- Никаких символов * или ** в тексте
- Заголовки пиши так: "Тренировка на сегодня:", "Важно сегодня:"
- После каждого заголовка сразу текст на новой строке
- Упражнения перечисляй через дефис: "- Название: подходы и повторения"
- НЕ упоминай отсутствие данных с часов, пульса или HRV
- Строй план ТОЛЬКО на основе субъективной оценки пользователя

Пользователь не использует умные часы.
Субъективная оценка состояния сегодня: {data_in.wellness_description}
Готовность по ощущениям: {data_in.readiness_score}%
Цель: {data_in.goal}
Вид спорта: {data_in.sport}
Опыт: {data_in.experience}
Возраст: {data_in.age} лет
Вес: {data_in.weight:.1f} кг
Рост: {data_in.height} см

Составь ПОДРОБНЫЙ план тренировки на основе самочувствия.

Тренировка на сегодня:
Распиши подробно для цели "{data_in.goal}" и вида спорта "{data_in.sport}":
- Разминка: упражнения с временем выполнения каждого
- Основные упражнения: название, подходы x повторения, вес в кг (рассчитай под опыт "{data_in.experience}" и вес тела {data_in.weight:.1f} кг), отдых между подходами в секундах, техническая подсказка
- Заминка: растяжка с временем удержания каждой позиции

Важно сегодня:
Распиши очень подробно:
- Питание до тренировки: продукты, граммовки, время приёма
- Питание после тренировки: продукты, граммовки белка и углеводов, время приёма
- Восстановление: сон, растяжка, водный баланс с количеством мл
- Персональный совет исходя из самочувствия

Если самочувствие плохое — предложи лёгкую тренировку или отдых."""

        else:
            # Обычный подробный промпт с данными часов
            prompt = f"""Ты персональный AI-тренер. Отвечай строго на русском языке. {name_part}
Правила оформления текста:
- Никаких английских слов, символов или иероглифов
- Никаких символов * или ** в тексте
- Заголовки пиши так: "Оценка состояния:", "Тренировка на сегодня:", "Важно сегодня:"
- После каждого заголовка сразу текст на новой строке
- Упражнения перечисляй через дефис: "- Название: подходы и повторения"

Данные пользователя:
- Пульс покоя: {data_in.resting_heart_rate:.0f} уд/мин ({rhr_status})
- Вариабельность пульса: {data_in.hrv:.0f} мс ({hrv_status})
- Сон: {data_in.sleep_hours:.1f} часов ({sleep_status})
- Шагов сегодня: {data_in.steps:.0f}
- Активных минут сегодня: {data_in.active_minutes:.0f} мин
- Часов стояния: {data_in.stand_hours} ч
- Готовность: {data_in.readiness_score}%
- Цель пользователя: {data_in.goal}
- Вид спорта: {data_in.sport}
- Опыт: {data_in.experience}
- Возраст: {data_in.age} лет
- Вес: {data_in.weight:.1f} кг
- Рост: {data_in.height} см
- Имя: {data_in.name if data_in.name else "не указано"}
{f"- Субъективное самочувствие: {data_in.wellness_description}" if data_in.wellness_description else ""}

Составь ПОДРОБНЫЙ план тренировки. Оценку состояния НЕ пиши — она уже есть у пользователя.

Тренировка на сегодня:
Распиши подробно для цели "{data_in.goal}" и вида спорта "{data_in.sport}":
- Разминка: упражнения с временем выполнения каждого
- Основные упражнения: название, подходы x повторения, вес в кг (рассчитай под опыт "{data_in.experience}" и вес тела {data_in.weight:.1f} кг), отдых между подходами в секундах, техническая подсказка
- Заминка: растяжка с временем удержания каждой позиции

Важно сегодня:
Распиши очень подробно:
- Питание до тренировки: продукты, граммовки, время приёма
- Питание после тренировки: продукты, граммовки белка и углеводов, время приёма
- Восстановление: сон, растяжка, водный баланс с количеством мл
- Персональный совет исходя из показателей восстановления

Если восстановление плохое — предложи лёгкую тренировку или отдых."""

    try:
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openai/gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2000 if data_in.detailed else 1000
                }
            )
            result = resp.json()
            print(f"ОТВЕТ API: {result}")
            if "choices" in result:
                plan_text = result["choices"][0]["message"]["content"]
            else:
                plan_text = str(result)

        return {
            "plan": plan_text,
            "readiness": data_in.readiness_score
        }
    except Exception as e:
        print(f"ОШИБКА: {e}")
        return {
            "plan": f"Ошибка: {str(e)}",
            "readiness": data_in.readiness_score
        }