from app.services.scoring_service import calculate_score


def test_score_uses_answer_keys_and_ignores_client_correctness(report_request):
    report = calculate_score(report_request)

    assert report.accuracy == 60
    assert report.correct_count == 3
    assert report.total_questions == 5
    assert report.xp_reward == 70
    assert report.coin_reward == 9
    assert report.mastered_points == ["Basics", "Review"]
    assert report.weak_points == ["Applications"]
    assert report.max_streak == 2


def test_partial_multiple_answer_awards_half_xp_but_no_coin(report_request):
    report_request.answer_records[3].selected_answers = ["A"]
    report = calculate_score(report_request)

    assert report.accuracy == 60
    assert report.xp_reward == 70
    assert report.coin_reward == 9
    assert report.max_streak == 2


def test_wrong_selection_breaks_streak_and_awards_nothing(report_request):
    report_request.answer_records[1].selected_answers = ["B"]
    report = calculate_score(report_request)

    assert report.max_streak == 1
    assert report.xp_reward == 50
    assert report.coin_reward == 6


def test_answers_are_order_independent(report_request):
    report_request.answer_records[3].selected_answers = ["C", "A"]

    report = calculate_score(report_request)

    assert report.accuracy == 80
    assert report.xp_reward == 80
    assert report.coin_reward == 12
