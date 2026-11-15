from common.pen import DEFAULT_PEN_KEY, PEN_ORDER, PENS, get_pen


def test_there_are_six_pens():
    assert len(PENS) == 6
    assert PEN_ORDER == list(PENS.keys())


def test_keys_match_and_names_are_unique():
    for key, pen in PENS.items():
        assert pen.key == key
    assert len({p.name for p in PENS.values()}) == 6


def test_stats_are_sane():
    for pen in PENS.values():
        assert pen.mass > 0
        assert 60 <= pen.length <= 260
        assert 8 <= pen.width <= 60
        assert pen.length > pen.width
        assert 0 <= pen.elasticity <= 1
        assert 0 <= pen.friction <= 1
        assert 0.5 <= pen.power <= 1.5
        assert pen.hp > 0
        assert len(pen.color) == 3


def test_pens_are_not_clones():
    stat_sets = {(p.mass, p.length, p.width, p.elasticity, p.power) for p in PENS.values()}
    assert len(stat_sets) == 6


def test_unknown_key_falls_back_to_default():
    assert get_pen("does_not_exist").key == DEFAULT_PEN_KEY



def test_every_pen_has_real_life_facts():
    from common.pen import PEN_FACTS, get_facts
    assert set(PEN_FACTS) == set(PENS)
    labels = [tuple(label for label, _ in PEN_FACTS[key]) for key in PEN_ORDER]
    assert len(set(labels)) == 1  # same labels for every pen, so the screen lines up
    assert all(value for key in PEN_ORDER for _, value in PEN_FACTS[key])
    assert get_facts("nope") == PEN_FACTS[DEFAULT_PEN_KEY]


def test_old_pencil_key_becomes_the_metal_pen():
    assert get_pen("pencil").key == "metal_pen"

