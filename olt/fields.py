"""
Campo de model que criptografa o valor em repouso (Fernet/AES). Usado só
pra senha de OLT (olt.models.Olt.password) - diferente de credenciais no
.env, um model fica dentro do banco e de qualquer backup dele.
"""
import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models

logger = logging.getLogger('olt.security')

_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is not None:
        return _fernet

    key = os.getenv('OLT_CREDENTIALS_KEY')
    if key:
        _fernet = Fernet(key.encode('utf-8'))
    else:
        # Fallback pra dev local: deriva do SECRET_KEY. Rotacionar o
        # SECRET_KEY sem ter setado OLT_CREDENTIALS_KEY invalida as senhas
        # de OLT já salvas - por isso o aviso.
        logger.warning(
            'OLT_CREDENTIALS_KEY não definido - usando chave derivada do SECRET_KEY. '
            'Defina OLT_CREDENTIALS_KEY em produção (Fernet.generate_key()) para não '
            'perder as senhas de OLT salvas caso o SECRET_KEY seja rotacionado.'
        )
        derived = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
        _fernet = Fernet(base64.urlsafe_b64encode(derived))
    return _fernet


class EncryptedCharField(models.CharField):
    """CharField criptografado com Fernet. O valor em Python é sempre o texto puro."""

    def get_prep_value(self, value):
        if not value:
            return value
        return _get_fernet().encrypt(value.encode('utf-8')).decode('utf-8')

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        try:
            return _get_fernet().decrypt(value.encode('utf-8')).decode('utf-8')
        except InvalidToken:
            logger.error('Falha ao descriptografar campo - chave OLT_CREDENTIALS_KEY incorreta ou valor legado não criptografado')
            return value
