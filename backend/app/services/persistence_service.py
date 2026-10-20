from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UserResourceNotFoundError
from app.db.models import AnswerRecordRow, QuizSession, ReportRow, User
from app.models.quiz import Quiz
from app.models.report import Report, ReportRequest


class PersistenceService:
    async def save_quiz(
        self,
        session: AsyncSession,
        user: User,
        quiz: Quiz,
    ) -> None:
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

    async def save_report(
        self,
        session: AsyncSession,
        user: User,
        request: ReportRequest,
        report: Report,
    ) -> None:
        quiz = await session.scalar(
            select(QuizSession)
            .where(
                QuizSession.quiz_id == request.quiz_id,
                QuizSession.user_id == user.id,
            )
            .with_for_update()
        )
        if quiz is None:
            await session.rollback()
            raise UserResourceNotFoundError()

        question_by_id = {question.id: question for question in request.questions}
        records = []
        for record in request.answer_records:
            question = question_by_id[record.question_id]
            record_data = record.model_dump()
            record_data["is_correct"] = set(record.selected_answers) == set(
                question.answer
            )
            records.append(record_data)

        answer_row = await session.scalar(
            select(AnswerRecordRow)
            .where(AnswerRecordRow.quiz_id == request.quiz_id)
            .with_for_update()
        )
        first_completion = answer_row is None
        if answer_row is None:
            answer_row = AnswerRecordRow(
                quiz_id=request.quiz_id,
                user_id=user.id,
                records_json=records,
                total_questions=report.total_questions,
                correct_count=report.correct_count,
                accuracy=Decimal(report.accuracy),
            )
            session.add(answer_row)
        else:
            answer_row.records_json = records
            answer_row.total_questions = report.total_questions
            answer_row.correct_count = report.correct_count
            answer_row.accuracy = Decimal(report.accuracy)

        report_row = await session.scalar(
            select(ReportRow)
            .where(ReportRow.quiz_id == request.quiz_id)
            .with_for_update()
        )
        if report_row is None:
            session.add(
                ReportRow(
                    quiz_id=request.quiz_id,
                    user_id=user.id,
                    report_json=report.model_dump(),
                )
            )
        else:
            report_row.report_json = report.model_dump()

        if first_completion:
            await session.execute(
                update(User)
                .where(User.id == user.id)
                .values(total_xp=User.total_xp + report.xp_reward)
            )
        await session.commit()
