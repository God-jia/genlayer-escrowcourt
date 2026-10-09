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

EscrowCourt moves **real GEN**. Opening a job is `payable`: the escrow is whatever GEN
the client attaches to the `create_job` transaction, and the contract holds it. A
settled share or a refund becomes withdrawable, and the payee pulls it out with
`withdraw`, which emits a real GEN transfer to their account.

Every waiting state also carries a **deadline**. If a party walks away — the job is
never accepted, the freelancer never delivers, the client never reviews, a dispute is
never adjudicated — anyone can settle the milestone and the escrow still moves. No
party can strand the money.

---

## Live on studionet

| | |
|---|---|
| Contract | [`0x7C77ccE524f3F0a34c1E0357a62dc2F3836cd017`](https://explorer-studio.genlayer.com/address/0x7C77ccE524f3F0a34c1E0357a62dc2F3836cd017) |
| Network | studionet (chain ID 61999) |
| dApp | <https://god-jia.github.io/genlayer-escrowcourt/> |
| Demo video | <https://god-jia.github.io/genlayer-escrowcourt/escrowcourt-demo.mp4> |
| Deploy tx | [`0xb0604493…e1fb54e`](https://explorer-studio.genlayer.com/tx/0xb06044938b241c15c5f9286d6e895ad6198fbf7c8d5fbe4f282ed6e96e1fb54e) |
| Escrow amount | `1e15` wei, sent with the `create_job` transaction |
| Recovery windows | 7 d accept · 14 d deliver · 7 d review · 7 d adjudicate |

The full lifecycle below was executed against studionet with real validators, real web
fetches and a real LLM round — not a simulation.

| Step | Transaction | Result |
|---|---|---|
| `deploy` | [`0xb0604493…e1fb54e`](https://explorer-studio.genlayer.com/tx/0xb06044938b241c15c5f9286d6e895ad6198fbf7c8d5fbe4f282ed6e96e1fb54e) | `EscrowCourt` deployed |
| `create_job` (payable, `1e15` wei) | [`0x9cc865c5…4754bb3b`](https://explorer-studio.genlayer.com/tx/0x9cc865c5a073e4118e8f065ad5aea5af11c378ef6b825b7cb23434e34754bb3b) | job #0 funded by the contract; milestones `M1` (6000 bps) + `M2` (4000 bps) |
| `accept_job` | [`0x0a2ddf22…a870bbca`](https://explorer-studio.genlayer.com/tx/0x0a2ddf229f83c1a34bb519be0a7930a99d908fcf072b0a9b839559fda870bbca) | freelancer assigned |
| `submit_milestone M1` | [`0xcae2a96f…3c4c7b5c`](https://explorer-studio.genlayer.com/tx/0xcae2a96fecf3937477dca821efe8c0a5119ee1fc2e4a684bafcbb0663c4c7b5c) | submitted with evidence |
| `dispute_milestone M1` | [`0x37426989…5365f622`](https://explorer-studio.genlayer.com/tx/0x37426989638ea21bb1c82a648b3c6ce74574c9bb2b48c9ae52bc70675365f622) | client disputes |
| `adjudicate_milestone M1` | [`0x2b4a6d0e…54d369b1`](https://explorer-studio.genlayer.com/tx/0x2b4a6d0ed8e64b2980a5e90217abd8b18436b595664f6dc12894822154d369b1) | `split` — freelancer `2e14`, client `4e14` credited |
| `submit_milestone M2` | [`0x2afb2123…333cdcc0`](https://explorer-studio.genlayer.com/tx/0x2afb21235233d9a3cb8247090d2dff8492ec40ac600b4598b4c984e0333cdcc0) | submitted with evidence |
| `approve_milestone M2` | [`0x56b23035…66649847`](https://explorer-studio.genlayer.com/tx/0x56b23035b783f80c260f6a1d36c583e349f32ffe1529871c805b5f0e66649847) | `release` — freelancer `4e14` credited |
| `withdraw` (freelancer) | [`0xdc01148c…616fc37a`](https://explorer-studio.genlayer.com/tx/0xdc01148c93c00cdd23c1dabb41137567c1c2d2192cb1696bb5832926616fc37a) | `6e14` wei paid out as a real GEN transfer — the freelancer's wallet balance rises by exactly `6e14` |
| `withdraw` (client) | [`0xda556a19…3177e68`](https://explorer-studio.genlayer.com/tx/0xda556a1948e37a73f8130343b099985c38657d8f85469bc69b75ce9b33177e68) | `4e14` wei paid out as a real GEN transfer |
| `withdraw` (drained) | [`0x419af97c…6dd0ed`](https://explorer-studio.genlayer.com/tx/0x419af97c6d791aa58e13f65b1a11a91b19133ce18d2b096616413b6fd96dd0ed) | called again with nothing left — `SUCCESS`, returns `0` instead of a GenVM error |

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
      "criterion": "The page returns an HTML document with a body element.",
      "verdict": "met",
      "reason": "The deliverable contains a valid HTML body element."
    },
    {
      "index": 1,
      "criterion": "The page contains a visible top-level heading.",
      "verdict": "unmet",
      "reason": "The deliverable lacks any visible top-level heading."
    },
    {
      "index": 2,
      "criterion": "The page lists at least three distinct product features.",
      "verdict": "unmet",
      "reason": "The deliverable does not list any product features."
    }
  ],
  "freelancer_cut": 200000000000000,
  "client_cut": 400000000000000,
  "reasoning": "The deliverable is an HTML document but contains no heading elements, violating criterion 1. Its content describes a documentation example domain policy, not product features, violating criterion 2. The freelancer's evidence points to an external IANA page, which is not the delivered work and does not fulfill the criteria."
}
```

One `met`, two `unmet` → the contract derives `split` and weights the freelancer's share
by the criteria met, so `M1` pays `2e14` out of `6e14`. After settlement the ledger
credited `2e14` wei to the freelancer (from `M1`) and `4e14` wei to the freelancer (from
`M2`), and `4e14` to the client. Both parties then called `withdraw`, so the ledger and
the escrow balance read back as:

```json
{ "0x5e5c124a…9966f3": 0, "0xe2fe51df…5e1888": 0 }
```

`get_escrow_balance()` returns `0` — every escrowed wei left the contract for a real
account. The freelancer's wallet balance moved from `1e18` before the withdraw to
`1e18 + 6e14` after it, which is the on-chain proof that the payout is a real transfer
and not only a ledger entry.

```json
{ "released": 1, "refunded": 0, "split": 1, "disputes_raised": 0 }
```

Job #0 ends `completed` with both milestones settled — one by adjudication, one by the
client.

---

## Recovery: the escrow can never be frozen

A dispute is only useful if it eventually resolves. EscrowCourt gives **every waiting
state a deadline**, so escrow always has a way out even when a party disappears. The
windows are set once, at deploy time, and are part of the published terms — any
freelancer can read them from `get_terms()` before accepting.

| Waiting state | Who owes the next move | On timeout |
|---|---|---|
| `open` — nobody accepted | a freelancer | `expire_open_job` refunds the client |
| `pending` — not delivered | the freelancer | `resolve_stalled_milestone` refunds the client |
| `submitted` — not reviewed | the client | `resolve_stalled_milestone` releases to the freelancer |
| `disputed` — not adjudicated | adjudication | `resolve_stalled_milestone` splits evenly |

Both settlement methods are **permissionless** and their outcome is fixed by the
milestone's state alone — not by who calls them — so neither party can stall the other
out of their money. Settling one milestone restarts the delivery clock for the
milestones still awaiting delivery, so a long review on an early milestone can never
quietly run out the clock on a later one.

The production windows are measured in days, which makes these paths impossible to
watch live. `tools/demo_recovery.py` therefore deploys the **same contract** with a
60-second window in every state and drives all four stalled cases to completion:

| Case | Stalled state | Method | Resolution |
|---|---|---|---|
| A | nobody accepted | `expire_open_job` | client refunded |
| B | accepted, freelancer vanished | `resolve_stalled_milestone` | `refund` |
| C | delivered, client vanished | `resolve_stalled_milestone` | `release` |
| D | disputed, nobody adjudicates | `resolve_stalled_milestone` | `split` |

The full run is recorded in `tools/recovery.json`; every transaction finalized with a
`SUCCESS` GenVM result and the contract's escrow balance ends at `0`.

| Step | Transaction | Result |
|---|---|---|
| `deploy` (60 s windows) | [`0x9ebfe379…e315f64`](https://explorer-studio.genlayer.com/tx/0x9ebfe3799fe2c5a1fad0142339ccd07e3a81aa99b847e9478c6ebcbbfe315f64) | recovery demo contract |
| `expire_open_job` (A) | [`0x2d583687…a601f61a`](https://explorer-studio.genlayer.com/tx/0x2d5836878af538108f33aac2ad9ce7b398100f6a055655671f0476d4a601f61a) | unaccepted job refunded |
| `resolve_stalled_milestone` (B: `pending`) | [`0xbda7cc9e…6a06da55`](https://explorer-studio.genlayer.com/tx/0xbda7cc9eb4eb58780905b8acb84257ae59686acf7a935b441398a4086a06da55) | `refund` |
| `resolve_stalled_milestone` (C: `submitted`) | [`0xdb46eb3a…283af5a1`](https://explorer-studio.genlayer.com/tx/0xdb46eb3a8302334908fa3323b14848930c53b730d2fb05cb7b022486283af5a1) | `release` |
| `resolve_stalled_milestone` (D: `disputed`) | [`0x417b7162…239145e2`](https://explorer-studio.genlayer.com/tx/0x417b7162bb205ce7acd5e47d77bd5220fae1e4baebf6b9432ebde7b1239145e2) | `split` |

Recovery contract: [`0xc088C31d0fEF9B166D1fa2461Ae7c5D5c5F6B340`](https://explorer-studio.genlayer.com/address/0xc088C31d0fEF9B166D1fa246Ae7c5D5c5F6B340)

---

## Demo

A ~35-second walkthrough — posting a job and funding the escrow, reading job #0 back
from studionet, handing a dispute to the validators, the per-criterion ruling with the
wei-level settlement, and the withdrawable balances — is at
[`docs/escrowcourt-demo.mp4`](docs/escrowcourt-demo.mp4), or streamed from the dApp URL
above. Every frame is the real dApp talking to the deployed contract.

The track-record slide reads a second job (`#1`) that was settled by client approval, so
the freelancer's share is shown sitting in a withdrawable balance before `withdraw`
moves it out of the contract.

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
URL can never quietly become a payout. That is why `M1` above settled at `2e14` out of
`6e14`: one `met`, two `unmet`.

## Contract API

`contracts/escrow_court.py` — 18 public methods (10 write, 8 view).

| Write | What it does |
|---|---|
| `create_job(title, brief, deliverable_url, milestones_json)` — `payable` | freezes the brief, the deliverable location and the weighted milestones; shares must total 10 000 bps; the GEN sent with the transaction becomes the escrow, so no amount argument can disagree with it |
| `accept_job(job_id)` | the freelancer takes the job (the client cannot take their own) |
| `cancel_job(job_id)` | the client cancels while the job is still open; the full escrow becomes withdrawable for the client |
| `expire_open_job(job_id)` | permissionless: once the accept window closes, refunds a job nobody accepted |
| `submit_milestone(job_id, milestone_id, evidence_url, note)` | freelancer submits a milestone with evidence; opens the client's review window |
| `approve_milestone(job_id, milestone_id)` | client approves; the milestone share becomes withdrawable for the freelancer |
| `dispute_milestone(job_id, milestone_id, claim)` | client disputes a submitted milestone; opens the ruling window |
| `adjudicate_milestone(job_id, milestone_id)` | anyone triggers the validator round; the settlement is derived in code and credited to the parties |
| `resolve_stalled_milestone(job_id, milestone_id)` | permissionless: settles a `pending` / `submitted` / `disputed` milestone whose deadline lapsed |
| `withdraw()` | the caller pulls their withdrawable balance out as a real GEN transfer |

| View | Returns |
|---|---|
| `get_job(job_id)` | the full job record, including rulings |
| `get_balance(address)` | withdrawable balance of an address |
| `get_withdrawable(address)` | withdrawable balance of an address |
| `get_escrow_balance()` | GEN currently held in escrow by the contract |
| `get_reputation(address)` | `released` / `refunded` / `split` / `disputes_raised` counters |
| `get_ledger()` | the whole withdrawable ledger |
| `get_terms()` | the published recovery windows, in seconds |
| `total_jobs()` | number of jobs created |

Value handling: `create_job` is decorated `@gl.public.write.payable` and escrows whatever
`gl.message.value` carries, so a funding call can never revert and strand the client's
GEN. `withdraw` returns `0` instead of reverting when the caller has nothing
withdrawable, so a replay against a drained ledger still succeeds. Payouts leave the
contract with `emit_transfer` to the payee's external account — routed through the EVM
contract interface, because sending value to an externally owned account over the IC
interface would emit an IC-to-IC message to a codeless account and fail — so the escrow
holds and moves real GEN, not just numbers.

Deadlines come from `gl.message_raw["datetime"]`, the protocol-supplied transaction
timestamp, so every validator derives the same deadline and the timeout outcome is
deterministic.

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

# 46 direct-mode unit tests
pytest tests/direct -v
```

The screenshot and video tooling needs a few extra packages:
`pip install pillow numpy opencv-python-headless playwright` (the capture scripts
drive the Chrome already installed on the machine).

The test suite covers the happy path plus every revert: bad milestone JSON, duplicate
ids, shares that do not total 10 000 bps, thin criteria, a create call that sends no
escrow, self-acceptance, double acceptance, cancelling after acceptance, the client
refund on cancellation, submitting out of turn, approving or disputing as the wrong
party, adjudicating without a dispute, double adjudication, withdrawing with nothing to
withdraw (returns 0), unknown ids, and all four settlement paths (`release`, `refund`,
`split`, and `split` when the deliverable is unreachable).

It also includes **adversarial recovery tests** that prove neither party can strand the
escrow: an unaccepted job refunds after the accept window, a `pending` milestone refunds
after the delivery window, a `submitted` milestone pays the freelancer after the review
window, a `disputed` milestone splits after the ruling window, and the specific cases
where the client goes silent, the freelancer goes silent, or a dispute is left
unadjudicated — each ends with the escrow moving and `get_escrow_balance()` back to `0`.

## Deploy it yourself

`tools/deploy_and_demo.py` deploys the contract and runs the entire lifecycle end to
end against studionet, printing every transaction hash: it funds the escrow on
`create_job`, runs a dispute through adjudication, approves the second milestone, then
withdraws both parties' balances as real GEN transfers — and finally calls `withdraw`
once more against the drained ledger to show it returns `0` with a `SUCCESS` result.

```bash
python tools/deploy_and_demo.py
```

It keeps the deployer key in `tools/.deploy_key` (git-ignored) and writes the full
result — address, trace, final job state, escrow balance, ledger and reputation — to
`tools/deployment.json`.

To watch the timeout paths live, run the 60-second-window recovery demo instead:

```bash
python tools/demo_recovery.py
```

It stages four stalled jobs, waits out every deadline, settles each one
permissionlessly and withdraws the recovered GEN, writing the run to
`tools/recovery.json`.

## Layout

```
contracts/escrow_court.py        the Intelligent Contract
tests/direct/test_escrow_court.py 46 direct-mode tests
docs/                            the dApp (GitHub Pages root) + the demo video
tools/deploy_and_demo.py         deploy + full lifecycle (escrow, adjudication, payouts) on studionet
tools/demo_recovery.py           deploy with 60s windows and drive all four timeout paths
tools/deployment.json            the recorded lifecycle run
tools/recovery.json              the recorded recovery run
tools/extra_demo.py              fund one more job and release it (leaves a live withdrawable balance)
tools/make_demo.py               compose the demo video from dApp screenshots
tools/shoot.py                   capture the dApp screenshots with headless Chrome
```

## License

MIT — see [LICENSE](LICENSE).
