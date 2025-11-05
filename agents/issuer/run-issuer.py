import subprocess
import shlex
import sys

# Comando exato fornecido por você
command = """
aca-py start \
 --inbound-transport http 0.0.0.0 8000 \
 --outbound-transport ws \
 --outbound-transport http \
 --log-level debug \
 --endpoint http://localhost:8000 \
 --label Issuer \
 --seed 000000000000000000000000Steward1 \
 --genesis-url http://localhost:9000/genesis \
 --ledger-pool-name localindypool \
 --wallet-key 123456 \
 --wallet-name issuer_wallet_prod \
 --wallet-type askar-anoncreds \
 --admin 0.0.0.0 8001 \
 --admin-insecure-mode \
 --public-invites \
 --auto-accept-invites \
 --auto-accept-requests \
 --auto-ping-connection \
 --auto-respond-messages \
 --auto-respond-credential-proposal \
 --auto-respond-credential-request \
 --auto-provision \
 --requests-through-public-did
"""

print(f"Iniciando Issuer na porta admin 8001...")
print(f"Comando: {command}")

# shlex.split lida corretamente com os argumentos
args = shlex.split(command)

try:
    # Usamos subprocess.run() que bloqueia, 
    # mantendo este script vivo enquanto o agente estiver rodando.
    process = subprocess.run(args, check=True)
except subprocess.CalledProcessError as e:
    print(f"O agente Issuer falhou: {e}")
except KeyboardInterrupt:
    print("\nParando o agente Issuer...")
    sys.exit(0)