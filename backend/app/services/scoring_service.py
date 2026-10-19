from app.models.report import ReportRequest, Score


def calculate_score(request: ReportRequest) -> Score:
    records = {record.question_id: record for record in request.answer_records}
    correct_count = 0
    xp_reward = 0
    coin_reward = 0
    max_streak = 0
    current_streak = 0
    point_totals: dict[str, int] = {}
    point_correct: dict[str, int] = {}

    for question in request.questions:
        record = records[question.id]
        selected = set(record.selected_answers)
        correct_answers = set(question.answer)
        is_correct = selected == correct_answers
        point_totals[question.knowledge_point] = (
            point_totals.get(question.knowledge_point, 0) + 1
        )

        if is_correct:
            correct_count += 1
            xp_reward += 20
            coin_reward += 3
            current_streak += 1
            max_streak = max(max_streak, current_streak)
            point_correct[question.knowledge_point] = (
                point_correct.get(question.knowledge_point, 0) + 1
            )
        else:
            current_streak = 0
            if question.type == "multiple" and selected < correct_answers:
                xp_reward += 10

    total_questions = len(request.questions)
    accuracy = round(correct_count * 100 / total_questions)
    mastered_points = [
        point
        for point, total in point_totals.items()
        if point_correct.get(point, 0) == total
    ]
    weak_points = [
        point
        for point, total in point_totals.items()
        if point_correct.get(point, 0) < total
    ]
    return Score(
        accuracy=accuracy,
        correct_count=correct_count,
        total_questions=total_questions,
        xp_reward=xp_reward,
        coin_reward=coin_reward,
        max_streak=max_streak,
        total_duration_ms=sum(record.duration_ms for record in request.answer_records),
        mastered_points=mastered_points,
        weak_points=weak_points,
    )
