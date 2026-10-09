"""Exercise the timeout / refund recovery paths on studionet, for real.

The production windows are measured in days, which makes the recovery paths
impossible to observe live. This script deploys the *same* contract with a
60-second window in every state and drives each stalled case to completion, so
the evidence is real GenVM SUCCESS transactions rather than a description.

Usage: python tools/demo_recovery.py

Writes tools/recovery.json.
"""

import json
import pathlib
import time

from genlayer_py import create_client, create_account, studionet
from genlayer_py.types.transactions import TransactionStatus

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "contracts" / "escrow_court.py"
TOOLS = pathlib.Path(__file__).resolve().parent
KEY_FILE = TOOLS / ".deploy_key"
OUT_FILE = TOOLS / "recovery.json"

ESCROW = 10**15
WINDOW = 60
WINDOWS = [WINDOW, WINDOW, WINDOW, WINDOW]

DELIVERABLE_URL = "https://example.com/"
EVIDENCE_URL = "https://www.iana.org/help/example-domains"

BRIEF = (
    "Produce a single page that is served over HTTPS and exposes a readable "
    "title, delivered at the agreed URL."
)

MILESTONES = [
    {
        "id": "M1",
        "title": "Recovery probe",
        "criteria": ["The deliverable is reachable over HTTPS."],
        "share_bps": 10000,
    }
]

CLAIM = (
    "The delivered page does not expose a readable title, so this milestone is "
    "not complete and should not be paid in full."
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


def ensure_funded(client, account, minimum=10**17):
    if client.get_balance(account.address) >= minimum:
        return
    print("funding", account.address)
    client.fund_account(account.address, 10**18)
    for _ in range(10):
        time.sleep(2)
        if client.get_balance(account.address) > 0:
            break


TRACE = []


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
    status = field(receipt, "status_name", "status")
    result = field(receipt, "tx_execution_result_name")
    print("  %-28s %s / %s" % (label, status, result))
    TRACE.append({"step": label, "tx": as_hex(tx_hash), "result": str(result)})
    return receipt


def job_state(client, address, job_id):
    return json.loads(client.read_contract(address=address, function_name="get_job", args=[job_id]))


def main():
    code = CONTRACT.read_text(encoding="utf-8")

    deployer = create_account(KEY_FILE.read_text().strip())
    client = create_client(chain=studionet, account=deployer)
    ensure_funded(client, deployer)

    freelancer = create_account()
    ensure_funded(client, freelancer)
    print("client:", deployer.address)
    print("freelancer:", freelancer.address)

    print("\n== deploy (60s window in every state) ==")
    deploy_tx = client.deploy_contract(code=code, args=WINDOWS)
    receipt = finalize(client, deploy_tx, "deploy")
    address = as_hex(field(receipt, "to_address", "recipient"))
    print("contract:", address)

    milestones_json = json.dumps(MILESTONES)

    def create(title):
        tx = client.write_contract(
            address=address,
            function_name="create_job",
            args=[title, BRIEF, DELIVERABLE_URL, milestones_json],
            value=ESCROW,
        )
        finalize(client, tx, "create_job: " + title)
        total = int(client.read_contract(address=address, function_name="total_jobs"))
        return total - 1

    def submit(job_id):
        tx = client.write_contract(
            address=address,
            function_name="submit_milestone",
            account=freelancer,
            args=[
                job_id,
                "M1",
                EVIDENCE_URL,
                "Delivered the page at the agreed URL with the requested title element.",
            ],
        )
        finalize(client, tx, "submit_milestone M1 (job %d)" % job_id)

    print("\n== stage four stalled jobs ==")

    # A: nobody ever accepts -> the accept window must refund the client.
    job_a = create("Abandoned before acceptance")

    # B: accepted, then the freelancer never delivers.
    job_b = create("Abandoned by the freelancer")
    tx = client.write_contract(
        address=address, function_name="accept_job", account=freelancer, args=[job_b]
    )
    finalize(client, tx, "accept_job (job %d)" % job_b)

    # C: delivered, then the client never approves or disputes.
    job_c = create("Ignored by the client")
    tx = client.write_contract(
        address=address, function_name="accept_job", account=freelancer, args=[job_c]
    )
    finalize(client, tx, "accept_job (job %d)" % job_c)
    submit(job_c)

    # D: disputed, and adjudication never settles it.
    job_d = create("Dispute nobody adjudicates")
    tx = client.write_contract(
        address=address, function_name="accept_job", account=freelancer, args=[job_d]
    )
    finalize(client, tx, "accept_job (job %d)" % job_d)
    submit(job_d)
    tx = client.write_contract(
        address=address, function_name="dispute_milestone", args=[job_d, "M1", CLAIM]
    )
    finalize(client, tx, "dispute_milestone M1 (job %d)" % job_d)

    wait = WINDOW + 10
    print("\nwaiting %ds for every deadline to lapse..." % wait)
    time.sleep(wait)

    print("\n== settle the stalled jobs (permissionless) ==")

    # Anyone can finalise an unaccepted job.
    tx = client.write_contract(address=address, function_name="expire_open_job", args=[job_a])
    finalize(client, tx, "expire_open_job (job %d)" % job_a)

    for job_id, label in (
        (job_b, "resolve_stalled_milestone (job %d: pending)" % job_b),
        (job_c, "resolve_stalled_milestone (job %d: submitted)" % job_c),
        (job_d, "resolve_stalled_milestone (job %d: disputed)" % job_d),
    ):
        tx = client.write_contract(
            address=address, function_name="resolve_stalled_milestone", args=[job_id, "M1"]
        )
        finalize(client, tx, label)

    print("\n== withdraw the recovered GEN ==")
    for account, label in (
        (deployer, "withdraw (client)"),
        (freelancer, "withdraw (freelancer)"),
    ):
        tx = client.write_contract(
            address=address, function_name="withdraw", account=account, args=[]
        )
        finalize(client, tx, label)

    print("\n== state ==")
    jobs = {}
    for name, job_id in (("A", job_a), ("B", job_b), ("C", job_c), ("D", job_d)):
        record = job_state(client, address, job_id)
        milestone = record["milestones"][0]
        jobs[name] = {
            "job_id": job_id,
            "status": record["status"],
            "milestone_status": milestone["status"],
            "resolution": milestone["resolution"],
            "ruling": milestone["ruling"],
        }
        print(
            "  %s job %d -> job=%s milestone=%s resolution=%s"
            % (name, job_id, record["status"], milestone["status"], milestone["resolution"])
        )

    escrow_balance = client.read_contract(address=address, function_name="get_escrow_balance")
    client_balance = client.get_balance(deployer.address)
    freelancer_balance = client.get_balance(freelancer.address)
    print("escrow balance (wei):", escrow_balance)
    print("client wallet (wei):", client_balance)
    print("freelancer wallet (wei):", freelancer_balance)

    OUT_FILE.write_text(
        json.dumps(
            {
                "contract": address,
                "deploy_tx": as_hex(deploy_tx),
                "windows_seconds": WINDOWS,
                "client": deployer.address,
                "freelancer": freelancer.address,
                "escrow_amount_wei": ESCROW,
                "escrow_balance_wei": str(escrow_balance),
                "client_balance_wei": str(client_balance),
                "freelancer_balance_wei": str(freelancer_balance),
                "jobs": jobs,
                "trace": TRACE,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("\nwrote", OUT_FILE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
