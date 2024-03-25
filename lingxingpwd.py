from Crypto.Cipher import AES
import base64

"""
领星密码加密解密，领星的前端密码传到后端是加密的，所以需要模拟加密解密的过程
"""


def encrypt_password(password, key_string):
    # Convert key string to bytes, then create AES key
    key_bytes = key_string.encode('utf-8')
    secret_key = AES.new(key_bytes, AES.MODE_ECB)

    # Pad password if necessary to fit block size
    def pad(s): return s + (AES.block_size - len(s) % AES.block_size) * chr(AES.block_size - len(s) % AES.block_size)

    padded_password = pad(password)

    # Encrypt password
    encrypted_bytes = secret_key.encrypt(padded_password.encode('utf-8'))

    # Encode encrypted bytes with Base64
    encoded_encrypted_password = base64.b64encode(encrypted_bytes).decode('utf-8')

    return encoded_encrypted_password


def decrypt_password(encoded_encrypted_password, key_string):
    # Convert key string to bytes, then create AES key
    key_bytes = key_string.encode('utf-8')
    secret_key = AES.new(key_bytes, AES.MODE_ECB)

    # Decode encrypted password with Base64
    encrypted_bytes = base64.b64decode(encoded_encrypted_password)

    # Decrypt password
    decrypted_bytes = secret_key.decrypt(encrypted_bytes)

    # Unpad decrypted password
    def unpad(s): return s[:-ord(s[len(s) - 1:])]

    decrypted_password = unpad(decrypted_bytes.decode('utf-8'))

    return decrypted_password


# Example usage
if __name__ == "__main__":
    print(encrypt_password("abcdedf", "fxSyzm1sGEIP7xrl"))
    print(decrypt_password("14aSJlu++f130PseTCYQ3w==", "fxSyzm1sGEIP7xrl"))
