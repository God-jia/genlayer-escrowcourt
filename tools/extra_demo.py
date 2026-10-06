"""Run one more escrow on the deployed contract so the dApp has a live
withdrawable balance to show, then pull it out.

Usage:
  python tools/extra_demo.py             # create + accept + submit + approve
  python tools/extra_demo.py --withdraw  # real GEN transfer to the freelancer
"""

import json
import pathlib
import sys
import time

from genlayer_py import create_client, create_account, studionet
from genlayer_py.types.transactions import TransactionStatus

TOOLS = pathlib.Path(__file__).resolve().parent
ROOT = TOOLS.parent
KEY_FILE = TOOLS / ".deploy_key"
FREE_KEY = TOOLS / ".freelancer_key"
DEPLOY_FILE = TOOLS / "deployment.json"

ESCROW = 10**15
DELIVERABLE_URL = "https://example.com/"
EVIDENCE_URL = "https://www.iana.org/help/example-domains"

BRIEF = (
    "Ship a single-page product site for the example domain, served over HTTPS with a "
    "readable title. Deliver it at the agreed URL."
)

MILESTONES = [
    {
        "id": "M1",
        "title": "Single-page product site",
        "criteria": [
            "The page is reachable over HTTPS.",
            "The document exposes a readable title element.",
        ],
        "share_bps": 10000,
    }
]


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
        "  %-20s %s / %s"
        % (label, field(receipt, "status_name", "status"), field(receipt, "tx_execution_result_name"))
    )
    return receipt


def ensure_funded(client, account, minimum=10**17):
    if client.get_balance(account.address) >= minimum:
        return
    print("funding", account.address)
    client.fund_account(account.address, 10**18)
    for _ in range(10):
        time.sleep(2)
        if client.get_balance(account.address) > 0:
            break


def main():
    deploy = json.loads(DEPLOY_FILE.read_text(encoding="utf-8"))
    address = deploy["contract"]

    deployer = create_account(KEY_FILE.read_text().strip())
    client = create_client(chain=studionet, account=deployer)

    if "--withdraw" in sys.argv:
        freelancer = create_account(FREE_KEY.read_text().strip())
        print("withdrawing for", freelancer.address)
        tx = client.write_contract(
            address=address, function_name="withdraw", account=freelancer, args=[]
        )
        finalize(client, tx, "withdraw (freelancer)")
        print("withdraw tx:", as_hex(tx))
        print("freelancer wallet (wei):", client.get_balance(freelancer.address))
        print("escrow balance (wei):", client.read_contract(address=address, function_name="get_escrow_balance"))
        return 0

    freelancer = create_account()
    FREE_KEY.write_text(freelancer.key.hex())
    ensure_funded(client, freelancer)
    print("freelancer:", freelancer.address)

    total = int(client.read_contract(address=address, function_name="total_jobs"))
    job_id = total
    print("creating job #%d" % job_id)

    tx = client.write_contract(
        address=address,
        function_name="create_job",
        args=["Example-domain product site", BRIEF, DELIVERABLE_URL, ESCROW, json.dumps(MILESTONES)],
        value=ESCROW,
    )
    finalize(client, tx, "create_job (funded)")
    print("create tx:", as_hex(tx))

    tx = client.write_contract(address=address, function_name="accept_job", account=freelancer, args=[job_id])
    finalize(client, tx, "accept_job")

    tx = client.write_contract(
        address=address,
        function_name="submit_milestone",
        account=freelancer,
        args=[job_id, "M1", EVIDENCE_URL, "Shipped the single-page site at the agreed URL."],
    )
    finalize(client, tx, "submit_milestone M1")

    tx = client.write_contract(address=address, function_name="approve_milestone", args=[job_id, "M1"])
    finalize(client, tx, "approve_milestone M1")

    print("\nfreelancer:", freelancer.address)
    print("withdrawable (wei):", client.read_contract(address=address, function_name="get_withdrawable", args=[freelancer.address]))
    print("escrow balance (wei):", client.read_contract(address=address, function_name="get_escrow_balance"))
    print("reputation:", json.dumps(client.read_contract(address=address, function_name="get_reputation", args=[freelancer.address]), sort_keys=True))
    print("total_jobs:", client.read_contract(address=address, function_name="total_jobs"))
    return 0


if __name__ == "__main__":
    sys.exit(main())