from evals.text import contains_term, flesch_kincaid_grade, sentence_count, syllables, word_count


def test_sentence_and_word_counts() -> None:
    assert sentence_count("One. Two! Three?") == 3
    assert sentence_count("No end mark") == 1
    assert sentence_count("") == 0
    assert word_count("a b  c") == 3


def test_syllables_heuristic() -> None:
    assert [syllables(w) for w in ("tea", "worried", "table", "make")] == [1, 2, 2, 1]


def test_flesch_kincaid_simple_vs_dense() -> None:
    assert flesch_kincaid_grade("I am here. Want some tea?") < 3
    dense = "Considerable apprehension notwithstanding, institutional deliberation continues."
    assert flesch_kincaid_grade(dense) > 15


def test_contains_term_is_whole_word() -> None:
    assert contains_term("Take the dose now", "dose")
    assert not contains_term("Come closer", "dose")
    assert contains_term("Any side  effects?", "side effects")
