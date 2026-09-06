import pytest
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token

def test_password_hashing():
    raw_pw = "MySecretPassword123"
    hashed = get_password_hash(raw_pw)
    
    assert hashed != raw_pw
    assert verify_password(raw_pw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_token_encode_decode():
    subject = "user-uuid-12345"
    token = create_access_token(subject=subject)
    
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == subject

def test_jwt_invalid_token():
    assert decode_access_token("invalid.jwt.token") is None
