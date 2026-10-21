# Related work

*Заготовка для недели 1 ([план](../plans/week-01.md), день 1). Первые две колонки заполнены по design-doc §4. Остальные заполняются при чтении.*

## Системы и бенчмарки

| Работа | Задача | Данные / бенчмарк | Метод | Метрики | Что берём | Ограничение |
|---|---|---|---|---|---|---|
| [STORM](https://arxiv.org/abs/2402.14207) (NAACL 2024) | Статья в стиле Википедии по теме | FreshWiki | Перспективы + диалоги writer↔expert + outline | | Перспективы, диалоги, outline-first. Baseline B3 | |
| [Co-STORM](https://arxiv.org/abs/2408.15232) (EMNLP 2024) | Совместный поиск информации с человеком | WildSeek | Эксперты + модератор + mind map | | Модератор → Gap Critic; mind map → карта доказательств | |
| [OmniThink](https://arxiv.org/abs/2501.09751) (2025) | Генерация длинных статей | | Итеративное расширение + рефлексия | | | |
| [OpenScholar](https://arxiv.org/abs/2411.14199) (2024) | Синтез научной литературы | ScholarQABench | RAG + self-feedback | | ScholarQABench, метрики цитирования | |
| [PaperQA2](https://arxiv.org/abs/2409.13740) (2024) | QA и обзоры по литературе, поиск противоречий | LitQA2 | Агент: поиск → сбор доказательств → ответ | | LitQA2 (abstention). Baseline B5 | |
| [Ai2 Scholar QA](https://arxiv.org/abs/2504.10861) (2025) | Научный QA с атрибуцией | ScholarQA-CS | Snippet search + кластеризация цитат | | Snippet search S2 | |
| [PaSa](https://arxiv.org/abs/2501.10120) (2025) | Поиск статей | RealScholarQuery | Агент поиска + RL | | Snowballing, RealScholarQuery | |
| [CRAG](https://arxiv.org/abs/2401.15884) (2024) | Robust RAG | | Оценка retrieval → корректирующее действие | | Правила контроллера | |
| [Self-RAG](https://arxiv.org/abs/2310.11511) (2023) | Адаптивный RAG | | Reflection-токены | | | |
| [SciFact](https://arxiv.org/abs/2004.14974) (EMNLP 2020) | Проверка научных утверждений | SciFact | | | Данные для verifier | |
| [LitSearch](https://arxiv.org/abs/2407.18940) (2024) | Поиск научных статей | 597 запросов ML/NLP | | Recall@k | Трек A | |
| [QASPER](https://arxiv.org/abs/2105.03011) (NAACL 2021) | QA по полному тексту статьи | 5 049 вопросов, NLP | | Answer F1, Evidence F1 | Трек C | |
| [CiteME](https://arxiv.org/abs/2407.12861) (2024) | Атрибуция цитат | Отрывки из ML-статей | CiteAgent | Accuracy | Возможный доп. трек | |
| [DeepResearch Bench](https://arxiv.org/abs/2506.11763) (2025) | Оценка deep research агентов | 100 задач PhD-уровня | | Качество отчёта, точность цитат | Идеи метрик | |

## Проверка новизны

*Заполнить на неделе 1: поиск работ 2025–2026 гг., которые уже делают «STORM + проверка утверждений + ablations при равном бюджете».*

| Запрос | Где искали | Найдено | Насколько близко к нам |
|---|---|---|---|
| `claim-level verification long-form scientific synthesis` | | | |
| `citation faithfulness deep research agents` | | | |
| `STORM scientific literature` | | | |
| `attribution evaluation long-form report` | | | |

## Позиционирование

*Один абзац по итогам проверки новизны: в чём вклад проекта относительно найденного.*
