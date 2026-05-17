from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

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
async def get_plan(data: HealthData):
    rhr_status = "в норме"
    if data.resting_heart_rate > 70:
        rhr_status = "повышенный — признак усталости"
    elif data.resting_heart_rate > 63:
        rhr_status = "немного выше нормы"

    sleep_status = "хороший"
    if data.sleep_hours < 5:
        sleep_status = "очень мало"
    elif data.sleep_hours < 6.5:
        sleep_status = "недостаточно"
    elif data.sleep_hours < 7:
        sleep_status = "нормально, но можно лучше"

    hrv_status = "нет данных"
    if data.hrv > 0:
        if data.hrv > 60:
            hrv_status = "отличный"
        elif data.hrv > 40:
            hrv_status = "хороший"
        elif data.hrv > 25:
            hrv_status = "средний"
        else:
            hrv_status = "низкий"

    name_part = ""
    if data.name:
        name_part = f"Обращайся к пользователю по имени {data.name}, правильно склоняя его по падежам в зависимости от контекста предложения (именительный, родительный, дательный и т.д.). "

    prompt = f"""Ты персональный AI-тренер. Отвечай строго на русском языке. {name_part}
Правила оформления текста:
- Никаких английских слов, символов или иероглифов
- Никаких символов * или ** в тексте
- Заголовки пиши так: "Оценка состояния:", "Тренировка на сегодня:", "Важно сегодня:"
- После каждого заголовка сразу текст на новой строке
- Упражнения перечисляй через дефис: "- Название: подходы и повторения"

Данные пользователя:
- Пульс покоя: {data.resting_heart_rate:.0f} уд/мин ({rhr_status})
- Вариабельность пульса: {data.hrv:.0f} мс ({hrv_status})
- Сон: {data.sleep_hours:.1f} часов ({sleep_status})
- Шагов сегодня: {data.steps:.0f}
- Активных минут сегодня: {data.active_minutes:.0f} мин
- Часов стояния: {data.stand_hours} ч
- Готовность: {data.readiness_score}%
- Цель пользователя: {data.goal}
- Возраст: {data.age} лет
- Вес: {data.weight:.1f} кг
- Рост: {data.height} см
- Имя: {data.name if data.name else "не указано"}

Составь план тренировки на сегодня по следующей структуре:

Оценка состояния:
(1-2 предложения о состоянии тела и готовности к нагрузке)

Тренировка на сегодня:
(конкретные упражнения с количеством подходов и повторений)

Важно сегодня:
(1-2 совета по восстановлению или питанию)

Если восстановление плохое — предложи лёгкую тренировку или отдых."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000
    )

    return {
        "plan": response.choices[0].message.content,
        "readiness": data.readiness_score
    }