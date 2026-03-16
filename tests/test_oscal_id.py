from ocbc.generate import oscal_id_to_control_id


def test_base_control():
    assert oscal_id_to_control_id("ac-2") == "AC-2"


def test_enhancement():
    assert oscal_id_to_control_id("ac-2.1") == "AC-2(1)"


def test_enhancement_double_digit():
    assert oscal_id_to_control_id("ia-2.12") == "IA-2(12)"


def test_zero_padded_enhancement():
    assert oscal_id_to_control_id("ac-2.01") == "AC-2(1)"


def test_three_letter_family():
    assert oscal_id_to_control_id("pii-3") == "PII-3"
    assert oscal_id_to_control_id("pii-3.2") == "PII-3(2)"
