# EscrowCourt

**Milestone escrow where the acceptance criteria are the judge — built as a GenLayer Intelligent Contract.**

A client opens a job, splits the budget into weighted milestones, and freezes the brief,
the deliverable location and every acceptance criterion on-chain. A freelancer accepts
and submits each milestone with evidence. The client either approves it or disputes it.

A disputed milestone is adjudicated by validators that read the deliverable and the
evidence and classify **every acceptance criterion** as `met` / `unmet` / `unclear`.
The settlement — `release`, `refund`, or `split` — is derived **in code** from those
classifications.

> The model classifies. The contract decides the money.

EscrowCourt moves **real GEN**. Opening a job is `payable`: the client sends exactly the
escrow amount with the transaction and the contract holds it. A settled share or a
refund becomes withdrawable, and the payee pulls it out with `withdraw`, which emits a
real GEN transfer to their account.

---

## Live on studionet

| | |
|---|---|
| Contract | [`0xD6b0771b600A22b70D61d2Fd594Ca8F4F8E2D22f`](https://explorer-studio.genlayer.com/address/0xD6b0771b600A22b70D61d2Fd594Ca8F4F8E2D22f) |
| Network | studionet (chain ID 61999) |
| dApp | <https://god-jia.github.io/genlayer-escrowcourt/> |
| Demo video | <https://god-jia.github.io/genlayer-escrowcourt/escrowcourt-demo.mp4> |
| Deploy tx | [`0x9f480141…c8eca53f`](https://explorer-studio.genlayer.com/tx/0x9f48014128fac4193dbb26fd892c2544a780ed2584ba8c965f6e43aac8eca53f) |

The full lifecycle below was executed against studionet with real validators, real web
fetches and a real LLM round — not a simulation.

| Step | Transaction | Result |
|---|---|---|
| `deploy` | [`0x9f480141…c8eca53f`](https://explorer-studio.genlayer.com/tx/0x9f48014128fac4193dbb26fd892c2544a780ed2584ba8c965f6e43aac8eca53f) | `EscrowCourt` deployed |
| `create_job` | [`0xe8672b46…09d4a4d0`](https://explorer-studio.genlayer.com/tx/0xe8672b4649a91b338663733ca520ed373f8a4ca612f26d5277cd011e09d4a4d0) | job #0, milestones `M1` (6000 bps) + `M2` (4000 bps) |
| `accept_job` | [`0x5d11d784…04f39c64`](https://explorer-studio.genlayer.com/tx/0x5d11d784e40b2028ae77ece1cfdb4204603a6e138c70b0952142622304f39c64) | freelancer assigned |
| `submit_milestone M1` | [`0x5573b555…2c2a37a1`](https://explorer-studio.genlayer.com/tx/0x5573b55563d7c526cb1eb443ebd536c6219e51cf6fc87a3477f6ea0b2c2a37a1) | submitted with evidence |
| `dispute_milestone M1` | [`0x8c074fa6…66c4a718`](https://explorer-studio.genlayer.com/tx/0x8c074fa66915e099bfc1bddef75b9c0ff4e8e5abdec3c022d6da90d166c4a718) | client disputes |
| `adjudicate_milestone M1` | [`0x2ce780f0…a5f38ab1`](https://explorer-studio.genlayer.com/tx/0x2ce780f05247bd32a23edae2a9305901aeef1ed94b42535546eaf6b2a5f38ab1) | `split` — freelancer 10 000, client 50 000 |
| `submit_milestone M2` | [`0xa8349608…0fc6fb54`](https://explorer-studio.genlayer.com/tx/0xa83496085e64073e3bad24dc1d4f8bb8e46585008795de6123c1c0e60fc6fb54) | submitted with evidence |
| `approve_milestone M2` | [`0xa653b3cc…5d432ca0`](https://explorer-studio.genlayer.com/tx/0xa653b3ccf4530d388ff33614499c9ba948a469b52555c1d4c5428a725d432ca0) | `release` — freelancer 40 000 |

### The adjudication record returned on-chain

`M1` carried three criteria. The validators classified them independently and the
contract turned that classification into a settlement:

```json
{
  "result": "split",
  "source": "adjudication",
  "deliverable_available": true,
  "evidence_available": true,
  "confidence": 90,
  "criteria": [
    {
      "index": 0,
      "criterion": "The page is served over HTTPS and returns an HTML document.",
      "verdict": "unclear",
      "reason": "No evidence confirms the page was served over HTTPS."
    },
    {
      "index": 1,
      "criterion": "The page contains a visible top-level heading.",
      "verdict": "unmet",
      "reason": "The HTML contains no visible top-level heading element."
    },
    {
      "index": 2,
      "criterion": "The page lists at least three distinct product features.",
      "verdict": "unmet",
      "reason": "The content does not list three distinct product features."
    }
  ],
  "freelancer_cut": 10000,
  "client_cut": 50000,
  "reasoning": "The deliverable provides HTML without a heading or feature list, and lacks protocol information. Therefore criteria 1 and 2 are clearly unmet, while criterion 0 cannot be verified."
}
```

Settlement ledger and per-address track record read back from the contract:

```json
{ "0x029ab4de…4a1532c": 50000, "0x5e5c124a…9966f3": 50000 }
```

```json
{ "released": 1, "refunded": 0, "split": 1, "disputes_raised": 0 }
```

Job #0 ends `completed` with both milestones settled — one by adjudication, one by the
client.

## Demo

A 35-second walkthrough — posting the job, reading job #0 back from studionet, handing a
dispute to the validators, the per-criterion ruling and the settlement ledger — is at
[`docs/escrowcourt-demo.mp4`](docs/escrowcourt-demo.mp4), or streamed from the dApp URL
above. Every frame is the real dApp talking to the deployed contract.

## Why this needs GenLayer

An escrow dispute has two halves, and a normal smart contract can only do one of them.

| Half | Nature | Where it belongs |
|---|---|---|
| Does the delivered page actually satisfy criterion 2? | subjective, needs reading a live web page | non-deterministic |
| `release` / `refund` / `split`, the exact split, the counters | mechanical, must be identical for every node | deterministic |

GenLayer lets both halves live in one contract. `gl.nondet.web.render` fetches the
deliverable and the evidence, `gl.nondet.exec_prompt` classifies the criteria, and
`gl.vm.run_nondet_unsafe` runs it under a custom validator that requires every
validator to agree on the **verdicts**, not on the prose.

Everything inside `<deliverable>`, `<evidence>`, `<submission_note>` and `<claim>` is
treated as untrusted data — the prompt explicitly refuses instructions embedded in it,
which matters because the deliverable is attacker-controlled by definition.

## The settlement is derived, never chosen

The prompt is not allowed to pick a number. It only fills in a verdict per criterion.
The contract then computes:

| Verdicts | Resolution | Payout |
|---|---|---|
| every criterion `met` | `release` | freelancer gets the milestone amount |
| every criterion `unmet` | `refund` | freelancer gets nothing |
| anything else (mixed or `unclear`) | `split` | freelancer gets `amount × (2·met + unclear) / (2·n)` |

A missing deliverable forces every affected criterion to `unclear`, so an unreachable
URL can never quietly become a payout. That is why `M1` above settled at 10 000 out of
60 000: one `unclear`, two `unmet`.

## Contract API

`contracts/escrow_court.py` — 15 public methods (8 write, 7 view).

| Write | What it does |
|---|---|
| `create_job(title, brief, deliverable_url, amount, milestones_json)` — `payable` | freezes the brief, the deliverable location and the weighted milestones; shares must total 10 000 bps; `gl.message.value` must equal `amount`, so the GEN is escrowed by the contract |
| `accept_job(job_id)` | the freelancer takes the job (the client cannot take their own) |
| `cancel_job(job_id)` | the client cancels while the job is still open; the full escrow becomes withdrawable for the client |
| `submit_milestone(job_id, milestone_id, evidence_url, note)` | freelancer submits a milestone with evidence |
| `approve_milestone(job_id, milestone_id)` | client approves; the milestone share becomes withdrawable for the freelancer |
| `dispute_milestone(job_id, milestone_id, claim)` | client disputes a submitted milestone |
| `adjudicate_milestone(job_id, milestone_id)` | anyone triggers the validator round; the settlement is derived in code and credited to the parties |
| `withdraw()` | the caller pulls their withdrawable balance out as a real GEN transfer |

| View | Returns |
|---|---|
| `get_job(job_id)` | the full job record, including rulings |
| `get_balance(address)` | withdrawable balance of an address |
| `get_withdrawable(address)` | withdrawable balance of an address |
| `get_escrow_balance()` | GEN currently held in escrow by the contract |
| `get_reputation(address)` | `released` / `refunded` / `split` / `disputes_raised` counters |
| `get_ledger()` | the whole withdrawable ledger |
| `total_jobs()` | number of jobs created |

Value handling: `create_job` is decorated `@gl.public.write.payable` and rejects a call
whose `gl.message.value` does not equal the job amount. Payouts leave the contract with
`emit_transfer` to the payee's external account, so the escrow holds and moves real GEN,
not just numbers.

## The dApp

`docs/` is a static site (no build step) that talks to the deployed contract through
`genlayer-js`:

- **Post a job** — write the brief, the deliverable URL and the milestone JSON; the
  app validates that the shares total 10 000 bps before sending.
- **Job workspace** — load a job, accept it, submit milestones, approve or dispute.
- **Adjudicate** — trigger the validator round on a disputed milestone and read back
  the per-criterion ruling.
- **Track record** — per-address reputation and the global ledger.

Set the contract address in the header (it is remembered in `localStorage`), connect a
wallet, and the whole lifecycle can be driven from the browser.

## Run it locally

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows
pip install -r requirements.txt

# static check
genvm-lint check contracts/escrow_court.py

# 29 direct-mode unit tests
pytest tests/direct -v
```

The test suite covers the happy path plus every revert: bad milestone JSON, duplicate
ids, shares that do not total 10 000 bps, thin criteria, a create call whose value does
not match the escrow amount, self-acceptance, double acceptance, cancelling after
acceptance, the client refund on cancellation, submitting out of turn, approving or
disputing as the wrong party, adjudicating without a dispute, double adjudication,
withdrawing with nothing to withdraw, unknown ids, and all four settlement paths
(`release`, `refund`, `split`, and `split` when the deliverable is unreachable).

## Deploy it yourself

`tools/deploy_and_demo.py` deploys the contract and runs the entire lifecycle end to
end against studionet, printing every transaction hash: it funds the escrow on
`create_job`, runs a dispute through adjudication, approves the second milestone, then
withdraws both parties' balances as real GEN transfers.

```bash
python tools/deploy_and_demo.py
```

It keeps the deployer key in `tools/.deploy_key` (git-ignored) and writes the full
result — address, trace, final job state, escrow balance, ledger and reputation — to
`tools/deployment.json`.

## Layout

```
contracts/escrow_court.py        the Intelligent Contract
tests/direct/test_escrow_court.py 29 direct-mode tests
docs/                            the dApp (GitHub Pages root) + the demo video
tools/deploy_and_demo.py         deploy + full lifecycle (escrow, adjudication, payouts) on studionet
tools/make_demo.py               compose the demo video from dApp screenshots
```

## License

MIT — see [LICENSE](LICENSE).
