"""Deploy EscrowCourt to studionet and run the full lifecycle.

Usage: python tools/deploy_and_demo.py

Keeps the deployer key in tools/.deploy_key so re-runs reuse the same address,
and records the deployment in tools/deployment.json.
"""

import json
import pathlib
import sys
import time

from genlayer_py import create_client, create_account, studionet
from genlayer_py.types.transactions import TransactionStatus

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "contracts" / "escrow_court.py"
KEY_FILE = pathlib.Path(__file__).resolve().parent / ".deploy_key"
OUT_FILE = ROOT / "tools" / "deployment.json"

DELIVERABLE_URL = "https://example.com/"
EVIDENCE_URL = "https://www.iana.org/help/example-domains"

# Escrow amount in wei (1 GEN = 10**18 wei). The client sends exactly this much
# when opening the job; the contract holds it until a milestone settles.
ESCROW = 10**15

BRIEF = (
    "Build a static landing page for a documentation example domain. The page must be "
    "served over HTTPS, present a clear top-level heading, and list at least three "
    "distinct product features. Deliver the page at the agreed URL."
)

MILESTONES = [
    {
        "id": "M1",
        "title": "Responsive landing page",
        "criteria": [
            "The page is served over HTTPS and returns an HTML document.",
            "The page contains a visible top-level heading.",
            "The page lists at least three distinct product features.",
        ],
        "share_bps": 6000,
    },
    {
        "id": "M2",
        "title": "Accessibility pass",
        "criteria": [
            "The page is reachable over HTTPS without a redirect loop.",
            "The document exposes a readable title element.",
        ],
        "share_bps": 4000,
    },
]

CLAIM = (
    "The delivered page is a bare placeholder. It does not present the three product "
    "features we agreed on, so this milestone should not be paid in full."
)


def field(receipt, *names):
    for name in names:
        value = receipt.get(name) if isinstance(receipt, dict) else getattr(receipt, name, None)
        if value:
            return value
    return None


def as_hex(value):
    if isinstance(value, bytes):
        return "0x" + value.hex()
    return str(value)


def load_or_create_key():
    if KEY_FILE.exists():
        return create_account(KEY_FILE.read_text().strip())
    account = create_account()
    KEY_FILE.write_text(account.key.hex())
    return account


def ensure_funded(client, account, minimum=10**17):
    balance = client.get_balance(account.address)
    if balance >= minimum:
        return
    print("funding", account.address)
    client.fund_account(account.address, 10**18)
    for _ in range(10):
        time.sleep(2)
        if client.get_balance(account.address) > 0:
            break


def finalize(client, tx_hash, label):
    receipt = None
    for attempt in range(6):
        try:
            receipt = client.wait_for_transaction_receipt(
                tx_hash, status=TransactionStatus.FINALIZED, interval=4000, retries=120
            )
            break
        except Exception as exc:  # noqa: BLE001 - transient studionet RPC flakiness
            print("  retry %d for %s: %s" % (attempt + 1, label, exc))
            time.sleep(5)
    if receipt is None:
        raise RuntimeError("could not finalize %s (%s)" % (label, as_hex(tx_hash)))
    print(
        "  %-22s %s / %s"
        % (label, field(receipt, "status_name", "status"), field(receipt, "tx_execution_result_name"))
    )
    record(label, tx_hash)
    return receipt


TRACE = []


def record(label, tx):
    TRACE.append({"step": label, "tx": as_hex(tx)})


def main():
    code = CONTRACT.read_text(encoding="utf-8")

    deployer = load_or_create_key()
    client = create_client(chain=studionet, account=deployer)
    print("deployer:", deployer.address)
    ensure_funded(client, deployer)

    freelancer = create_account()
    ensure_funded(client, freelancer)
    print("freelancer:", freelancer.address)

    print("\n== deploy ==")
    deploy_tx = client.deploy_contract(code=code)
    receipt = finalize(client, deploy_tx, "deploy")
    address = field(receipt, "to_address", "recipient")
    address = as_hex(address)
    print("contract:", address)
    print("deploy tx:", as_hex(deploy_tx))

    print("\n== lifecycle ==")
    milestones_json = json.dumps(MILESTONES)

    tx = client.write_contract(
        address=address,
        function_name="create_job",
        args=["Example-domain landing page", BRIEF, DELIVERABLE_URL, ESCROW, milestones_json],
        value=ESCROW,
    )
    finalize(client, tx, "create_job (escrow funded)")

    tx = client.write_contract(
        address=address, function_name="accept_job", account=freelancer, args=[0]
    )
    finalize(client, tx, "accept_job")

    tx = client.write_contract(
        address=address,
        function_name="submit_milestone",
        account=freelancer,
        args=[
            0,
            "M1",
            EVIDENCE_URL,
            "Delivered the landing page at the agreed URL and added the IANA reference page as evidence.",
        ],
    )
    finalize(client, tx, "submit_milestone M1")

    tx = client.write_contract(
        address=address, function_name="dispute_milestone", args=[0, "M1", CLAIM]
    )
    finalize(client, tx, "dispute_milestone M1")

    tx = client.write_contract(
        address=address, function_name="adjudicate_milestone", args=[0, "M1"]
    )
    finalize(client, tx, "adjudicate_milestone M1")

    tx = client.write_contract(
        address=address,
        function_name="submit_milestone",
        account=freelancer,
        args=[
            0,
            "M2",
            EVIDENCE_URL,
            "Accessibility pass completed; the page loads over HTTPS and exposes a title element.",
        ],
    )
    finalize(client, tx, "submit_milestone M2")

    tx = client.write_contract(
        address=address, function_name="approve_milestone", args=[0, "M2"]
    )
    finalize(client, tx, "approve_milestone M2")

    # Settled balances are now withdrawable; pull them out as real GEN transfers.
    print("\n== payouts (real GEN transfers) ==")
    tx = client.write_contract(
        address=address, function_name="withdraw", account=freelancer, args=[]
    )
    finalize(client, tx, "withdraw (freelancer)")

    tx = client.write_contract(address=address, function_name="withdraw", args=[])
    finalize(client, tx, "withdraw (client)")

    print("\n== state ==")
    job = client.read_contract(address=address, function_name="get_job", args=[0])
    ledger = client.read_contract(address=address, function_name="get_ledger")
    reputation = client.read_contract(
        address=address, function_name="get_reputation", args=[freelancer.address]
    )
    total = client.read_contract(address=address, function_name="total_jobs")
    escrow_balance = client.read_contract(
        address=address, function_name="get_escrow_balance"
    )
    freelancer_balance = client.get_balance(freelancer.address)

    print("total_jobs:", total)
    print("escrow balance (wei):", escrow_balance)
    print("ledger:", json.dumps(ledger, sort_keys=True))
    print("freelancer reputation:", json.dumps(reputation, sort_keys=True))
    print("freelancer wallet balance (wei):", freelancer_balance)
    print("job:", json.dumps(job, indent=2, sort_keys=True))

    OUT_FILE.write_text(
        json.dumps(
            {
                "contract": address,
                "deploy_tx": as_hex(deploy_tx),
                "deployer": deployer.address,
                "freelancer": freelancer.address,
                "escrow_amount_wei": ESCROW,
                "escrow_balance_wei": str(escrow_balance),
                "freelancer_balance_wei": str(freelancer_balance),
                "job": job,
                "ledger": ledger,
                "reputation": reputation,
                "total_jobs": total,
                "trace": TRACE,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("\nwrote", OUT_FILE)


if __name__ == "__main__":
    sys.exit(main())
