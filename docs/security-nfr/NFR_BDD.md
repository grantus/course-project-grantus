# NFR_BDD.md — Приёмка в формате Gherkin

Feature: Аутентификация обязательна
  Scenario: Доступ без токена отклоняется
    Given запущен сервис и нет заголовка Authorization
    When клиент отправляет POST /objectives c валидным телом
    Then ответ — 401 и тело в формате RFC7807

Feature: Авторизация только для владельца
  Scenario: Пользователь не может читать чужой Objective
    Given существуют user A и user B и Objective objA, принадлежащий user A
    When user B делает GET /objectives/{objA.id}
    Then ответ — 403 и тело в формате RFC7807

Feature: Валидация дедлайна period
  Scenario: Создание Objective с прошлой датой запрещено
    Given текущая дата — сегодня
    When клиент отправляет POST /objectives с period в прошлом
    Then ответ — 422 и описание ошибки без PII в RFC7807

Feature: Rate limiting на запись
  Scenario: Превышение лимита приводит к 429
    Given лимит 100 запросов в минуту на токен
    When один и тот же токен делает >100 POST /key-results за 60 секунд
    Then как минимум один ответ — 429 Too Many Requests
