"""Check the on-chain GenVM result of the payout (withdraw) transactions.

Usage: python tools/check_payout.py

Reads tools/deployment.json, prints the finalized status + the leader receipt's
execution_result for every withdraw transaction, and reports the contract's
current escrow balance and the payees' wallet balances.
"""

import json
import pathlib
import sys

from genlayer_py import create_client, create_account, studionet
from genlayer_py.types.transactions import TransactionStatus

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEP = json.loads((ROOT / "tools" / "deployment.json").read_text(encoding="utf-8"))
KEY_FILE = pathlib.Path(__file__).resolve().parent / ".deploy_key"


def leader_receipt(receipt):
    try:
        consensus = receipt["consensus_data"]
    except Exception:  # noqa: BLE001
        consensus = None
    if not isinstance(consensus, dict):
        return None
    lr = consensus.get("leader_receipt")
    if isinstance(lr, dict):
        return lr
    if isinstance(lr, list) and lr:
        return lr[0]
    return None


def main():
    deployer = create_account(KEY_FILE.read_text().strip())
    client = create_client(chain=studionet, account=deployer)
    address = DEP["contract"]
    print("contract:", address)

    for step in DEP["trace"]:
        if "withdraw" not in step["step"]:
            continue
        tx = step["tx"]
        try:
            receipt = client.wait_for_transaction_receipt(
                tx, status=TransactionStatus.FINALIZED, interval=3000, retries=40
            )
            lr = leader_receipt(receipt)
            execution = lr.get("execution_result") if lr else None
            error = (lr.get("error") or lr.get("execution_error")) if lr else None
            print("  %-32s status=%s execution=%s" % (step["step"], receipt["status_name"], execution))
            if error:
                print("      error: %s" % error)
        except Exception as exc:  # noqa: BLE001 - report and keep going
            print("  %-32s ERROR %s" % (step["step"], exc))

    print("escrow balance (wei):", client.read_contract(address=address, function_name="get_escrow_balance"))
    print("ledger:", client.read_contract(address=address, function_name="get_ledger"))
    print("deployer wallet (wei):", client.get_balance(deployer.address))
    freelancer = DEP.get("freelancer")
    if freelancer:
        print("freelancer wallet (wei):", client.get_balance(freelancer))
    return 0


if __name__ == "__main__":
    sys.exit(main())