from harness.crypto import encrypt_value, decrypt_value


def test_encrypt_decrypt_roundtrip() -> None:
    original = "sk-test-api-key-12345"
    encrypted = encrypt_value(original)
    assert encrypted != original
    assert decrypt_value(encrypted) == original


def test_encrypt_produces_different_output() -> None:
    enc1 = encrypt_value("same")
    enc2 = encrypt_value("same")
    assert enc1 != enc2


def test_decrypt_invalid_returns_none() -> None:
    assert decrypt_value("not-valid") is None
