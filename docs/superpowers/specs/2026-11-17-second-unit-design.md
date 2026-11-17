# Second Unit: продуктовая страница NexusShell

Дата: 17 ноября 2026. Статус: согласовано пользователем для локального черновика.

## Задача и подход

Показать существующую среду агентного видеопроизводства через её процесс,
результаты и накопленные исправления. Основной читатель: организатор отбора
FLUX: In Production, которому нужна понятная ссылка на работу автора.
Страница должна оставаться полезной и после конкурса.

Предлагается самостоятельная английская страница `/second-unit/` с входом
из главной и каталога проектов. Это соответствует запросу на продуктовую
страницу и позволяет объяснить процесс рядом с фильмами. Обычная короткая
карточка проекта не вместит демонстрации; отдельный сайт потребовал бы другой
навигации и отделил бы работу от истории NexusShell. Оба варианта здесь менее
полезны. Подход пока предложен агентом, а не согласован пользователем.

Рабочее название Second Unit выбрано пользователем. Оно не означает, что
проверены домен, товарный знак или исключительные права на название.

## Подача и оформление

Продуктовая страница о производственном процессе для технической и творческой
аудитории. Сохраняем Manrope, темы, цвета и спокойный голос NexusShell. Внутри
страницы используем крупные реальные кадры, листы проверки, подписи версий и
небольшую схему процесса. Параметры: DESIGN_VARIANCE 5, MOTION_INTENSITY 2,
VISUAL_DENSITY 5. Нативный HTML/CSS/JavaScript в существующей сборке Python.

| Сейчас в переданном тексте | Предлагается | Причина |
| --- | --- | --- |
| 14 разделов и длинный перечень возможностей | 7 основных блоков, детали раскрываются по запросу | Страницу можно быстро понять и затем изучить |
| Слоган «Cinema rules in, AI slop out» | Описание задачи системы простыми словами | Не обещать художественное качество каждого результата |
| Четыре крупных счётчика в начале | Результаты и механизм работы перед числами | Для отбора полезнее увидеть работу и решения |
| Полная таблица соответствия одному конкурсу | Небольшой раздел о запланированном FLUX-адаптере | Страница пригодится после конкурса |
| Фоновый видеолуп | Плееры выбранных работ с постерами и явным запуском | Посетитель управляет просмотром и звуком |

## Структура страницы

1. **Введение.** Second Unit, короткое описание и переход к работам. На широком
   экране текст рядом с одним сильным кадром из выбранного фильма. До выбора
   работ не подставляем случайное изображение и не делаем фиктивную кнопку Play.
2. **Selected films.** Две-три реальные работы с длительностью, форматом,
   краткой задачей, использованной частью процесса и подписью аудиоверсии.
   Автор пришлёт свой выбор отдельно. Этот раздел включается после получения
   файлов. Вертикальные работы целиком в кадре; горизонтальные без обрезки.
3. **From brief to delivery.** Шесть этапов: Prepare, Establish, Generate,
   Review, Finish, Carry forward. Посетитель выбирает этап и видит вход,
   получаемый материал, проверку и решение человека. Это объяснение процесса,
   а не имитация запущенного генератора. Без JavaScript читаются все этапы.
4. **What the reviewers inspect.** Компактные строки DP, Editor, Colourist
   с раскрываемыми примерами проверок. Рядом обозначены утверждения человека.
5. **A correction that changed the workflow.** Разбор Lawn Wars: r6, две
   отвергнутые попытки унификации цвета, итоговое правило коррекции только
   выбивающихся планов и просмотра всего монтажа. Без видео сравнения до
   согласования конкретных файлов. Рядом петля: замечание → запись ошибки →
   проверенное исправление → общее правило → следующий проект.
6. **Keeping a run inspectable.** Бюджетные ограничения, история принятых
   дублей, версия монтажного скрипта, контрольные суммы. Короткий пример
   состава производственного пакета, без внутренних путей и идентификаторов.
7. **Current engines / Next: FLUX.** Существующие адаптеры и запланированный
   FLUX-адаптер. Одинаковые эталоны, проверки и бюджет для будущего сравнения.
   Небольшая справка о стадии продукта и ссылка на связь через существующий X.

## Готовый черновик основного английского текста

### Introduction

**Second Unit**

**An agentic film crew, from brief to final cut.**

Plan shots, review takes, assemble the edit, and carry what worked into the
next film. You approve the creative decisions along the way.

Second Unit is a production workflow built around image and video models.
Character masters, scene maps, review checklists, edit scripts and a failure
registry give each generation a place in the film. The director approves the
keyframes and the cut before accepted takes move to delivery.

