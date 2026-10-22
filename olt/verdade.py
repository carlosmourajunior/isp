"""
Quem é a verdade sobre a CTO de um cliente: o IXC ou a vistoria?

Regra: o IXC é a verdade. A vistoria só prevalece enquanto a correção de
campo ainda não subiu para o IXC - isto é, enquanto o IXC continua com o
mesmo valor que tinha quando o cliente foi registrado na vistoria. Se o IXC
mudou depois disso (pelo botão de correção ou direto no IXC), vale o IXC.
"""


def caixa_no_ixc(cliente):
    return (cliente.id_caixa_ftth or '') if cliente else ''


def campo_prevalece(registro, cliente):
    """registro: VistoriaPorta (cliente identificado). cliente: ClienteFibraIxc ou None."""
    if registro.caixa_ixc_no_registro is None:
        # Registro de antes do snapshot existir: sem como saber se o IXC mudou depois.
        return True
    return caixa_no_ixc(cliente) == (registro.caixa_ixc_no_registro or '')


def correcao_pendente(registro, cliente):
    """A vistoria prevalece E o IXC ainda está diferente do que se viu em campo."""
    return campo_prevalece(registro, cliente) and caixa_no_ixc(cliente) != (registro.vistoria.cto.ixc_id or '')
