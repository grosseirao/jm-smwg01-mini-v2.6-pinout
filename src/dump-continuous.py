import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'work'
OUT = ROOT / 'outputs'
TOOLS = WORK / 'wbrg1-tools' / 'wbrg1'
SIZE = 0x800000
STATUS = WORK / 'dump-continuous-status.json'
LOG = OUT / 'dump-WBRG1-processo.txt'
candidate = WORK / 'WBRG1-full-candidate.bin'
partial = WORK / 'WBRG1-current-attempt.bin'
runner = TOOLS / 'rtltool-read-timeout.py'
source = (TOOLS / 'rtltool.py').read_text(encoding='utf-8-sig')
# Allow slow USB scheduling; retain the upstream read command and validation.
runner.write_text(source.replace('timeout=0.2', 'timeout=2.0'), encoding='utf-8')
env = dict(os.environ)
env['PYTHONPATH'] = str(WORK / 'python-deps')
env['PYTHONUNBUFFERED'] = '1'

def say(message):
    line = f'[{datetime.now():%H:%M:%S}] {message}'
    print(line, flush=True)
    with LOG.open('a', encoding='utf-8') as f:
        f.write(line + '\n')

def status(state, **fields):
    obj = dict(state=state, pid=os.getpid(), updated=datetime.now().astimezone().isoformat(), **fields)
    temp = STATUS.with_suffix('.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(STATUS)

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    OUT.mkdir(exist_ok=True)
    say('BACKUP WBRG1: COM12; leitura de 8 MB; nenhuma gravacao de flash.')
    say('Tentativas continuas ate duas leituras completas e identicas. Ctrl+C interrompe.')
    say('Se necessario: desligue USB-C da placa, resistor 1k entre P1-1/P1-2,')
    say('ligue USB-C, aguarde 1 segundo e retire o resistor. Mantenha FT232RL conectado.')
    say('Fios: GND->P1-1; RXD->P1-2; TXD->P1-3. VCC livre.')
    first_hash = digest(candidate) if candidate.exists() and candidate.stat().st_size == SIZE else None
    if first_hash:
        say('Primeira leitura completa preservada. Retomando a leitura de confirmacao desde o inicio.')
    attempt = 0
    while True:
        attempt += 1
        baud = 115200
        status('reading', attempt=attempt, baud=baud, expected_bytes=SIZE, verified_reads=bool(first_hash))
        say(f'Tentativa {attempt}, {baud} baud. Uma leitura lenta pode levar 15 minutos.')
        if partial.exists():
            partial.unlink()
        command = [sys.executable, '-u', str(runner), '-p', 'COM12', '-b', str(baud),
                   'rf', '0', hex(SIZE), str(partial)]
        child = subprocess.Popen(command, cwd=TOOLS, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, errors='replace')
        try:
            for line in child.stdout:
                say(line.rstrip())
            rc = child.wait()
        except BaseException:
            child.terminate()
            child.wait(timeout=10)
            raise
        count = partial.stat().st_size if partial.exists() else 0
        if rc == 0 and count == SIZE:
            current_hash = digest(partial)
            if first_hash == current_hash:
                target = OUT / 'WBRG1-firmware-original-8MB.bin'
                shutil.copyfile(partial, target)
                hashfile = OUT / 'WBRG1-firmware-original-8MB.sha256'
                hashfile.write_text(f'{current_hash}  {target.name}\n', encoding='ascii')
                status('completed', attempt=attempt, bytes=SIZE, sha256=current_hash,
                       matching_reads=2, output=str(target))
                say('CONCLUIDO: duas leituras completas identicas; backup validado.')
                say(f'Arquivo: {target}')
                say(f'SHA256: {current_hash}')
                return
            if first_hash:
                say('As duas leituras completas diferem. Vou obter outra para confirmar.')
            shutil.copyfile(partial, candidate)
            first_hash = current_hash
            say(f'Leitura completa recebida ({SIZE} bytes). Iniciando confirmacao.')
        else:
            say(f'Leitura incompleta: {count}/{SIZE} bytes, retorno {rc}. Ainda nao e backup valido.')
            say('Nova tentativa em 5 segundos. Se persistir, refaca a entrada no modo de programacao.')
            status('retrying', attempt=attempt, bytes=count, expected_bytes=SIZE)
            time.sleep(5)

try:
    main()
except KeyboardInterrupt:
    status('interrupted')
    say('Interrompido pelo usuario; dados parciais preservados em work.')
except Exception as exc:
    status('failed', error=str(exc))
    say(f'Erro no controlador de captura: {exc}')
    raise
