from livestt.pipeline.text_processor import TextProcessor


def test_commit_final_capitalizes_and_punctuates():
    tp = TextProcessor()
    tp.commit_final("привет всем")
    assert tp.committed_text == "Привет всем."


def test_commit_final_keeps_existing_punctuation():
    tp = TextProcessor()
    tp.commit_final("как дела?")
    assert tp.committed_text == "Как дела?"


def test_multiple_utterances_accumulate_with_single_space():
    tp = TextProcessor()
    tp.commit_final("привет всем")
    tp.commit_final("сегодня мы обсудим новый проект")
    assert tp.committed_text == "Привет всем. Сегодня мы обсудим новый проект."


def test_full_text_never_duplicates_partial_on_repeated_calls():
    tp = TextProcessor()
    tp.commit_final("первое предложение")
    # Simulate partial updates growing word by word, as STT would emit mid-utterance.
    r1 = tp.full_text("привет")
    r2 = tp.full_text("привет всем")
    r3 = tp.full_text("привет всем сегодня")
    assert r1 == "Первое предложение. привет"
    assert r2 == "Первое предложение. привет всем"
    assert r3 == "Первое предложение. привет всем сегодня"
    # committed text itself must be untouched by partial calls
    assert tp.committed_text == "Первое предложение."


def test_full_text_with_no_partial_returns_committed_only():
    tp = TextProcessor()
    tp.commit_final("готово")
    assert tp.full_text("") == "Готово."
    assert tp.full_text() == "Готово."


def test_empty_final_does_not_corrupt_state():
    tp = TextProcessor()
    tp.commit_final("   ")
    assert tp.committed_text == ""


def test_reset_clears_committed_text():
    tp = TextProcessor()
    tp.commit_final("что-то")
    tp.reset()
    assert tp.committed_text == ""


def test_whitespace_is_collapsed():
    tp = TextProcessor()
    tp.commit_final("привет    всем   \n как   дела")
    assert tp.committed_text == "Привет всем как дела."