### From brief to delivery

**Prepare.** Start with the brief, budget and acceptance criteria. Analyse
references for composition, light, colour and rhythm, then turn those
observations into a story and a shot plan.

**Establish.** Approve character and location masters. Record the features
that must remain consistent, the action axis, light direction and prop states.
Each new shot starts from its master.

**Generate.** Build keyframes with a declared camera, subject, action and
change over time. Explore motion in inexpensive drafts. Keep accepted takes
as source files for the final edit and upscale.

**Review.** Inspect contact sheets and details, then watch shots inside the
cut. Separate reviewer agents check framing and physical contact, continuity
and motivation, and colour across the sequence. Human review decides what
is accepted and what needs another pass.

**Finish.** Assemble the edit with versioned scripts. Match colour outliers,
apply the look, and add grain at delivery size. Check the exported file and
keep a no-music version where required.

**Carry forward.** Record rejected takes, the reason, the proposed fix and
whether it worked. Accepted references and A/B preferences become material
for the next review. Proven fixes move into the shared rules.

### Review is part of the workflow

**Cinematography.** Check perspective, light, depth, character features,
contact with the ground, hands and prop scale. A shot can be rejected,
returned for another take, or passed to the director.

**Editing.** Check what motivates an action, whether one shot causes the
next, and whether continuity survives the cut. Track the director's notes
against timecodes.

**Colour.** Match before applying the look. Inspect skin and the full
sequence as well as individual cuts. Numeric comparisons support the
review; the director still decides whether the film looks right.

The models are not fine-tuned on the reference library. Craft knowledge is
recorded as rules, checklists and measured observations used around the models.

### When the numbers passed and the colour did not

Lawn Wars is a comedy about two suburban dads racing ride-on mowers at 7 a.m.
Its colour passes exposed a gap in the review process.

The r6 cut met the local colour-difference targets, yet the sequence drifted
between warm and cool shots. A second pass pulled the whole cut toward one
target. The author rejected it: the image had become cold and the greens
had lost separation. A warmer uniform pass was rejected too.

The final returned to the earlier grade. The lesson became a shared rule:
correct outliers selectively and review the whole sequence as a contact
sheet before chasing a single target. A good measurement still needs a
creative verdict.

### What the next film remembers

Each failure entry keeps the symptom, the proposed correction and its outcome.
Before a new generation, the workflow retrieves relevant fixes. Accepted
shots provide references for regression checks; recorded A/B preferences
help calibrate reviewers. A rule change cites the feedback that caused it.

This learning loop updates the workflow's instructions and review material.
It does not train or update the weights of the generation models.

### Keep the production inspectable

Jobs declare their model, inputs, estimated cost and remaining budget.
The runner checks spending caps and request fingerprints before submission.
Accepted takes retain their source records and checksums; edit and grade
scripts are versioned so the final can be rebuilt from those files.

Vendor safety refusals are recorded as terminal outcomes. That record is
kept separate from quota errors, invalid requests and other API failures.

### Current engines. Next: FLUX.

The current workflow uses Gemini image models, Omni and Veo through model
adapters. Planning, review and post-production sit around that generation layer.

The proposed FLUX integration would add an adapter for character masters
and keyframes, then compare results on the same approved references with
the same reviewers and budget limits. This integration is planned.

## Редакционные ограничения

Материал основан на документации, предоставленной владельцем проекта.
Непроверенные агрегированные показатели не используются как рекламные метрики.
Страница описывает рабочую среду; доступность публичного сервиса не заявлена.
FLUX-адаптер обозначен как запланированный. Отбор на конкурс и партнёрство
с организаторами не заявлены.

Медиаматериалы добавляются после выбора владельцем. Публичная страница не
содержит внутренних путей, производственных идентификаторов или чужих
референсов. Для каждого фильма требуется пригодная для сайта версия с
согласованным звуком. Оригинальные файлы не изменяются.

## Объём реализации после согласования

- Добавить страницу в существующую сборку, метаданные и sitemap.
- Добавить вход из главной и каталога в группе продолжающихся проектов.
- Сохранить существующие проекты, маршруты, темы и управление клавиатурой.
- Публичные тексты и редакционные данные хранить отдельно от разметки.
- Видеоблок включать из явного списка выбранных материалов; без пустых плееров.
- Проверить ширины 320, 768 и 1280 px, обе темы, клавиатуру, ссылки и загрузку
  медиа. Видео с controls, playsinline и preload=none; без автозапуска со звуком.
- Сначала показать черновик. Публикация этой новой страницы — после проверки
  выбранных работ и итогового вида пользователем.
