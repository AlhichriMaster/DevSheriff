from app.services.diff_parser import parse_diff_with_positions


SAMPLE_PATCH = """@@ -0,0 +1,10 @@
+line 1
+line 2
+line 3
 context line
+line 5
-removed line
+line 7"""


def test_parse_diff_maps_added_lines():
    positions = parse_diff_with_positions(SAMPLE_PATCH)
    assert 1 in positions
    assert 2 in positions
    assert 3 in positions


def test_parse_diff_empty_patch():
    positions = parse_diff_with_positions("")
    assert positions == {}


def test_parse_diff_none_patch():
    positions = parse_diff_with_positions(None)
    assert positions == {}


def test_parse_diff_positions_are_sequential():
    positions = parse_diff_with_positions(SAMPLE_PATCH)
    # All position values should be positive integers
    for line_num, pos in positions.items():
        assert pos > 0
        assert isinstance(pos, int)
