import subprocess
import shlex
import sys

command = """
aca-py start \
 --inbound-transport http 0.0.0.0 8010 \
 --outbound-transport ws \
 --outbound-transport http \
 --log-level debug \
 --endpoint http://localhost:8010 \
 --label Holder \
 --seed 000000000000000000000000Steward1 \
 --genesis-url http://localhost:9000/genesis \
 --ledger-pool-name localindypool \
 --wallet-key 123456 \
 --wallet-name holder_wallet_clean \
 --wallet-type askar-anoncreds \
 --admin 0.0.0.0 8011 \
 --admin-insecure-mode \
 --auto-provision \
 --auto-accept-invites \
 --auto-accept-requests \
 --auto-ping-connection \
 --auto-respond-messages \
 --auto-respond-credential-offer \
 --auto-store-credential \
 --auto-respond-presentation-request \
 --auto-respond-presentation-proposal
"""

print(f"Iniciando Holder na porta admin 8011...")
print(f"Comando: {command}")

args = shlex.split(command)

try:
    process = subprocess.run(args, check=True)
except subprocess.CalledProcessError as e:
    print(f"O agente Holder falhou: {e}")
except KeyboardInterrupt:
    print("\nParando o agente Holder...")
    sys.exit(0)