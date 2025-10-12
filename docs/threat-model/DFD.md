## Диаграмма (Mermaid)
```mermaid
flowchart LR
  U[User (Browser/Mobile)] -->|F1: HTTPS Auth (JWT)| BFF[Web/API]

  subgraph Edge[Trust Boundary: Edge / Public Network]
    BFF -->|F2: mTLS proxied API| SVC[FastAPI Service<br/>AuthN/AuthZ + Validation]
  end

  subgraph Core[Trust Boundary: Core / App + Data]
    SVC -->|F3: TCP/PSQL CRUD| DB[(Postgres/SQLite<br/>users, objectives, key_results)]
    SVC -->|F4: TCP/PSQL Aggregations| DB
    SVC -->|F5: Audit events| AUD[(Audit Log store)]
  end
```

## Список потоков
| ID | Откуда → Куда | Канал/Протокол | Данные/PII | Комментарий |
|----|---------------|-----------------|-----------|-------------|
| F1 | U → BFF       | HTTPS           | creds     |      Логин/получение/передача JWT; все защищённые вызовы идут с Authorization: Bearer.       |
| F2 | BFF → SVC     | mTLS            | session   |     Реверс-прокси/шлюз до FastAPI; лимитирование/логирование на периметре (если есть).        |
| F3 | SVC → DB      | TCP   (PSQL/SQLite)            | PII (имя пользователя), цели и KR        |     CRUD /objectives, /key-results, create_user, чтение.        |
| F4 | SVC → DB      | TCP   (PSQL)            | агрегированные данные       |     GET /stats — агрегации по Objective/KR.       |
| F5 | SVC → AUD     | TCP/append          | метаданные событий       |    Аудит login/CRUD/deny (non-repudiation).      |
