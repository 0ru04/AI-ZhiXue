from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import UserSystemConfigurationError
from app.db.models import User
from app.models.user import (
    LoginResponse,
    QuizHistoryDetail,
    QuizHistoryItem,
    QuizHistoryPage,
    UserProfile,
    UserProfileUpdate,
    UserSummary,
)
from app.db.models import AnswerRecordRow, QuizSession, ReportRow


class UserService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def ensure_login_configured(self) -> None:
        if (
            self.settings.jwt_secret_key is None
            or len(self.settings.jwt_secret_key.get_secret_value()) < 32
        ):
            raise UserSystemConfigurationError("JWT_SECRET_KEY 未配置或长度不足")

    def _create_token(self, user: User) -> str:
        self.ensure_login_configured()
        if self.settings.jwt_secret_key is None:
            raise UserSystemConfigurationError("JWT_SECRET_KEY 未配置")
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user.id),
            "openid": user.openid,
            "iat": now,
            "exp": now + timedelta(days=self.settings.jwt_expiration_days),
        }
        return jwt.encode(
            payload,
            self.settings.jwt_secret_key.get_secret_value(),
            algorithm="HS256",
        )

    @staticmethod
    def _user_summary(user: User) -> UserSummary:
        return UserSummary(
            id=user.id,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            total_xp=user.total_xp,
        )

    async def login(
        self,
        session: AsyncSession,
        openid: str,
    ) -> LoginResponse:
        self.ensure_login_configured()
        user = await session.scalar(select(User).where(User.openid == openid))
        if user is None:
            user = User(openid=openid, nickname="学习者", total_xp=0)
            session.add(user)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                user = await session.scalar(
                    select(User).where(User.openid == openid)
                )
                if user is None:
                    raise
        return LoginResponse(
            token=self._create_token(user),
            user=self._user_summary(user),
        )

    async def get_profile(
        self,
        session: AsyncSession,
        user: User,
    ) -> UserProfile:
        aggregates = await session.execute(
            select(
                func.count(AnswerRecordRow.id),
                func.coalesce(func.sum(AnswerRecordRow.correct_count), 0),
                func.coalesce(func.avg(AnswerRecordRow.accuracy), 0),
            ).where(AnswerRecordRow.user_id == user.id)
        )
        quiz_count, correct_count, average_accuracy = aggregates.one()
        return UserProfile(
            **self._user_summary(user).model_dump(),
            quiz_count=quiz_count,
            correct_count=correct_count,
            average_accuracy=round(float(average_accuracy), 2),
        )

    async def update_profile(
        self,
        session: AsyncSession,
        user: User,
        update: UserProfileUpdate,
    ) -> UserSummary:
        changes = update.model_dump(exclude_unset=True)
        if "nickname" in changes:
            user.nickname = changes["nickname"]
        if "avatar_url" in changes:
            user.avatar_url = (
                str(changes["avatar_url"])
                if changes["avatar_url"] is not None
                else None
            )
        await session.commit()
        await session.refresh(user)
        return self._user_summary(user)

    async def list_quizzes(
        self,
        session: AsyncSession,
        user: User,
        page: int,
        page_size: int,
    ) -> QuizHistoryPage:
        base_query = (
            select(QuizSession, AnswerRecordRow)
            .join(
                AnswerRecordRow,
                AnswerRecordRow.quiz_id == QuizSession.quiz_id,
            )
            .where(QuizSession.user_id == user.id)
        )
        total = await session.scalar(
            select(func.count())
            .select_from(QuizSession)
            .join(
                AnswerRecordRow,
                AnswerRecordRow.quiz_id == QuizSession.quiz_id,
            )
            .where(QuizSession.user_id == user.id)
        )
        rows = (
            await session.execute(
                base_query
                .order_by(QuizSession.created_at.desc(), QuizSession.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        items = [
            QuizHistoryItem(
                quiz_id=quiz.quiz_id,
                title=quiz.title,
                accuracy=float(answer.accuracy),
                question_count=answer.total_questions,
                created_at=quiz.created_at.isoformat(),
            )
            for quiz, answer in rows
        ]
        return QuizHistoryPage(
            items=items,
            total=total or 0,
            page=page,
            page_size=page_size,
        )

    async def get_quiz_detail(
        self,
        session: AsyncSession,
        user: User,
        quiz_id: str,
    ) -> QuizHistoryDetail | None:
        quiz = await session.scalar(
            select(QuizSession).where(
                QuizSession.quiz_id == quiz_id,
                QuizSession.user_id == user.id,
            )
        )
        if quiz is None:
            return None
        answer = await session.scalar(
            select(AnswerRecordRow).where(
                AnswerRecordRow.quiz_id == quiz_id,
                AnswerRecordRow.user_id == user.id,
            )
        )
        report = await session.scalar(
            select(ReportRow).where(
                ReportRow.quiz_id == quiz_id,
                ReportRow.user_id == user.id,
            )
        )
        if answer is None or report is None:
            return None
        return QuizHistoryDetail(
            quiz_id=quiz.quiz_id,
            title=quiz.title,
            summary=quiz.summary,
            user_input=quiz.user_input,
            questions=quiz.questions_json,
            answer_records=answer.records_json,
            report=report.report_json,
            created_at=quiz.created_at.isoformat(),
        )
