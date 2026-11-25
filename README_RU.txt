ПАТЧ: БЕЗОПАСНОСТЬ УДАЛЕНИЯ ФОТО И ВИДЕО

Что делает патч
- Сохраняет существующие API-маршруты и бизнес-логику аренды.
- Сериализует создание, прикрепление, удаление и перестановку фото/видео через транзакционные PostgreSQL advisory locks.
- Делает удаление парка, постановку его медиа в очередь и каскадное удаление одной транзакцией.
- Защищает фоновый worker от параллельного удаления одного URL несколькими экземплярами backend.
- Не меняет схему БД и не требует повторного применения миграции 006.

Файлы в архиве имеют пути относительно корня проекта:
1) backend/app/services/media_locks.py (НОВЫЙ)
2) backend/app/services/bikes.py (ЗАМЕНИТЬ)
3) backend/app/services/media_cleanup.py (ЗАМЕНИТЬ)
4) backend/app/routers/super_admin.py (ЗАМЕНИТЬ)

Важно
- Не заменяйте .env, базу данных, frontend или другие файлы.
- Не запускайте миграцию 006 повторно: этот патч использует уже созданную media_cleanup_queue.
- Сначала примените файлы локально и выполните проверки ниже. До успешных проверок не коммитьте, не пушьте и не деплойте.

Проверка в PowerShell из корня проекта:

.\backend\.venv\Scripts\python.exe -m compileall -q .\backend\app
if ($LASTEXITCODE -ne 0) { throw 'Python compile failed' }

.\backend\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from app.main import app; print('IMPORT OK:', app.title)"
if ($LASTEXITCODE -ne 0) { throw 'Backend import failed' }

git diff --check

Затем отдельно проверьте frontend:
cd .\frontend
npm run build

Если любая проверка завершится ошибкой — остановитесь и пришлите полный вывод.
