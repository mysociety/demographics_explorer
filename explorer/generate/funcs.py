
import hashlib

salt = "uxlgfC3JAUFliAzp7kgR"
def md5_hash(v):
    if v:
        return hashlib.md5(salt + v).hexdigest()
    else:
        return ""