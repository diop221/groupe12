"""Décode le message fictif fourni par le module cryptography/low.php."""
import base64
ciphertext = base64.b64decode('Lg4WGlQZChhSFBYSEB8bBQtPGxdNQSwEHREOAQY=')
key = b'wachtwoord'
print(bytes(c ^ key[i % len(key)] for i, c in enumerate(ciphertext)).decode())
