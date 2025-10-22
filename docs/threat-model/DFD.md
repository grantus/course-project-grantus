## Диаграмма (Mermaid)
```mermaid
flowchart LR
    %% --- Trust boundaries ---
    subgraph Edge
        U[Пользователь]
    end

    subgraph Core
        APP[(FastAPI App)]
        DB[(Database)]
        AUD[(Audit Log Storage)]
    end

    subgraph CI
        CI[(GitHub Actions<br/>pip-audit + SBOM)]
    end

    %% --- Data flows ---
    U -->|F1: AuthN/AuthZ (JWT)| APP
    APP -->|F2: CRUD (objectives, key-results)| DB
    APP -->|F3: Errors (RFC7807)| U
    APP -->|F4: Rate limit / validation feedback| U
    APP -->|F5: Audit events (CRUD/Auth, non-repudiation)| AUD
    Dev[Developer] -->|F6: CI/CD supply chain (source, deps)| CI
```

## Список потоков
| ID | Откуда → Куда | Канал/Протокол | Данные/PII | Комментарий |
|----|---------------|-----------------|-----------|-------------|
| F1 | U → BFF       | HTTPS           | creds     |      Логин/получение/передача JWT; все защищённые вызовы идут с Authorization: Bearer.       |
| F2 | BFF → SVC     | mTLS            | session   |     Реверс-прокси/шлюз до FastAPI; лимитирование/логирование на периметре (если есть).        |
| F3 | SVC → DB      | TCP   (PSQL/SQLite)            | PII (имя пользователя), цели и KR        |     CRUD /objectives, /key-results, create_user, чтение.        |
| F4 | SVC → DB      | TCP   (PSQL)            | агрегированные данные       |     GET /stats — агрегации по Objective/KR.       |
| F5 | SVC → AUD     | TCP/append          | метаданные событий       |    Аудит login/CRUD/deny (non-repudiation).      |
| F6 | Developer → CI/CD (GitHub Actions) | HTTPS            | исходный код, зависимости | Проверка `pip-audit`, формирование SBOM, контроль supply chain. |
