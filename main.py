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

    name_part = ""
    if data_in.name:
        name_part = f"Обращайся к пользователю по имени {data_in.name}, правильно склоняя его по падежам в зависимости от контекста предложения. "

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
- Возраст: {data_in.age} лет
- Вес: {data_in.weight:.1f} кг
- Рост: {data_in.height} см
- Имя: {data_in.name if data_in.name else "не указано"}

Составь план тренировки на сегодня по следующей структуре:

Оценка состояния:
(1-2 предложения о состоянии тела и готовности к нагрузке)

Тренировка на сегодня:
(конкретные упражнения с количеством подходов и повторений)

Важно сегодня:
(1-2 совета по восстановлению или питанию)

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
                    "model": "mistralai/mistral-7b-instruct:free",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000
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