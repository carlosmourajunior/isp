"""
Status do contrato do IXC (cliente_contrato.status / status_internet) em
linguagem da vistoria. Os códigos crus ficam em ClienteFibraIxc; os rótulos
abaixo seguem o padrão do IXC - se aparecer um código fora da lista, ele é
mostrado como veio.
"""

STATUS_CONTRATO = {
    'A': 'Ativo',
    'I': 'Inativo',
    'P': 'Pré-contrato',
    'N': 'Negativado',
    'D': 'Desistiu',
}

STATUS_INTERNET = {
    'A': 'Ativo',
    'D': 'Desativado',
    'CM': 'Bloqueio manual',
    'CA': 'Bloqueio automático',
    'FA': 'Financeiro em atraso',
    'AA': 'Aguardando assinatura',
}

BLOQUEIOS = {'CM', 'CA', 'FA'}


def situacao_contrato(cliente):
    """-> (codigo, rotulo). codigo: ativo | bloqueado | inativo | sem_contrato.

    'inativo' e 'sem_contrato' com a ONT offline = candidato a porta fantasma.
    """
    if cliente is None or not cliente.vinculado:
        return 'sem_contrato', 'Sem contrato no IXC'
    contrato = (cliente.status_contrato or '').upper()
    internet = (cliente.status_internet or '').upper()
    if contrato and contrato != 'A':
        return 'inativo', f"Contrato {STATUS_CONTRATO.get(contrato, contrato)}"
    if internet == 'D':
        return 'inativo', "Internet desativada"
    if internet in BLOQUEIOS:
        return 'bloqueado', STATUS_INTERNET[internet]
    if not contrato:
        return 'ativo', "Ativo (status não informado)"
    return 'ativo', "Ativo"
