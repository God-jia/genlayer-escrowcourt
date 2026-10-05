import json

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


def _deploy(direct_deploy):
    return direct_deploy("contracts/escrow_court.py")


def _create(contract, direct_vm, sender, milestones=None, amount=AMOUNT):
    direct_vm.sender = sender
    return contract.create_job(
        "Landing page and API integration",
        BRIEF,
        DELIVERABLE_URL,
        amount,
        json.dumps(milestones if milestones is not None else MILESTONES),
    )


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

    with direct_vm.expect_revert("must be a JSON array"):
        contract.create_job("Landing page", BRIEF, DELIVERABLE_URL, AMOUNT, "not json")


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

    with direct_vm.expect_revert("Job brief must be"):
        contract.create_job(
            "Landing page", "too short", DELIVERABLE_URL, AMOUNT, json.dumps(MILESTONES)
        )


def test_create_rejects_thin_criterion(direct_vm, direct_deploy, direct_alice):
    contract = _deploy(direct_deploy)
    thin = [dict(MILESTONES[0], criteria=["short"]), MILESTONES[1]]

    with direct_vm.expect_revert("criterion must be"):
        _create(contract, direct_vm, direct_alice, milestones=thin)


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


def test_cancel_open_job(direct_vm, direct_deploy, direct_alice):
    contract = _deploy(direct_deploy)
    job_id = _create(contract, direct_vm, direct_alice)

    direct_vm.sender = direct_alice
    contract.cancel_job(job_id)

    assert json.loads(contract.get_job(job_id))["status"] == "cancelled"


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
