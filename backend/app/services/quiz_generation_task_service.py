import logging
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import APIError, UserResourceNotFoundError
from app.db.models import QuizGenerationTaskRow, QuizSession, User
from app.models.quiz import Quiz
from app.models.quiz_task import QuizGenerationTask
from app.models.source_import import GenerateFromSourceRequest
from app.services.quiz_service import QuizService


logger = logging.getLogger(__name__)
TASK_RETENTION_DAYS = 7
ACTIVE_TASK_STATUSES = ("queued", "running")
TERMINAL_TASK_STATUSES = ("completed", "failed")
MAX_TASK_RUNTIME = timedelta(minutes=4)


def task_response(task: QuizGenerationTaskRow) -> QuizGenerationTask:
    return QuizGenerationTask(
        task_id=task.task_id,
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
        quiz=Quiz.model_validate(task.result_json) if task.result_json else None,
        error_message=task.error_message,
    )


async def create_quiz_generation_task(
    session: AsyncSession,
    *,
    task_type: str,
    request_data: dict,
    user_id: int | None,
    server_started_at: datetime,
) -> QuizGenerationTaskRow:
    now = datetime.now()
    await _mark_tasks_before_server_start_failed(session, server_started_at)
    await session.execute(
        delete(QuizGenerationTaskRow).where(
            QuizGenerationTaskRow.status.in_(TERMINAL_TASK_STATUSES),
            QuizGenerationTaskRow.updated_at
            < now - timedelta(days=TASK_RETENTION_DAYS),
        )
    )
    task = QuizGenerationTaskRow(
        task_id=uuid4().hex,
        user_id=user_id,
        task_type=task_type,
        status="queued",
        request_json=request_data,
        created_at=now,
        updated_at=now,
    )
    session.add(task)
    await session.commit()
    return task


async def execute_quiz_generation_task(
    task_id: str,
    session_factory: async_sessionmaker[AsyncSession],
    service: QuizService,
) -> None:
    async with session_factory() as session:
        task = await session.get(QuizGenerationTaskRow, task_id)
        if task is None or task.status != "queued":
            return
        task.status = "running"
        task.updated_at = datetime.now()
        request_data = task.request_json
        task_type = task.task_type
        await session.commit()

    try:
        if task_type == "text":
            quiz = await service.generate(request_data["user_input"])
        elif task_type == "source":
            source_request = GenerateFromSourceRequest.model_validate(request_data)
            quiz = await service.generate_from_source(
                source_type=source_request.source_type,
                title=source_request.title,
                content=source_request.content,
                knowledge_points=source_request.knowledge_points,
            )
        else:
            raise ValueError("unsupported quiz task type")
    except APIError as error:
        await _finish_task(
            task_id,
            session_factory,
            status="failed",
            error_message=error.message,
        )
    except Exception as error:
        logger.error(
            "Quiz generation task failed (%s)",
            type(error).__name__,
        )
        await _finish_task(
            task_id,
            session_factory,
            status="failed",
            error_message="题目生成失败，请稍后重试",
        )
    else:
        await _finish_task(
            task_id,
            session_factory,
            status="completed",
            quiz=quiz,
        )


async def _finish_task(
    task_id: str,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    status: str,
    quiz: Quiz | None = None,
    error_message: str | None = None,
) -> None:
    async with session_factory() as session:
        task = await session.get(QuizGenerationTaskRow, task_id)
        if task is None:
            logger.error("Quiz generation task disappeared before completion")
            return
        if task.status != "running":
            return
        task.status = status
        task.updated_at = datetime.now()
        task.error_message = error_message
        task.result_json = quiz.model_dump(mode="json") if quiz else None

        if quiz is not None and task.user_id is not None:
            user = await session.get(User, task.user_id)
            if user is not None:
                session.add(
                    QuizSession(
                        quiz_id=quiz.quiz_id,
                        user_id=user.id,
                        title=quiz.title,
                        summary=quiz.summary,
                        user_input=quiz.user_input,
                        questions_json=[
                            question.model_dump() for question in quiz.questions
                        ],
                    )
                )
        await session.commit()


async def _mark_tasks_before_server_start_failed(
    session: AsyncSession,
    server_started_at: datetime,
) -> None:
    await session.execute(
        update(QuizGenerationTaskRow)
        .where(
            QuizGenerationTaskRow.status.in_(ACTIVE_TASK_STATUSES),
            QuizGenerationTaskRow.updated_at < server_started_at,
        )
        .values(
            status="failed",
            error_message="服务重启导致任务中断，请重新生成",
            updated_at=datetime.now(),
        )
    )


async def get_quiz_generation_task(
    session: AsyncSession,
    task_id: str,
    user_id: int | None,
    server_started_at: datetime,
) -> QuizGenerationTask:
    task = await session.get(QuizGenerationTaskRow, task_id)
    if task is None or (
        task.user_id is not None and task.user_id != user_id
    ):
        raise UserResourceNotFoundError()
    if task.status in ACTIVE_TASK_STATUSES:
        now = datetime.now()
        if task.updated_at < server_started_at:
            task.status = "failed"
            task.error_message = "服务重启导致任务中断，请重新生成"
            task.updated_at = now
            await session.commit()
        elif now - task.updated_at > MAX_TASK_RUNTIME:
            task.status = "failed"
            task.error_message = "任务处理超时，请重新生成"
            task.updated_at = now
            await session.commit()
    return task_response(task)
