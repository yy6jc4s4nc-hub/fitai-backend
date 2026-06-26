# -*- coding: utf-8 -*-
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from auth_utils import create_access_token, decode_access_token, hash_password, verify_password
from database import User, UserSyncData, get_db, init_db
from decrypt_payload import decrypt_plan_request_body

app = FastAPI()
security = HTTPBearer(auto_error=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(default="", max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    name: str


class UserProfileResponse(BaseModel):
    user_id: str
    email: str
    name: str


class SyncPushRequest(BaseModel):
    payload: dict[str, Any]
    updated_at: Optional[str] = None


class SyncPullResponse(BaseModel):
    payload: dict[str, Any]
    updated_at: Optional[str] = None


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    try:
        token_data = decode_access_token(credentials.credentials)
        user_id = token_data.get("sub")
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Недействительный токен") from exc

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user


@app.post("/auth/register", response_model=AuthResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Аккаунт с таким email уже существует")

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=hash_password(body.password),
        name=body.name.strip(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, email=user.email)
    return AuthResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        name=user.name,
    )


@app.post("/auth/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    token = create_access_token(user_id=user.id, email=user.email)
    return AuthResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        name=user.name,
    )


@app.get("/auth/me", response_model=UserProfileResponse)
def me(current_user: User = Depends(get_current_user)):
    return UserProfileResponse(
        user_id=current_user.id,
        email=current_user.email,
        name=current_user.name,
    )


@app.get("/sync/pull", response_model=SyncPullResponse)
def sync_pull(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(UserSyncData, current_user.id)
    if row is None:
        return SyncPullResponse(payload={}, updated_at=None)

    try:
        payload = json.loads(row.payload)
    except json.JSONDecodeError:
        payload = {}

    updated_at = row.updated_at.isoformat() if row.updated_at else None
    return SyncPullResponse(payload=payload, updated_at=updated_at)


@app.put("/sync/push", response_model=SyncPullResponse)
def sync_push(
    body: SyncPushRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    payload_json = json.dumps(body.payload, ensure_ascii=False)

    row = db.get(UserSyncData, current_user.id)
    if row is None:
        row = UserSyncData(user_id=current_user.id, payload=payload_json, updated_at=now)
        db.add(row)
    else:
        row.payload = payload_json
        row.updated_at = now

    db.commit()
    db.refresh(row)

    return SyncPullResponse(
        payload=body.payload,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
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
    years_of_experience: int = 0
    cycle_tracking_enabled: bool = False
    cycle_phase: str = ""
    cycle_phase_description: str = ""
    cycle_day: Optional[int] = None
    cycle_length: Optional[int] = None
    period_length: Optional[int] = None

@app.get("/")
def root():
    return {"status": "FitAI backend работает"}

@app.post("/get-plan")
async def get_plan(request: Request):
    try:
        raw_body = await request.json()
        decrypted = decrypt_plan_request_body(raw_body)
        data_in = HealthData(**decrypted)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid request payload: {exc}")

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

    # Определяем уровень атлета по стажу и опыту
    def get_athlete_level(years: int) -> str:
        if years == 0:
            return "новичок (менее года) — только базовые упражнения, минимальные веса, главное техника"
        elif years == 1:
            return "начинающий (1 год) — осваивает базовые движения, веса 30-50% от максимума"
        elif years <= 3:
            return f"любитель ({years} года) — знает базовые упражнения, веса 50-65% от максимума"
        elif years <= 5:
            return f"опытный любитель ({years} лет) — хорошая техника, веса 65-75% от максимума"
        elif years <= 10:
            return f"продвинутый ({years} лет) — отличная техника, веса 75-85% от максимума"
        else:
            return f"эксперт ({years} лет) — профессиональный уровень, веса 85-95% от максимума"

    athlete_level = get_athlete_level(data_in.years_of_experience)

    # Строка стажа для промпта
    years_str = "менее года" if data_in.years_of_experience == 0 else f"{data_in.years_of_experience} лет"

    # Определяем наличие данных с часов
    has_wearable_data = data_in.hrv > 0 or data_in.resting_heart_rate > 0
    has_wellness_data = data_in.wellness_description != ""

    name_part = ""
    if data_in.name:
        name_part = f"Обращайся к пользователю по имени {data_in.name}, правильно склоняя его по падежам. "

    cycle_info = ""
    if data_in.cycle_tracking_enabled:
        cycle_info = (
            f"- Менструальный цикл: фаза {data_in.cycle_phase}, "
            f"день {data_in.cycle_day if data_in.cycle_day is not None else 'не указан'}\n"
            f"- Рекомендации по фазе: {data_in.cycle_phase_description or data_in.cycle_phase}\n"
        )

    # КРАТКИЙ ПЛАН
    if not data_in.detailed:

        # Промпт для пользователей БЕЗ часов
        if not has_wearable_data and has_wellness_data:
            prompt = f"""Ты персональный AI-тренер. Отвечай строго на русском языке. {name_part}
Правила оформления текста:
- Никаких английских слов, символов или иероглифов
- Никаких символов * или ** в тексте
- Заголовки пиши так: "Оценка состояния:", "Тренировка на сегодня:", "Важно сегодня:"
- После каждого заголовка сразу текст на новой строке
- Упражнения перечисляй через дефис
- НЕ упоминай отсутствие данных с часов, пульса или HRV
- Строй план ТОЛЬКО на основе субъективной оценки и стажа

Данные пользователя:
- Субъективная оценка сегодня: {data_in.wellness_description}
- Готовность по ощущениям: {data_in.readiness_score}%
- Цель: {data_in.goal}
- Вид спорта: {data_in.sport}
- Стаж в спорте: {years_str}
- Уровень атлета: {athlete_level}
- Возраст: {data_in.age} лет
- Вес: {data_in.weight:.1f} кг
- Рост: {data_in.height} см
{cycle_info}
Составь КРАТКИЙ ТЕЗИСНЫЙ план тренировки под уровень атлета "{athlete_level}".

Оценка состояния:
(2-3 предложения о состоянии на основе субъективной оценки)

Тренировка на сегодня:
(тезисно: 3-5 упражнений подходящих для уровня "{athlete_level}", без весов и подходов)

Важно сегодня:
(2-3 тезиса по питанию и восстановлению)

Если самочувствие плохое — предложи отдых или лёгкую активность."""

        # Промпт для пользователей С часами
        else:
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
- Стаж в спорте: {years_str}
- Уровень атлета: {athlete_level}
- Возраст: {data_in.age} лет
- Вес: {data_in.weight:.1f} кг
- Рост: {data_in.height} см
{cycle_info}{f"- Субъективное самочувствие: {data_in.wellness_description}" if data_in.wellness_description else ""}

Составь КРАТКИЙ ТЕЗИСНЫЙ план тренировки под уровень атлета "{athlete_level}".

Оценка состояния:
(2-3 предложения о состоянии тела на основе пульса, сна, HRV и готовности)

Тренировка на сегодня:
(тезисно: 3-5 упражнений подходящих для уровня "{athlete_level}", без весов и подходов)

Важно сегодня:
(2-3 тезиса по питанию, водному балансу и восстановлению)

Если восстановление плохое — предложи отдых или лёгкую активность."""

    # ПОДРОБНЫЙ ПЛАН
    else:

        # Подробный план для пользователей БЕЗ часов
        if not has_wearable_data and has_wellness_data:
            prompt = f"""Ты персональный AI-тренер. Отвечай строго на русском языке. {name_part}
Правила оформления текста:
- Никаких английских слов, символов или иероглифов
- Никаких символов * или ** в тексте
- Заголовки пиши так: "Тренировка на сегодня:", "Важно сегодня:"
- После каждого заголовка сразу текст на новой строке
- Упражнения перечисляй через дефис: "- Название: подходы и повторения"
- НЕ упоминай отсутствие данных с часов, пульса или HRV

Данные пользователя:
- Субъективная оценка сегодня: {data_in.wellness_description}
- Готовность по ощущениям: {data_in.readiness_score}%
- Цель: {data_in.goal}
- Вид спорта: {data_in.sport}
- Стаж в спорте: {years_str}
- Уровень атлета: {athlete_level}
- Возраст: {data_in.age} лет
- Вес: {data_in.weight:.1f} кг
- Рост: {data_in.height} см
{cycle_info}
Составь ПОДРОБНЫЙ план тренировки строго под уровень "{athlete_level}".
Оценку состояния НЕ пиши — она уже показана пользователю.

Тренировка на сегодня:
- Разминка: конкретные упражнения с временем выполнения
- Основные упражнения: название, подходы x повторения, вес в кг рассчитанный под уровень "{athlete_level}" и вес тела {data_in.weight:.1f} кг, отдых между подходами в секундах, техническая подсказка по технике
- Заминка: растяжка с временем удержания каждой позиции

Важно сегодня:
- Питание до тренировки: продукты, граммовки, время приёма
- Питание после тренировки: продукты, граммовки белка и углеводов, время приёма
- Восстановление: сон, растяжка, водный баланс с количеством мл
- Персональный совет под уровень атлета

Если самочувствие плохое — предложи лёгкую тренировку или отдых."""

        # Подробный план для пользователей С часами
        else:
            prompt = f"""Ты персональный AI-тренер. Отвечай строго на русском языке. {name_part}
Правила оформления текста:
- Никаких английских слов, символов или иероглифов
- Никаких символов * или ** в тексте
- Заголовки пиши так: "Тренировка на сегодня:", "Важно сегодня:"
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
- Стаж в спорте: {years_str}
- Уровень атлета: {athlete_level}
- Возраст: {data_in.age} лет
- Вес: {data_in.weight:.1f} кг
- Рост: {data_in.height} см
{cycle_info}- Имя: {data_in.name if data_in.name else "не указано"}
{cycle_info}{f"- Субъективное самочувствие: {data_in.wellness_description}" if data_in.wellness_description else ""}

Составь ПОДРОБНЫЙ план строго под уровень "{athlete_level}".
Оценку состояния НЕ пиши — она уже показана пользователю.

Тренировка на сегодня:
- Разминка: конкретные упражнения с временем выполнения
- Основные упражнения: название, подходы x повторения, вес в кг рассчитанный под уровень "{athlete_level}" и вес тела {data_in.weight:.1f} кг, отдых между подходами в секундах, техническая подсказка
- Заминка: растяжка с временем удержания каждой позиции

Важно сегодня:
- Питание до тренировки: продукты, граммовки, время приёма
- Питание после тренировки: продукты, граммовки белка и углеводов, время приёма
- Восстановление: сон, растяжка, водный баланс с количеством мл
- Персональный совет исходя из показателей восстановления и уровня атлета

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