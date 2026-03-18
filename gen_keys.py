# gen_keys.py — chạy 1 lần, không đưa vào repo
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

private_key = rsa.generate_private_key(
    public_exponent=65537, key_size=2048
)

# → Lưu lên server, không bao giờ đưa vào .exe
with open("private_key.pem", "wb") as f:
    f.write(private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption()
    ))

# → Nhúng cứng vào client code
with open("public_key.pem", "wb") as f:
    f.write(private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo
    ))