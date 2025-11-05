import subprocess
import shlex
import sys

command = """
aca-py start \
 --inbound-transport http 0.0.0.0 8020 \
 --outbound-transport ws \
 --outbound-transport http \
 --log-level debug \
 --endpoint http://localhost:8020 \
 --label Verifier \
 --seed 000000000000000000000000Steward1 \
 --genesis-url http://localhost:9000/genesis \
 --ledger-pool-name localindypool \
 --wallet-key 123456 \
 --wallet-name verifier_wallet_clean \
 --wallet-type askar-anoncreds \
 --admin 0.0.0.0 8021 \
 --admin-insecure-mode \
 --auto-provision \
 --auto-accept-invites \
 --auto-accept-requests \
 --auto-ping-connection \
 --auto-respond-messages \
 --public-invites
"""

print(f"Iniciando Verifier na porta admin 8021...")
print(f"Comando: {command}")

args = shlex.split(command)

try:
    process = subprocess.run(args, check=True)
except subprocess.CalledProcessError as e:
    print(f"O agente Verifier falhou: {e}")
except KeyboardInterrupt:
    print("\nParando o agente Verifier...")
    sys.exit(0)