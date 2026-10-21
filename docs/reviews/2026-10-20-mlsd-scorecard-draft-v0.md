*Reviewed with [ml-system-design-review](https://github.com/ML-SystemDesign/MLSystemDesign/tree/main/skills) · [ML System Design](https://arseny.info/ml_design_book) by Kravchenko and Babushkin*

## ML System Design Scorecard: Agentic Medical Evidence Intelligence (черновик v0)

**Verdict:** approve with concerns (avg 2.33) · design doc, NLP / RAG / agentic workflow, risk: high для медицины → medium после перехода к общей научной литературе
**Critical findings:** 1
**Author verdict:** Валерий и Арсений, скорее всего, назвали бы это WIP на хорошем фундаменте: лестница baseline и risk–coverage уже работают, но главная метрика пока может подтвердить гипотезу просто по построению.

| Dimension | Grade | Why |
|---|---|---|
| Problem framing, goals & antigoals | C+ | Исследовательская проблема («релевантно ≠ подтверждает») и гипотезы чёткие; нет пользователя, текущего workflow и явных antigoals, кроме «не клинический сервис» |
| Cost of mistakes & risk | C- | Отдельные failure modes названы (наблюдательное vs причинное, популяция), но таблицы цены ошибок нет; пропущены: пропуск опровергающих данных, отозванные статьи, prompt injection из текста статей |
| Prior work, build/buy & baselines | B- | Лестница B0–B3 и ablations — сильная часть; нет сравнения с готовыми системами той же задачи (STORM, OpenScholar, PaperQA2, Ai2 ScholarQA) и нет baseline при равном бюджете вычислений |
| Metrics, loss & measurement | C+ | Слоистые метрики, risk–coverage, bootstrap, McNemar; не определено, кто измеряет «неподтверждённость» (риск циркулярности с verifier), нет MDE |
| Data, labels & features | C | Роли датасетов расписаны; корпус «50–200k аннотаций» не привязан к бенчмаркам, по одним аннотациям нельзя «извлечь методы и результаты», нет парсинга и provenance |
| Validation & leakage | C+ | Правильные запреты (не тюнить на test, официальные splits); не учтены утечка «вопрос = заголовок статьи» в PubMedQA при open retrieval и контаминация претрейна бенчмарками 2019–2020 гг. |
| Error analysis | B- | Ручной разбор 50–100 примеров с осмысленными категориями; не привязан к трассам по компонентам |
| Training pipeline & reproducibility | B- | Конфиги, seed, хеши корпусов, MLflow; нет версионирования промптов и record/replay для внешних API и LLM |
| Serving, integration & release | C+ | Для прототипа достаточно (FastAPI, Docker, latency, VRAM, лимиты итераций); нет fallback при сбое поиска или парсинга |
| Monitoring, ownership & maintenance | n/a (stage) | Исследовательский прототип с одним владельцем |
| Modern AI systems | C+ | Ограниченный FSM-контроллер и типизированные контракты — хорошо; слабее всего eval grounding (судья не откалиброван), нет защиты от injection, цитаты не собираются из ID |

**Top fix:** Определить, как измеряется «доля неподтверждённых утверждений»: независимый судья другого семейства моделей, откалиброванный на 200+ размеченных вручную парах (claim, фрагмент); внутренний verifier системы никогда не используется как судья.
**Takeaway:** Метрика «неподтверждённых утверждений» стоит ровно столько, насколько независим судья, который её считает; агентность нужно сравнивать с baseline при равном бюджете вычислений, иначе выигрыш — это просто больше вызовов модели.
