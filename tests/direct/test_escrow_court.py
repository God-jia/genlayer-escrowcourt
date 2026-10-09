import json
from datetime import datetime, timedelta, timezone

MILESTONES = [
    {
        "id": "M1",
        "title": "Landing page",
        "criteria": [
            "A responsive landing page renders correctly on a mobile viewport.",
            "The hero section states the product name and the primary call to action.",
        ],
        "share_bps": 6000,
    },
    {
        "id": "M2",
        "title": "API integration",
        "criteria": [
            "The contact form posts to a working endpoint and stores the submission.",
        ],
        "share_bps": 4000,
    },
]

DELIVERABLE_URL = "https://example.com/repo/spec"
EVIDENCE_URL = "https://example.com/repo/m1"
BRIEF = (
    "Build a responsive landing page for the product and wire the contact form "
    "to a working backend endpoint that stores every submission."
)
CLAIM = (
    "The submitted page is missing the hero section and the form does not post "
    "anywhere, so the milestone is not complete."
)
AMOUNT = 100000

DAY = 24 * 60 * 60
EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)
BASE_EPOCH = int(EPOCH.timestamp())


def _at(seconds):
    """ISO-8601 timestamp *seconds* after the fixed test epoch."""
    return (EPOCH + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _warp(direct_vm, seconds):
    direct_vm.warp(_at(seconds))


def _deploy(direct_deploy):
    return direct_deploy("contracts/escrow_court.py")


def _create(contract, direct_vm, sender, milestones=None, value=AMOUNT):
    direct_vm.sender = sender
    direct_vm.value = value
    try:
        return contract.create_job(
            "Landing page and API integration",
            BRIEF,
            DELIVERABLE_URL,
            json.dumps(milestones if milestones is not None else MILESTONES),
        )
    finally:
        direct_vm.value = 0


def _client(contract, job_id):
    return json.loads(contract.get_job(job_id))["client"]


def _accept(contract, direct_vm, sender, job_id):
    direct_vm.sender = sender
    contract.accept_job(job_id)


def _submit(contract, direct_vm, sender, job_id, milestone_id="M1"):
    direct_vm.sender = sender
    contract.submit_milestone(
        job_id,
        milestone_id,
        EVIDENCE_URL,
        "Delivered the milestone and pushed the code to the shared repository.",
    )


def _dispute(contract, direct_vm, sender, job_id, milestone_id="M1"):
    direct_vm.sender = sender
    contract.dispute_milestone(job_id, milestone_id, CLAIM)


def _mock_web(direct_vm):
    direct_vm.mock_web(r".*example\.com/repo/spec.*", {"status": 200, "body": "<html>spec</html>"})
    direct_vm.mock_web(r".*example\.com/repo/m1.*", {"status": 200, "body": "<html>evidence</html>"})


def _mock_llm(direct_vm, payload):
    direct_vm.mock_llm(r".*milestone escrow.*", json.dumps(payload))


def _active_job(contract, direct_vm, direct_alice, direct_bob):
    """Create a job as alice, accept it as bob, return (job_id, alice, bob)."""
    job_id = _create(contract, direct_vm, direct_alice)
    alice = _client(contract, job_id)
    _accept(contract, direct_vm, direct_bob, job_id)
    bob = json.loads(contract.get_job(job_id))["freelancer"]
    return job_id, alice, bob


# ----------------------------------------------------------------------- create


def test_create_job_and_read(direct_vm, direct_deploy, direct_alice):
    contract = _deploy(direct_deploy)
    job_id = _create(contract, direct_vm, direct_alice)

    assert job_id == 0
    assert contract.total_jobs() == 1

    record = json.loads(contract.get_job(job_id))
    assert record["status"] == "open"
    assert record["amount"] == AMOUNT
    assert len(record["milestones"]) == 2
    assert record["milestones"][0]["share_bps"] == 6000
    assert record["milestones"][0]["status"] == "pending"
    assert record["freelancer"] == ""


def test_create_rejects_bad_milestones_json(direct_vm, direct_deploy, direct_alice):
    contract = _deploy(direct_deploy)
    direct_vm.sender = direct_alice
    direct_vm.value = AMOUNT

    try:
        with direct_vm.expect_revert("must be a JSON array"):
            contract.create_job("Landing page", BRIEF, DELIVERABLE_URL, "not json")
    finally:
        direct_vm.value = 0


def test_create_rejects_duplicate_milestone_ids(direct_vm, direct_deploy, direct_alice):
    contract = _deploy(direct_deploy)
    duplicated = [MILESTONES[0], dict(MILESTONES[0], share_bps=4000)]

    with direct_vm.expect_revert("Duplicate milestone id"):
        _create(contract, direct_vm, direct_alice, milestones=duplicated)


def test_create_rejects_shares_that_do_not_total(direct_vm, direct_deploy, direct_alice):
    contract = _deploy(direct_deploy)
    lopsided = [dict(MILESTONES[0], share_bps=5000), dict(MILESTONES[1], share_bps=4000)]

    with direct_vm.expect_revert("must add up to"):
        _create(contract, direct_vm, direct_alice, milestones=lopsided)


def test_create_rejects_short_brief(direct_vm, direct_deploy, direct_alice):
    contract = _deploy(direct_deploy)
    direct_vm.sender = direct_alice
    direct_vm.value = AMOUNT

    try:
        with direct_vm.expect_revert("Job brief must be"):
            contract.create_job(
                "Landing page", "too short", DELIVERABLE_URL, json.dumps(MILESTONES)
            )
    finally:
        direct_vm.value = 0


def test_create_rejects_thin_criterion(direct_vm, direct_deploy, direct_alice):
    contract = _deploy(direct_deploy)
    thin = [dict(MILESTONES[0], criteria=["short"]), MILESTONES[1]]

    with direct_vm.expect_revert("criterion must be"):
        _create(contract, direct_vm, direct_alice, milestones=thin)


def test_create_escrows_the_amount(direct_vm, direct_deploy, direct_alice):
    contract = _deploy(direct_deploy)
    job_id = _create(contract, direct_vm, direct_alice)

    record = json.loads(contract.get_job(job_id))
    assert record["amount"] == AMOUNT
    assert record["escrowed"] == AMOUNT


def test_create_escrows_the_sent_value(direct_vm, direct_deploy, direct_alice):
    contract = _deploy(direct_deploy)
    job_id = _create(contract, direct_vm, direct_alice, value=AMOUNT * 3)

    record = json.loads(contract.get_job(job_id))
    assert record["amount"] == AMOUNT * 3
    assert record["escrowed"] == AMOUNT * 3


def test_create_requires_a_funded_transaction(direct_vm, direct_deploy, direct_alice):
    contract = _deploy(direct_deploy)

    with direct_vm.expect_revert("Send the escrow amount"):
        _create(contract, direct_vm, direct_alice, value=0)


# ----------------------------------------------------------------------- accept


def test_client_cannot_accept_own_job(direct_vm, direct_deploy, direct_alice):
    contract = _deploy(direct_deploy)
    job_id = _create(contract, direct_vm, direct_alice)

    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("cannot accept their own job"):
        contract.accept_job(job_id)


def test_accept_twice_reverts(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = _deploy(direct_deploy)
    job_id = _create(contract, direct_vm, direct_alice)
    _accept(contract, direct_vm, direct_bob, job_id)

    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("Only an open job"):
        contract.accept_job(job_id)


def test_cancel_open_job_refunds_the_client(direct_vm, direct_deploy, direct_alice):
    contract = _deploy(direct_deploy)
    job_id = _create(contract, direct_vm, direct_alice)
    alice = _client(contract, job_id)

    direct_vm.sender = direct_alice
    contract.cancel_job(job_id)

    record = json.loads(contract.get_job(job_id))
    assert record["status"] == "cancelled"
    assert record["escrowed"] == 0
    assert contract.get_balance(alice) == AMOUNT


def test_cancel_after_accept_reverts(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = _deploy(direct_deploy)
    job_id = _create(contract, direct_vm, direct_alice)
    _accept(contract, direct_vm, direct_bob, job_id)

    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Only an open job can be cancelled"):
        contract.cancel_job(job_id)


# --------------------------------------------------------------------- submit


def test_submit_only_by_freelancer(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = _deploy(direct_deploy)
    job_id, _alice, _bob = _active_job(contract, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Only the freelancer"):
        contract.submit_milestone(job_id, "M1", EVIDENCE_URL, "Delivered everything on time.")


def test_submit_requires_pending_milestone(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = _deploy(direct_deploy)
    job_id, _alice, bob = _active_job(contract, direct_vm, direct_alice, direct_bob)
    _submit(contract, direct_vm, direct_bob, job_id)

    direct_vm.sender = bob
    with direct_vm.expect_revert("not awaiting a submission"):
        contract.submit_milestone(job_id, "M1", EVIDENCE_URL, "Delivered everything on time.")


# -------------------------------------------------------------------- approve


def test_approve_only_by_client(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = _deploy(direct_deploy)
    job_id, _alice, bob = _active_job(contract, direct_vm, direct_alice, direct_bob)
    _submit(contract, direct_vm, direct_bob, job_id)

    direct_vm.sender = bob
    with direct_vm.expect_revert("Only the client"):
        contract.approve_milestone(job_id, "M1")


def test_approve_releases_share_and_completes_job(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = _deploy(direct_deploy)
    job_id, _alice, bob = _active_job(contract, direct_vm, direct_alice, direct_bob)

    _submit(contract, direct_vm, direct_bob, job_id, "M1")
    direct_vm.sender = direct_alice
    contract.approve_milestone(job_id, "M1")

    record = json.loads(contract.get_job(job_id))
    assert record["milestones"][0]["status"] == "released"
    assert record["milestones"][0]["resolution"] == "release"
    assert record["status"] == "active"

    assert contract.get_balance(bob) == 60000

    _submit(contract, direct_vm, direct_bob, job_id, "M2")
    direct_vm.sender = direct_alice
    contract.approve_milestone(job_id, "M2")

    record = json.loads(contract.get_job(job_id))
    assert record["status"] == "completed"
    assert contract.get_balance(bob) == 100000

    reputation = json.loads(contract.get_reputation(bob))
    assert reputation["released"] == 2


# -------------------------------------------------------------------- withdraw


def test_withdraw_pays_out_and_zeroes_the_balance(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = _deploy(direct_deploy)
    job_id, _alice, bob = _active_job(contract, direct_vm, direct_alice, direct_bob)
    _submit(contract, direct_vm, direct_bob, job_id, "M1")

    direct_vm.sender = direct_alice
    contract.approve_milestone(job_id, "M1")
    assert contract.get_balance(bob) == 60000

    direct_vm.sender = direct_bob
    paid = contract.withdraw()

    assert paid == 60000
    assert contract.get_balance(bob) == 0
    assert contract.get_withdrawable(bob) == 0


def test_withdraw_with_no_balance_returns_zero(direct_vm, direct_deploy, direct_alice):
    contract = _deploy(direct_deploy)
    _create(contract, direct_vm, direct_alice)

    direct_vm.sender = direct_alice
    assert contract.withdraw() == 0


# -------------------------------------------------------------------- dispute


def test_dispute_only_by_client(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = _deploy(direct_deploy)
    job_id, _alice, bob = _active_job(contract, direct_vm, direct_alice, direct_bob)
    _submit(contract, direct_vm, direct_bob, job_id)

    direct_vm.sender = bob
    with direct_vm.expect_revert("Only the client"):
        contract.dispute_milestone(job_id, "M1", CLAIM)


def test_dispute_requires_a_substantial_claim(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = _deploy(direct_deploy)
    job_id, _alice, _bob = _active_job(contract, direct_vm, direct_alice, direct_bob)
    _submit(contract, direct_vm, direct_bob, job_id)

    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Dispute claim must be"):
        contract.dispute_milestone(job_id, "M1", "not good")


def test_adjudicate_requires_dispute(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = _deploy(direct_deploy)
    job_id, _alice, _bob = _active_job(contract, direct_vm, direct_alice, direct_bob)
    _submit(contract, direct_vm, direct_bob, job_id)

    with direct_vm.expect_revert("not under dispute"):
        contract.adjudicate_milestone(job_id, "M1")


# ---------------------------------------------------------------- adjudication


def test_adjudicate_releases_on_all_met(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = _deploy(direct_deploy)
    job_id, alice, bob = _active_job(contract, direct_vm, direct_alice, direct_bob)
    _submit(contract, direct_vm, direct_bob, job_id)
    _dispute(contract, direct_vm, direct_alice, job_id)

    _mock_web(direct_vm)
    _mock_llm(
        direct_vm,
        {
            "deliverable_available": True,
            "criteria": [
                {"index": 0, "verdict": "met", "reason": "The page renders responsively."},
                {"index": 1, "verdict": "met", "reason": "The hero names the product."},
            ],
            "confidence": 88,
            "reasoning": "Both criteria are satisfied by the delivered page.",
        },
    )

    contract.adjudicate_milestone(job_id, "M1")

    record = json.loads(contract.get_job(job_id))
    milestone = record["milestones"][0]
    assert milestone["status"] == "settled"
    assert milestone["resolution"] == "release"
    assert milestone["ruling"]["freelancer_cut"] == 60000
    assert milestone["ruling"]["client_cut"] == 0

    assert contract.get_balance(bob) == 60000
    assert contract.get_balance(alice) == 0

    reputation = json.loads(contract.get_reputation(bob))
    assert reputation["released"] == 1


def test_adjudicate_refunds_on_all_unmet(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = _deploy(direct_deploy)
    job_id, alice, bob = _active_job(contract, direct_vm, direct_alice, direct_bob)
    _submit(contract, direct_vm, direct_bob, job_id)
    _dispute(contract, direct_vm, direct_alice, job_id)

    _mock_web(direct_vm)
    _mock_llm(
        direct_vm,
        {
            "deliverable_available": True,
            "criteria": [
                {"index": 0, "verdict": "unmet", "reason": "The page does not render."},
                {"index": 1, "verdict": "unmet", "reason": "There is no hero section."},
            ],
            "confidence": 79,
            "reasoning": "The delivered work fails both acceptance criteria.",
        },
    )

    contract.adjudicate_milestone(job_id, "M1")

    record = json.loads(contract.get_job(job_id))
    milestone = record["milestones"][0]
    assert milestone["resolution"] == "refund"
    assert milestone["ruling"]["freelancer_cut"] == 0

    assert contract.get_balance(bob) == 0
    assert contract.get_balance(alice) == 60000

    reputation = json.loads(contract.get_reputation(bob))
    assert reputation["refunded"] == 1


def test_adjudicate_splits_on_mixed_verdicts(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = _deploy(direct_deploy)
    job_id, alice, bob = _active_job(contract, direct_vm, direct_alice, direct_bob)
    _submit(contract, direct_vm, direct_bob, job_id)
    _dispute(contract, direct_vm, direct_alice, job_id)

    _mock_web(direct_vm)
    _mock_llm(
        direct_vm,
        {
            "deliverable_available": True,
            "criteria": [
                {"index": 0, "verdict": "met", "reason": "The page renders responsively."},
                {"index": 1, "verdict": "unclear", "reason": "The hero section is not visible."},
            ],
            "confidence": 66,
            "reasoning": "One criterion holds and one cannot be verified.",
        },
    )

    contract.adjudicate_milestone(job_id, "M1")

    record = json.loads(contract.get_job(job_id))
    milestone = record["milestones"][0]
    assert milestone["resolution"] == "split"
    # two criteria: one met, one unclear -> weight 3 of 4
    assert milestone["ruling"]["freelancer_cut"] == 45000
    assert milestone["ruling"]["client_cut"] == 15000

    assert contract.get_balance(bob) == 45000
    assert contract.get_balance(alice) == 15000


def test_adjudicate_splits_when_deliverable_unavailable(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = _deploy(direct_deploy)
    job_id, _alice, _bob = _active_job(contract, direct_vm, direct_alice, direct_bob)
    _submit(contract, direct_vm, direct_bob, job_id)
    _dispute(contract, direct_vm, direct_alice, job_id)

    direct_vm.mock_web(r".*example\.com/repo/spec.*", {"status": 404, "body": "gone"})
    direct_vm.mock_web(r".*example\.com/repo/m1.*", {"status": 200, "body": "<html>evidence</html>"})
    _mock_llm(
        direct_vm,
        {
            "deliverable_available": False,
            "criteria": [
                {"index": 0, "verdict": "unclear", "reason": "The deliverable is unreachable."},
                {"index": 1, "verdict": "unclear", "reason": "The deliverable is unreachable."},
            ],
            "confidence": 35,
            "reasoning": "The deliverable could not be retrieved.",
        },
    )

    contract.adjudicate_milestone(job_id, "M1")

    record = json.loads(contract.get_job(job_id))
    milestone = record["milestones"][0]
    assert milestone["ruling"]["deliverable_available"] is False
    assert milestone["resolution"] == "split"
    # two unclear criteria -> weight 2 of 4
    assert milestone["ruling"]["freelancer_cut"] == 30000


def test_adjudicate_twice_reverts(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = _deploy(direct_deploy)
    job_id, _alice, _bob = _active_job(contract, direct_vm, direct_alice, direct_bob)
    _submit(contract, direct_vm, direct_bob, job_id)
    _dispute(contract, direct_vm, direct_alice, job_id)

    _mock_web(direct_vm)
    _mock_llm(
        direct_vm,
        {
            "deliverable_available": True,
            "criteria": [
                {"index": 0, "verdict": "met", "reason": "It renders."},
                {"index": 1, "verdict": "met", "reason": "The hero is present."},
            ],
            "confidence": 90,
            "reasoning": "Everything checks out.",
        },
    )

    contract.adjudicate_milestone(job_id, "M1")

    with direct_vm.expect_revert("not under dispute"):
        contract.adjudicate_milestone(job_id, "M1")


# ----------------------------------------------------------------------- views


def test_unknown_ids_revert(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = _deploy(direct_deploy)

    with direct_vm.expect_revert("Unknown job id"):
        contract.get_job(999)

    job_id, _alice, _bob = _active_job(contract, direct_vm, direct_alice, direct_bob)
    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("Unknown milestone id"):
        contract.submit_milestone(job_id, "ZZ", EVIDENCE_URL, "Delivered everything on time.")


def test_reputation_starts_at_zero(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = _deploy(direct_deploy)
    _job_id, alice, bob = _active_job(contract, direct_vm, direct_alice, direct_bob)

    assert json.loads(contract.get_reputation(alice)) == {
        "released": 0,
        "refunded": 0,
        "split": 0,
        "disputes_raised": 0,
    }
    assert json.loads(contract.get_reputation(bob)) == {
        "released": 0,
        "refunded": 0,
        "split": 0,
        "disputes_raised": 0,
    }
    assert contract.get_balance(bob) == 0


# ------------------------------------------------------------------ recovery


def test_default_windows_are_exposed(direct_vm, direct_deploy):
    contract = _deploy(direct_deploy)

    assert json.loads(contract.get_terms()) == {
        "accept_window": 7 * DAY,
        "submit_window": 14 * DAY,
        "review_window": 7 * DAY,
        "ruling_window": 7 * DAY,
    }


def test_windows_are_configurable_at_deploy(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = direct_deploy("contracts/escrow_court.py", 60, 120, 60, 60)
    assert json.loads(contract.get_terms())["submit_window"] == 120

    _warp(direct_vm, 0)
    job_id, alice, _bob = _active_job(contract, direct_vm, direct_alice, direct_bob)

    _warp(direct_vm, 121)
    direct_vm.sender = direct_alice
    contract.resolve_stalled_milestone(job_id, "M1")
    assert contract.get_balance(alice) == 60000


def test_windows_below_the_floor_are_rejected(direct_vm, direct_deploy):
    with direct_vm.expect_revert("at least 60 seconds"):
        direct_deploy("contracts/escrow_court.py", 0, 120, 60, 60)


def test_expire_open_job_refunds_a_job_nobody_accepted(
    direct_vm, direct_deploy, direct_alice, direct_charlie
):
    contract = _deploy(direct_deploy)
    _warp(direct_vm, 0)
    job_id = _create(contract, direct_vm, direct_alice)
    alice = _client(contract, job_id)

    # Anyone can finalise an abandoned job once its accept window closes.
    _warp(direct_vm, 7 * DAY + 1)
    direct_vm.sender = direct_charlie
    contract.expire_open_job(job_id)

    record = json.loads(contract.get_job(job_id))
    assert record["status"] == "expired"
    assert record["escrowed"] == 0
    assert contract.get_balance(alice) == AMOUNT


def test_expire_open_job_before_the_deadline_reverts(
    direct_vm, direct_deploy, direct_alice
):
    contract = _deploy(direct_deploy)
    _warp(direct_vm, 0)
    job_id = _create(contract, direct_vm, direct_alice)

    _warp(direct_vm, 6 * DAY)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("accept window has not closed"):
        contract.expire_open_job(job_id)


def test_expire_open_job_rejects_an_accepted_job(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = _deploy(direct_deploy)
    _warp(direct_vm, 0)
    job_id, _alice, _bob = _active_job(contract, direct_vm, direct_alice, direct_bob)

    _warp(direct_vm, 8 * DAY)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Only an open job can expire"):
        contract.expire_open_job(job_id)


def test_resolve_pending_milestone_refunds_the_client(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = _deploy(direct_deploy)
    _warp(direct_vm, 0)
    job_id, alice, bob = _active_job(contract, direct_vm, direct_alice, direct_bob)

    # The freelancer never delivers, so after the submission window the client
    # reclaims that milestone's share.
    _warp(direct_vm, 14 * DAY + 1)
    direct_vm.sender = direct_alice
    contract.resolve_stalled_milestone(job_id, "M1")

    record = json.loads(contract.get_job(job_id))
    milestone = record["milestones"][0]
    assert milestone["status"] == "expired"
    assert milestone["resolution"] == "refund"
    assert milestone["ruling"]["source"] == "timeout"
    assert milestone["ruling"]["elapsed_window"] == "pending"
    assert contract.get_balance(alice) == 60000
    assert contract.get_balance(bob) == 0


def test_resolve_pending_milestone_before_the_deadline_reverts(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = _deploy(direct_deploy)
    _warp(direct_vm, 0)
    job_id, _alice, _bob = _active_job(contract, direct_vm, direct_alice, direct_bob)

    _warp(direct_vm, 13 * DAY)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("deadline has not passed"):
        contract.resolve_stalled_milestone(job_id, "M1")


def test_resolve_submitted_milestone_pays_the_freelancer(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = _deploy(direct_deploy)
    _warp(direct_vm, 0)
    job_id, alice, bob = _active_job(contract, direct_vm, direct_alice, direct_bob)
    _submit(contract, direct_vm, direct_bob, job_id)

    # The client neither approves nor disputes: the freelancer is still paid.
    _warp(direct_vm, 7 * DAY + 1)
    direct_vm.sender = direct_bob
    contract.resolve_stalled_milestone(job_id, "M1")

    record = json.loads(contract.get_job(job_id))
    milestone = record["milestones"][0]
    assert milestone["status"] == "expired"
    assert milestone["resolution"] == "release"
    assert milestone["ruling"]["elapsed_window"] == "submitted"
    assert contract.get_balance(bob) == 60000
    assert contract.get_balance(alice) == 0


def test_resolve_disputed_milestone_splits_evenly(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = _deploy(direct_deploy)
    _warp(direct_vm, 0)
    job_id, alice, bob = _active_job(contract, direct_vm, direct_alice, direct_bob)
    _submit(contract, direct_vm, direct_bob, job_id)
    _dispute(contract, direct_vm, direct_alice, job_id)

    # Adjudication never settles the dispute; the ruling window forces a split.
    _warp(direct_vm, 7 * DAY + 1)
    direct_vm.sender = direct_alice
    contract.resolve_stalled_milestone(job_id, "M1")

    record = json.loads(contract.get_job(job_id))
    milestone = record["milestones"][0]
    assert milestone["status"] == "expired"
    assert milestone["resolution"] == "split"
    assert milestone["ruling"]["elapsed_window"] == "disputed"
    assert contract.get_balance(bob) == 30000
    assert contract.get_balance(alice) == 30000


def test_resolve_stalled_milestone_is_permissionless(
    direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie
):
    contract = _deploy(direct_deploy)
    _warp(direct_vm, 0)
    job_id, alice, _bob = _active_job(contract, direct_vm, direct_alice, direct_bob)

    _warp(direct_vm, 14 * DAY + 1)
    direct_vm.sender = direct_charlie
    contract.resolve_stalled_milestone(job_id, "M1")

    assert contract.get_balance(alice) == 60000


def test_resolve_stalled_milestone_rejects_a_settled_milestone(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = _deploy(direct_deploy)
    _warp(direct_vm, 0)
    job_id, _alice, _bob = _active_job(contract, direct_vm, direct_alice, direct_bob)
    _submit(contract, direct_vm, direct_bob, job_id)

    direct_vm.sender = direct_alice
    contract.approve_milestone(job_id, "M1")

    _warp(direct_vm, 30 * DAY)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("already settled"):
        contract.resolve_stalled_milestone(job_id, "M1")


def test_resolve_stalled_milestone_requires_an_active_job(
    direct_vm, direct_deploy, direct_alice
):
    contract = _deploy(direct_deploy)
    _warp(direct_vm, 0)
    job_id = _create(contract, direct_vm, direct_alice)

    _warp(direct_vm, 30 * DAY)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("job is not active"):
        contract.resolve_stalled_milestone(job_id, "M1")


def test_deadline_renews_after_a_milestone_settles(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    contract = _deploy(direct_deploy)
    _warp(direct_vm, 0)
    job_id, _alice, _bob = _active_job(contract, direct_vm, direct_alice, direct_bob)

    before = json.loads(contract.get_job(job_id))["milestones"][1]["due_at"]
    assert before == BASE_EPOCH + 14 * DAY

    # A late approval on M1 pushes M2's deadline out, so a slow review on an
    # early milestone cannot quietly expire the work still to be delivered.
    _warp(direct_vm, 2 * DAY)
    _submit(contract, direct_vm, direct_bob, job_id, "M1")
    direct_vm.sender = direct_alice
    contract.approve_milestone(job_id, "M1")

    after = json.loads(contract.get_job(job_id))["milestones"][1]["due_at"]
    assert after == BASE_EPOCH + 2 * DAY + 14 * DAY


def test_client_cannot_strand_the_freelancer(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    """Adversarial: a client that refuses to approve or dispute still cannot
    hold the freelancer's money forever."""
    contract = _deploy(direct_deploy)
    _warp(direct_vm, 0)
    job_id, _alice, bob = _active_job(contract, direct_vm, direct_alice, direct_bob)
    _submit(contract, direct_vm, direct_bob, job_id, "M1")

    # The client goes silent and the milestone sits submitted.
    _warp(direct_vm, 7 * DAY)
    assert json.loads(contract.get_job(job_id))["milestones"][0]["status"] == "submitted"

    # Once the review window closes the freelancer is paid without the client.
    _warp(direct_vm, 7 * DAY + 1)
    direct_vm.sender = direct_bob
    contract.resolve_stalled_milestone(job_id, "M1")

    assert contract.get_balance(bob) == 60000
    direct_vm.sender = direct_bob
    assert contract.withdraw() == 60000
    assert contract.get_balance(bob) == 0


def test_freelancer_cannot_strand_the_client(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    """Adversarial: a freelancer that accepts and disappears still cannot hold
    the client's escrow forever."""
    contract = _deploy(direct_deploy)
    _warp(direct_vm, 0)
    job_id, alice, _bob = _active_job(contract, direct_vm, direct_alice, direct_bob)

    # The freelancer never submits anything at all.
    _warp(direct_vm, 14 * DAY + 1)
    direct_vm.sender = direct_alice
    contract.resolve_stalled_milestone(job_id, "M1")
    contract.resolve_stalled_milestone(job_id, "M2")

    record = json.loads(contract.get_job(job_id))
    assert record["status"] == "completed"
    assert all(m["status"] == "expired" for m in record["milestones"])
    assert contract.get_balance(alice) == AMOUNT

    direct_vm.sender = direct_alice
    assert contract.withdraw() == AMOUNT
    assert contract.get_balance(alice) == 0


def test_a_dispute_cannot_freeze_the_escrow(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    """Adversarial: a dispute that is never adjudicated still cannot lock the
    escrow, because the ruling window forces a deterministic split."""
    contract = _deploy(direct_deploy)
    _warp(direct_vm, 0)
    job_id, alice, bob = _active_job(contract, direct_vm, direct_alice, direct_bob)
    _submit(contract, direct_vm, direct_bob, job_id, "M1")
    _dispute(contract, direct_vm, direct_alice, job_id, "M1")

    _warp(direct_vm, 7 * DAY + 1)
    direct_vm.sender = direct_bob
    contract.resolve_stalled_milestone(job_id, "M1")

    assert contract.get_balance(bob) == 30000
    assert contract.get_balance(alice) == 30000

    direct_vm.sender = direct_bob
    assert contract.withdraw() == 30000
    direct_vm.sender = direct_alice
    assert contract.withdraw() == 30000
    assert contract.get_escrow_balance() == 0
