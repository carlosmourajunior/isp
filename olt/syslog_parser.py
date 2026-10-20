"""
Parsers dos alarmes de ONT da OLT Nokia (ISAM 7360, release 6.2).

Nomes de alarme confirmados no equipamento (`show alarm log ont-ploam`):
ont-ploam-loss-sig, ont-ploam-dying-gasp, ont-ploam-sig-fail,
ont-ploam-inactive, ont-ploam-rdi, ont-ploam-loss-ack, ...

O formato da mensagem de SYSLOG ainda não foi capturado. Por isso
parse_ont_alarm é tolerante: procura o caminho da ONT e o nome do alarme
em qualquer lugar da linha. A mensagem crua é sempre guardada em
OltSyslogMessage, então dá pra reprocessar quando o formato real chegar.
"""
import re

# 1/1/1/14/90 -> pon 1/1/1/14, posição 90
ONT_PATH_RE = re.compile(r'\b(\d+/\d+/\d+/\d+)/(\d+)\b')
ALARM_TYPE_RE = re.compile(r'\bont-[a-z]+(?:-[a-z]+)*\b', re.IGNORECASE)

# loss-sig é o que interessa para CTO: corte de fibra/caixa derruba todos
# os clientes dela com LOS ao mesmo tempo. dying-gasp é falta de energia no
# cliente - evento individual, não diz nada sobre a CTO.
LOS_RE = re.compile(r'loss[\s_-]*sig|loss[\s_-]*of[\s_-]*signal|\blosi?\b', re.IGNORECASE)
DYING_GASP_RE = re.compile(r'dying[\s_-]*gasp|\bdgi?\b', re.IGNORECASE)
CLEAR_RE = re.compile(r'\bclear(ed)?\b|\bend(ed)?\b', re.IGNORECASE)

# Flag do `show alarm log ont-ploam` -> tipo de evento.
PLOAM_FLAG_TO_EVENT = {
    'ont-ploam-loss-sig': 'los',
    'ont-ploam-dying-gasp': 'dying_gasp',
}


# Mensagens de comando digitado na CLI (msg-type cli-config-chgs / cli-msgs).
# Um comando como "configure equipment ont interface 1/1/2/8/42" tem o
# caminho da ONT mas não é um alarme - sem esse filtro viraria evento falso.
# Formato real: "<142>Oct 19 17:11:00 VIA01_OURO_FINO cli[334]: isadmin@... : [Parser, 3561] executeCommand, cmdstr: '...'"
CLI_MESSAGE_RE = re.compile(r'\bcli\[\d+\]:|executeCommand|cmdstr:', re.IGNORECASE)


def parse_ont_alarm(raw):
    """Mensagem de syslog crua -> dict do evento, ou None se não for alarme de ONT."""
    if CLI_MESSAGE_RE.search(raw):
        return None

    path = ONT_PATH_RE.search(raw)
    if not path:
        return None

    if LOS_RE.search(raw):
        event_type = 'los'
    elif DYING_GASP_RE.search(raw):
        event_type = 'dying_gasp'
    else:
        event_type = 'other'

    # Fica com o nome mais específico (ont-ploam-loss-sig em vez de ont-ploam).
    alarm_names = ALARM_TYPE_RE.findall(raw)
    alarm_type = max(alarm_names, key=len).lower() if alarm_names else ''
    return {
        'pon': path.group(1),
        'position': int(path.group(2)),
        'event_type': event_type,
        'is_clear': bool(CLEAR_RE.search(raw)),
        'alarm_type': alarm_type,
    }


_PLOAM_INDEX_RE = re.compile(r'index\s*:\s*(\d+)')
_PLOAM_ONT_RE = re.compile(r'\bont\s*:\s*(\d+/\d+/\d+/\d+)/(\d+)')
_PLOAM_FLAG_RE = re.compile(r'(ont-ploam-[a-z-]+)\s*:\s*(yes|no)')


def parse_ploam_log(output):
    """`show alarm log ont-ploam` -> lista de entradas.

    Cada entrada é uma foto dos flags da ONT no momento da mudança:
    {'index', 'pon', 'position', 'active': {flags 'yes'}}. A transição
    (o que ligou/desligou) sai comparando entradas da mesma ONT em ordem
    de index - o log não diz explicitamente qual flag mudou.
    """
    entries = []
    # Cada bloco começa no 'index :'; o texto antes do primeiro index é
    # resto de bloco cortado e é descartado.
    blocks = re.split(r'(?=\bindex\s*:)', output)
    for block in blocks:
        index = _PLOAM_INDEX_RE.search(block)
        ont = _PLOAM_ONT_RE.search(block)
        if not index or not ont:
            continue
        active = {flag for flag, value in _PLOAM_FLAG_RE.findall(block) if value == 'yes'}
        entries.append({
            'index': int(index.group(1)),
            'pon': ont.group(1),
            'position': int(ont.group(2)),
            'active': active,
        })
    return entries


# Cabeçalho RFC 3164 (padrão da OLT): "<142>Oct 19 17:11:00 VIA01_OURO_FINO cli[334]: ..."
SYSLOG_HOSTNAME_RE = re.compile(r'^<\d+>\s*[A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+(\S+)')


def extract_hostname(raw):
    """Hostname da OLT no cabeçalho do syslog, ou '' se não houver cabeçalho."""
    match = SYSLOG_HOSTNAME_RE.match(raw)
    return match.group(1) if match else ''
