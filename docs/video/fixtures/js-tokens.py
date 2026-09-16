"""Valeurs du défi JavaScript de la version DVWA figée ; aucun appel réseau."""
import codecs
import hashlib
phrase = 'success'
print('low:', hashlib.md5(codecs.encode(phrase, 'rot_13').encode()).hexdigest())
print('medium:', ('XX' + phrase + 'XX')[::-1])
first = hashlib.sha256(('XX' + phrase[::-1]).encode()).hexdigest()
print('high:', hashlib.sha256((first + 'ZZ').encode()).hexdigest())
