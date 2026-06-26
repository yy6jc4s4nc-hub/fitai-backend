# Деплой FitAI Backend на Railway

## 1. PostgreSQL

1. Откройте проект на [railway.app](https://railway.app)
2. **+ New** → **Database** → **PostgreSQL**
3. Откройте сервис PostgreSQL → **Variables** → скопируйте `DATABASE_URL`
4. В сервисе **fitai-backend** → **Variables** → **Add Variable**:
   - Name: `DATABASE_URL`
   - Value: вставьте URL из PostgreSQL (или Reference → PostgreSQL → DATABASE_URL)

## 2. JWT

В сервисе **fitai-backend** → **Variables**:

```
JWT_SECRET_KEY=<случайная длинная строка, 32+ символов>
```

Сгенерировать в терминале:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 3. AI (уже должно быть)

```
OPENROUTER_API_KEY=<ваш ключ OpenRouter>
```

## 4. Деплой

После push в `main` Railway пересоберёт сервис автоматически.

Проверка:

```bash
curl https://fitai-backend-production-c38e.up.railway.app/
curl -X POST https://fitai-backend-production-c38e.up.railway.app/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"123456","name":"Test"}'
```

Ожидается: `200` и JSON с `access_token`.
